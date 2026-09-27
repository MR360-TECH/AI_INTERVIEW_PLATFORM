import re
import json
import time
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import (
    db,
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
    interview_datetime = db.Column(db.DateTime, server_default=db.func.now())

    # Statuses that should NOT consume a token slot:
    #   - anything with 'Practice' in name
    #   - 'Abandoned (Reset)' — user reset before finishing
    #   - 'Terminated (Breach)' — auto-terminated by proctoring
    NON_COUNTING_STATUSES = ['Abandoned (Reset)', 'Terminated (Breach)']

    @property
    def session_code(self):
        """Returns a standardized unique assessment session code, e.g. AIS-000042, scalable beyond 1,000,000+ users."""
        if self.id:
            return f"AIS-{self.id:06d}"
        return "AIS-000000"

    @classmethod
    def real_attempt_filter(cls):
        """Returns SQLAlchemy filter conditions for attempts that count against the token limit.
        Only completed assessments (passed, failed, selected, rejected) consume a token."""
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


class SettingsSnapshot:
    def __init__(self, s=None):
        self.min_questions = getattr(s, 'min_questions', 3) or 3
        self.max_questions = getattr(s, 'max_questions', 8) or 8
        self.pass_score = getattr(s, 'pass_score', 3) or 3
        self.default_difficulty = getattr(s, 'default_difficulty', 'student') or 'student'
        self.question_timer_seconds = getattr(s, 'question_timer_seconds', 90) or 90
        self.enable_attempt_limits = getattr(s, 'enable_attempt_limits', True)
        if self.enable_attempt_limits is None:
            self.enable_attempt_limits = True
        self.default_allowed_interviews = getattr(s, 'default_allowed_interviews', 2) or 2
        self.enable_warning_strikes = getattr(s, 'enable_warning_strikes', True)
        if self.enable_warning_strikes is None:
            self.enable_warning_strikes = True


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
                enable_warning_strikes=True
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
        db.session.commit()
    except Exception:
        db.session.rollback()


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
