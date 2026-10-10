import os
import re
import json
import time
from datetime import datetime
import io
import mimetypes
from flask import current_app, send_file
from sqlalchemy import String, LargeBinary, event
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import (
    db,
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS,
    ALLOWED_RESUME_EXTENSIONS
)

# ══════════════════════════════════════════════════════════════════════════════
# DATA PERSISTENCE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)
    gender = db.Column(db.String(10))
    education = db.Column(db.String(50))
    course = db.Column(db.String(100))
    semester = db.Column(db.String(20))
    auth_provider = db.Column(db.String(20), default='local')
    email_verified = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    registered_at = db.Column(db.DateTime, server_default=db.func.now())
    user_type = db.Column(db.String(20), default='student')
    github_url = db.Column(db.String(200))
    linkedin_url = db.Column(db.String(200))
    skills = db.Column(db.Text)
    years_of_experience = db.Column(db.String(20))
    current_designation = db.Column(db.String(100))
    resume_text = db.Column(db.Text)
    resume_filename = db.Column(db.String(255))
    extra_allowed_interviews = db.Column(db.Integer, default=0)
    attempts_count = db.Column(db.Integer, default=0)
    welcome_sent = db.Column(db.Boolean, default=False)

    def get_attempts_used(self):
        try:
            curr_count = self.attempts_count or 0
        except Exception:
            curr_count = 0
        results_count = InterviewResult.query.filter(
            InterviewResult.user_id == self.id,
            InterviewResult.real_attempt_filter()
        ).count()
        return max(curr_count, results_count)


class InterviewResult(db.Model):
    __tablename__ = 'interview_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Numeric(4, 2))
    status = db.Column(db.String(50))
    strengths = db.Column(db.Text)
    improvements = db.Column(db.Text)
    summary = db.Column(db.Text)
    domain = db.Column(db.String(150))
    is_terminated = db.Column(db.Boolean, default=False)
    termination_reason = db.Column(db.Text)
    transcript = db.Column(db.Text)          # JSON [{"q", "a"}] of the questions answered (kept for exited sessions)
    interview_datetime = db.Column(db.DateTime, server_default=db.func.now())

    # The candidate pressed Exit during a scored assessment: the answers given so far are evaluated and it counts
    # as one attempt.
    EXITED_STATUS = "Exited (Incomplete)"

    # Statuses that should NOT consume a token slot:
    #   - anything with 'Practice' in name
    #   - 'Abandoned (Reset)' — older records from before exiting counted as an attempt
    NON_COUNTING_STATUSES = ['Abandoned (Reset)']

    @property
    def is_exited(self):
        return self.status == self.EXITED_STATUS

    def transcript_items(self):
        try:
            items = json.loads(self.transcript or "[]")
            return [i for i in items if isinstance(i, dict) and i.get("q")]
        except (TypeError, ValueError):
            return []

    @property
    def session_code(self):
        """Returns a standardized unique assessment session code, e.g. AIS-000042, scalable beyond 1,000,000+ users."""
        if self.id:
            return f"AIS-{self.id:06d}"
        return "AIS-000000"

    @classmethod
    def real_attempt_filter(cls):
        """Returns SQLAlchemy filter conditions for attempts that count against the token limit.
        Only completed or terminated assessments consume a token."""
        from sqlalchemy import and_
        return and_(
            ~cls.status.like('%Practice%'),
            ~cls.status.in_(cls.NON_COUNTING_STATUSES)
        )


class InterviewProgress(db.Model):
    __tablename__ = 'interview_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    chat_history = db.Column(db.Text, default='[]')
    q_count = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    # Interview integrity (all kept on the server, so clearing browser storage cannot reset them)
    strikes = db.Column(db.Integer, default=0)
    sid = db.Column(db.String(40))                        # which browser / device currently holds this interview
    last_seen_at = db.Column(db.DateTime)                 # last page load or heartbeat from that browser
    question_shown_at = db.Column(db.DateTime)            # when the current question was first shown


class ResumeFile(db.Model):
    """The candidate's original resume file, kept in the database. A free host (Render) has no permanent disk, so a
    file written to disk would be lost on a restart or redeploy. One row per user; a new upload replaces it."""
    __tablename__ = 'resume_files'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    filename = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer, default=0)
    data = db.Column(LargeBinary, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class InterviewViolation(db.Model):
    """One integrity event recorded during a scored assessment. `strike_no` is set when it counted as a strike;
    review flags (strike_no NULL) are only ever shown to the admin. result_id is filled in when the assessment ends."""
    __tablename__ = 'interview_violations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    result_id = db.Column(db.Integer, db.ForeignKey('interview_results.id'), nullable=True, index=True)
    kind = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    detail = db.Column(db.String(300))
    strike_no = db.Column(db.Integer)
    q_num = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False)


class Feedback(db.Model):
    """A review / feedback message sent from the feedback box. Kept in the database so nothing is lost if the e-mail fails."""
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rating = db.Column(db.Integer)                       # 1-5, optional
    category = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    contact_ok = db.Column(db.Boolean, default=True)
    page = db.Column(db.String(30))                      # dashboard | result
    session_code = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, nullable=False)


class ResourceBookmark(db.Model):
    """A preparation-library link a candidate saved for later."""
    __tablename__ = 'resource_bookmarks'
    __table_args__ = (db.UniqueConstraint('user_id', 'url', name='uq_bookmark_user_url'),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)


class LinkCheck(db.Model):
    """Result of the admin link checker for one library link. Only the admin ever sees this; `hidden` removes the link
    from the candidate pages without editing code."""
    __tablename__ = 'link_checks'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False, unique=True)
    status_code = db.Column(db.Integer)
    kind = db.Column(db.String(10))                      # ok | blocked | broken
    note = db.Column(db.String(120))
    checked_at = db.Column(db.DateTime)
    hidden = db.Column(db.Boolean, default=False)


class OtpChallenge(db.Model):
    """One-time code issued by email. Only a keyed hash of the code is stored (never the code itself)."""
    __tablename__ = 'otp_challenges'
    id = db.Column(db.Integer, primary_key=True)
    purpose = db.Column(db.String(20), nullable=False)          # login | signup | reset
    email = db.Column(db.String(100), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False)


class AuthThrottle(db.Model):
    """Failed-attempt counter used to lock brute-force attempts on login and code requests."""
    __tablename__ = 'auth_throttle'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(160), unique=True, nullable=False)
    failures = db.Column(db.Integer, default=0)
    window_start = db.Column(db.DateTime)
    locked_until = db.Column(db.DateTime)


class AdminSettings(db.Model):
    __tablename__ = 'admin_settings'
    id = db.Column(db.Integer, primary_key=True)
    min_questions = db.Column(db.Integer, default=3)
    max_questions = db.Column(db.Integer, default=8)
    pass_score = db.Column(db.Integer, default=3)
    default_difficulty = db.Column(db.String(20), default='student')
    question_timer_seconds = db.Column(db.Integer, default=90)
    enable_attempt_limits = db.Column(db.Boolean, default=True)
    default_allowed_interviews = db.Column(db.Integer, default=2)
    enable_warning_strikes = db.Column(db.Boolean, default=True)
    enable_feedback_emails = db.Column(db.Boolean, default=True)
    # Interview integrity. `enable_warning_strikes` above is the master proctoring switch for scored assessments.
    max_strikes = db.Column(db.Integer, default=2)
    proctor_server_strikes = db.Column(db.Boolean, default=True)
    proctor_single_session = db.Column(db.Boolean, default=True)
    proctor_server_timer = db.Column(db.Boolean, default=True)
    proctor_block_copy_paste = db.Column(db.Boolean, default=True)
    proctor_fullscreen = db.Column(db.Boolean, default=False)
    proctor_typing_flags = db.Column(db.Boolean, default=True)
    proctor_integrity_log = db.Column(db.Boolean, default=True)
    enable_rate_limits = db.Column(db.Boolean, default=True)      # friendly request limits (see rate_limit.py)


# The integrity switches, with the value each one has when nothing was ever saved.
INTEGRITY_SWITCHES = {
    "proctor_server_strikes": True, "proctor_single_session": True, "proctor_server_timer": True,
    "proctor_block_copy_paste": True, "proctor_fullscreen": False, "proctor_typing_flags": True,
    "proctor_integrity_log": True,
}


class SettingsSnapshot:
    def __init__(self, s=None):
        self.min_questions = getattr(s, 'min_questions', 3) or 3
        self.max_questions = getattr(s, 'max_questions', 8) or 8
        pass_score = getattr(s, 'pass_score', 3)
        self.pass_score = 3 if pass_score is None else pass_score        # 0 is a valid passing score
        self.default_difficulty = getattr(s, 'default_difficulty', 'student') or 'student'
        self.question_timer_seconds = getattr(s, 'question_timer_seconds', 90) or 90
        self.enable_attempt_limits = getattr(s, 'enable_attempt_limits', True)
        if self.enable_attempt_limits is None:
            self.enable_attempt_limits = True
        self.default_allowed_interviews = getattr(s, 'default_allowed_interviews', 2) or 2
        self.enable_warning_strikes = getattr(s, 'enable_warning_strikes', True)
        if self.enable_warning_strikes is None:
            self.enable_warning_strikes = True
        self.enable_feedback_emails = getattr(s, 'enable_feedback_emails', True)
        if self.enable_feedback_emails is None:
            self.enable_feedback_emails = True
        self.max_strikes = max(1, min(5, getattr(s, 'max_strikes', 2) or 2))
        rate = getattr(s, 'enable_rate_limits', True)
        self.enable_rate_limits = True if rate is None else bool(rate)
        for name, default in INTEGRITY_SWITCHES.items():
            value = getattr(s, name, default)
            setattr(self, name, default if value is None else bool(value))


def _clamp_strings(mapper, connection, target):
    """PostgreSQL rejects text longer than a VARCHAR(n) column (MySQL used to cut it silently), which would make
    saving fail for free-text values such as the domain a candidate types as their first answer. Trim to fit."""
    for column in mapper.columns:
        if isinstance(column.type, String) and column.type.length:
            value = getattr(target, column.key, None)
            if isinstance(value, str) and len(value) > column.type.length:
                setattr(target, column.key, value[:column.type.length])


event.listen(db.Model, "before_insert", _clamp_strings, propagate=True)
event.listen(db.Model, "before_update", _clamp_strings, propagate=True)


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS CACHE & PERSISTENCE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_cached_settings = None
_cached_settings_time = 0


def invalidate_settings_cache():
    """Force-clear the in-memory settings cache so the next call to get_settings()
    fetches fresh data from the database. Call this immediately after saving AdminSettings."""
    global _cached_settings, _cached_settings_time
    _cached_settings = None
    _cached_settings_time = 0


def get_settings():
    global _cached_settings, _cached_settings_time
    now = time.time()
    if _cached_settings and (now - _cached_settings_time) < 5:
        return _cached_settings

    try:
        settings_row = AdminSettings.query.first()
        if not settings_row:
            settings_row = AdminSettings(
                min_questions=3,
                max_questions=8,
                pass_score=3,
                default_difficulty='student',
                question_timer_seconds=90,
                enable_attempt_limits=True,
                default_allowed_interviews=2,
                enable_warning_strikes=True,
                enable_feedback_emails=True
            )
            db.session.add(settings_row)
            db.session.commit()
        snapshot = SettingsSnapshot(settings_row)
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        snapshot = SettingsSnapshot()

    _cached_settings = snapshot
    _cached_settings_time = now
    return snapshot


def save_progress(user_id, chat_history, q_count):
    try:
        progress = InterviewProgress.query.filter_by(user_id=user_id).first()
        if not progress:
            progress = InterviewProgress(user_id=user_id)
            db.session.add(progress)
        progress.chat_history = json.dumps(chat_history)
        progress.q_count = q_count
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        try:
            progress = InterviewProgress.query.filter_by(user_id=user_id).first()
            if progress:
                progress.chat_history = json.dumps(chat_history)
                progress.q_count = q_count
                db.session.commit()
        except Exception:
            db.session.rollback()


def clear_progress(user_id):
    try:
        InterviewProgress.query.filter_by(user_id=user_id).delete()
        # integrity events that never became part of a stored result belong to the interview being discarded
        InterviewViolation.query.filter_by(user_id=user_id, result_id=None).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()


def attach_violations(user_id, result_id):
    """Links the integrity events of the interview that just ended to its stored result. Call BEFORE clear_progress."""
    try:
        InterviewViolation.query.filter_by(user_id=user_id, result_id=None).update({"result_id": result_id})
        db.session.commit()
    except Exception:
        db.session.rollback()



def record_counted_attempt(user, result_record):
    """Adds a result that consumes one attempt token and bumps the user's cached counter by exactly 1.

    The current usage must be read BEFORE the new row is added: querying afterwards autoflushes the
    pending result, so it would be counted twice (once as a row, once by the +1).
    Caller commits (or rolls back) — nothing is consumed unless the commit succeeds."""
    with db.session.no_autoflush:
        used_so_far = user.get_attempts_used() if user else 0
    db.session.add(result_record)
    if user:
        user.attempts_count = used_so_far + 1


def _legacy_resume_path(user):
    """Resumes saved before they moved into the database were files in UPLOAD_FOLDER."""
    if not user or not user.resume_filename:
        return None
    folder = current_app.config.get('UPLOAD_FOLDER', UPLOAD_FOLDER)
    path = os.path.join(folder, user.resume_filename)
    return path if os.path.isfile(path) else None


def save_resume_file(user, ext, data):
    """Stores the original resume in the database (replacing the previous one) and returns its file name.
    The caller commits. Nothing is written to disk."""
    saved = f"user_{user.id}_resume.{ext}"
    row = ResumeFile.query.filter_by(user_id=user.id).first()
    if row is None:
        row = ResumeFile(user_id=user.id)
        db.session.add(row)
    row.filename, row.size, row.data, row.updated_at = saved, len(data), data, datetime.utcnow()
    legacy = _legacy_resume_path(user)          # an older copy on disk is now obsolete
    if legacy and os.path.basename(legacy) != saved:
        _remove_quietly(legacy)
    user.resume_filename = saved
    return saved


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError as e:
        print(f"Could not remove old resume file: {e}")


def delete_resume_file(user):
    """Removes the stored resume (database row and any older file on disk). The caller commits."""
    if not user:
        return
    ResumeFile.query.filter_by(user_id=user.id).delete()
    legacy = _legacy_resume_path(user)
    if legacy:
        _remove_quietly(legacy)


def load_resume_file(user):
    """Returns (file name, bytes) of the candidate's resume, or None. A file that still only exists on disk is
    copied into the database the first time it is opened, so older resumes are kept too."""
    if not user or not user.resume_filename:
        return None
    row = ResumeFile.query.filter_by(user_id=user.id).first()
    if row:
        return row.filename, bytes(row.data)
    legacy = _legacy_resume_path(user)
    if not legacy:
        return None
    with open(legacy, "rb") as f:
        data = f.read()
    try:
        db.session.add(ResumeFile(user_id=user.id, filename=user.resume_filename, size=len(data), data=data))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Could not move an older resume into the database: {e}")
    return user.resume_filename, data


def move_disk_resumes_to_database():
    """At startup: copies every resume that still exists only as a file on disk into the database (the files are left
    in place). Safe to run on every start; it does nothing once everything has been copied. Returns how many moved."""
    moved = 0
    stored = {uid for (uid,) in db.session.query(ResumeFile.user_id).all()}
    for user in User.query.filter(User.resume_filename.isnot(None)).all():
        if user.id in stored:
            continue
        path = _legacy_resume_path(user)
        if not path:
            continue
        try:
            with open(path, "rb") as f:
                data = f.read()
            db.session.add(ResumeFile(user_id=user.id, filename=user.resume_filename, size=len(data), data=data))
            db.session.commit()
            moved += 1
        except Exception as e:
            db.session.rollback()
            print(f"Could not move the resume of user {user.id} into the database: {e}")
    return moved


def resume_response(user):
    """The resume as a Flask response (shown in the browser), or None when there is no stored file."""
    found = load_resume_file(user)
    if not found:
        return None
    name, data = found
    kind = mimetypes.guess_type(name)[0] or "application/octet-stream"   # from our own extension, never the client's
    return send_file(io.BytesIO(data), mimetype=kind, download_name=name, max_age=0)


def resume_file_exists(user):
    """True when the candidate's original resume file is stored (database, or an older file still on disk)."""
    if not user or not user.resume_filename:
        return False
    if db.session.query(ResumeFile.id).filter_by(user_id=user.id).first():
        return True
    return _legacy_resume_path(user) is not None


# ══════════════════════════════════════════════════════════════════════════════
# DATA & PROFILE VALIDATORS
# ══════════════════════════════════════════════════════════════════════════════

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(email and re.match(pattern, email))


def profile_is_complete(user):
    if not user or not user.gender:
        return False
    if getattr(user, 'user_type', None) == 'professional':
        return bool(user.current_designation and user.years_of_experience)
    return bool(user.education and user.course and user.semester)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_resume_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_RESUME_EXTENSIONS
