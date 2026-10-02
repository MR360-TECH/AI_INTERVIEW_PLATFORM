"""Interview integrity for scored assessments (practice sessions are never proctored).

Everything is decided and stored on the SERVER, so clearing browser storage or editing the page cannot reset it:
  * strikes     every violation is a strike; the interview ends when the admin's strike limit is reached
  * one session an interview open in another browser / device is refused (and counted) while the first is active
  * server timer the time a question has left is kept on the server, so a reload cannot reset the clock
  * copy / paste blocked in the browser, and every attempt is a violation
  * fullscreen  (optional) leaving fullscreen is a violation
  * typing flags answers that look pasted or instant are flagged for the admin (review only, not a strike)
  * integrity log every event is stored and shown to the admin on the report

Each feature has its own admin switch (AdminSettings.proctor_*); `enable_warning_strikes` is the master switch.
"""
import secrets
from datetime import datetime, timedelta, timezone

from flask import session

from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db
from MODULES.LAYER_2_DATA_PERSISTENCE.models import (
    InterviewProgress, InterviewResult, InterviewViolation, User, attach_violations, clear_progress, record_counted_attempt,
)

SESSION_TAKEOVER_SECONDS = 120     # a holder that has been silent this long no longer blocks another browser
LATE_GRACE_SECONDS = 15            # network slack on top of the question time limit
DUPLICATE_WINDOW_SECONDS = 2       # the same event twice inside this window is one event

# kind -> (title shown to the candidate, what exactly happened, admin switch that enables it, counts as a strike)
RULES = {
    "tab_switch": ("You left the exam window",
                   "You switched to another tab, window or application while the assessment was running.", None, True),
    "fullscreen_exit": ("You left fullscreen mode",
                        "This assessment must stay in fullscreen. You exited fullscreen during the assessment.",
                        "proctor_fullscreen", True),
    "paste": ("You tried to paste text",
              "Pasting is not allowed. Your answer must be typed or spoken by you.", "proctor_block_copy_paste", True),
    "copy": ("You tried to copy question text",
             "Copying or cutting question text is not allowed during the assessment.", "proctor_block_copy_paste", True),
    "second_session": ("The interview was opened in another window or device",
                       "This interview is already open in another browser or device. Only one session is allowed at a time.",
                       "proctor_single_session", True),
    "late_answer": ("You answered after the time limit",
                    "Your answer arrived after the time limit for this question had ended.", "proctor_server_timer", True),
    "fast_answer": ("Answer arrived unusually fast", "", "proctor_typing_flags", False),
    "no_typing": ("Answer text did not match typing activity", "", "proctor_typing_flags", False),
}


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def proctored(settings, is_practice):
    """True when integrity rules apply: a scored assessment with the master switch on."""
    return bool(settings.enable_warning_strikes and not is_practice)


def rule_enabled(settings, kind):
    switch = RULES[kind][2]
    return switch is None or bool(getattr(settings, switch, False))


def current_sid():
    """Identifies this browser's login session (a second tab in the same browser shares it)."""
    if not session.get("_sid"):
        session["_sid"] = secrets.token_hex(8)
    return session["_sid"]


def get_progress(user_id):
    return InterviewProgress.query.filter_by(user_id=user_id).first()


def warning_text(remaining):
    if remaining <= 0:
        return "You have reached the strike limit. The assessment is being ended."
    if remaining == 1:
        return "FINAL WARNING: one more violation will end your assessment immediately."
    return f"{remaining} more violations will end your assessment."


def box_for(kind, strikes, max_strikes, detail=""):
    title, text, _switch, counted = RULES[kind]
    return {"kind": kind, "title": title, "mistake": text, "detail": detail, "strikes": strikes, "max": max_strikes,
            "warning": warning_text(max_strikes - strikes) if counted else ""}


def terminate(user_id, reason, summary):
    """Ends the assessment: stores a terminated result (it counts as an attempt), clears the saved interview and
    queues the neutral notice e-mail. Returns the new result id, or None when there was nothing to terminate."""
    from MODULES.LAYER_3_BUSINESS_SERVICES.feedback_email import queue_terminated_notice
    result_id = None
    domain = session.get("interview_domain", "General")
    try:
        record = InterviewResult(user_id=user_id, score=0.0, status="Terminated (Breach)", summary=summary, domain=domain,
                                 is_terminated=True, termination_reason=reason)
        user = db.session.get(User, user_id)
        record_counted_attempt(user, record)
        db.session.commit()
        result_id = record.id
        attach_violations(user_id, result_id)
        if user and user.email:
            queue_terminated_notice(user.email, full_name=user.full_name, domain=domain, session_code=record.session_code,
                                    result_id=record.id, when=datetime.now())
    except Exception as err:
        print(f"[INTEGRITY] could not record the termination: {err}")
        db.session.rollback()
    for key in ("chat_history", "q_count", "resume_choice", "resume_summary", "interview_domain", "interview_difficulty",
                "interview_mode", "practice_topic", "pending_violation"):
        session.pop(key, None)
    session.modified = True
    clear_progress(user_id)
    return result_id


def record(user_id, progress, kind, detail, settings):
    """Stores one event. Returns {"ignored"} for a duplicate, {"terminated": True, ...} when it used the last strike,
    otherwise {"counted", "strikes", "max", "box"}."""
    now = _now()
    last = (InterviewViolation.query.filter_by(user_id=user_id, kind=kind, result_id=None)
            .order_by(InterviewViolation.id.desc()).first())
    if last and (now - last.created_at).total_seconds() < DUPLICATE_WINDOW_SECONDS:
        return {"ignored": True, "strikes": progress.strikes or 0, "max": settings.max_strikes}

    title, _text, _switch, can_strike = RULES[kind]
    counted = bool(can_strike and settings.proctor_server_strikes)
    strike_no = None
    if counted:
        progress.strikes = (progress.strikes or 0) + 1
        strike_no = progress.strikes
    db.session.add(InterviewViolation(user_id=user_id, kind=kind, title=title, detail=(detail or "")[:300], strike_no=strike_no,
                                      q_num=(progress.q_count or 0) + 1, created_at=now))
    db.session.commit()

    strikes = progress.strikes or 0
    if counted and strikes >= settings.max_strikes:
        reason = f"Integrity strikes reached the limit ({settings.max_strikes} of {settings.max_strikes}). Last violation: {title}."
        summary = ("SESSION ENDED EARLY:\n\nThis assessment session was closed automatically because the integrity rules were "
                   f"broken on {settings.max_strikes} occasions. The last violation was: {title}.\n\n"
                   "The session has been recorded as terminated and no evaluation score was generated. "
                   "It remains available for administrator review.")
        terminate(user_id, reason, summary)
        return {"terminated": True, "counted": True, "strikes": strikes, "max": settings.max_strikes,
                "redirect": "/interview-result?terminated=1"}
    return {"counted": counted, "strikes": strikes, "max": settings.max_strikes, "box": box_for(kind, strikes, settings.max_strikes, detail) if counted else None}


def touch(user_id, new_question=False):
    """Marks this browser as the active holder and remembers when the current question was first shown."""
    progress = get_progress(user_id)
    if not progress:
        return
    now = _now()
    progress.sid = current_sid()
    progress.last_seen_at = now
    if new_question or progress.question_shown_at is None:
        progress.question_shown_at = now
    db.session.commit()


def guard_session(user_id, settings):
    """One session at a time. Returns None when this browser may continue, otherwise a dict describing the refusal:
    {"terminated": True, "redirect": ...} or {"blocked": True, "notice": ...}."""
    if not settings.proctor_single_session:
        return None
    progress = get_progress(user_id)
    if not progress or not progress.sid:
        return None
    sid = current_sid()
    if progress.sid == sid:
        progress.last_seen_at = _now()
        db.session.commit()
        return None
    idle = (_now() - progress.last_seen_at).total_seconds() if progress.last_seen_at else SESSION_TAKEOVER_SECONDS + 1
    if idle > SESSION_TAKEOVER_SECONDS:                    # the other browser went quiet: this one takes over
        progress.sid = sid
        progress.last_seen_at = _now()
        db.session.commit()
        return None
    outcome = record(user_id, progress, "second_session", "Opened while another browser or device was using this interview.", settings)
    if outcome.get("terminated"):
        return {"terminated": True, "redirect": outcome["redirect"]}
    return {"blocked": True, "notice": (f"Strike {outcome['strikes']} of {outcome['max']}. " if outcome.get("counted") else "")
            + "Close the interview in the other window or device, or wait about a minute, then press Back."}


def seconds_left(progress, settings, total_seconds):
    """Time left for the current question according to the server clock (None when the server timer is off)."""
    if not settings.proctor_server_timer or not progress or not progress.question_shown_at:
        return None
    elapsed = (_now() - progress.question_shown_at).total_seconds()
    return max(0, int(total_seconds - elapsed))


def check_answer(user_id, settings, answer_text, form, total_seconds):
    """Runs the checks that belong to a submitted answer. Returns {"terminated": ..., "timed_out": ...}."""
    progress = get_progress(user_id)
    out = {"terminated": False, "timed_out": False}
    if not progress:
        return out
    if settings.proctor_server_timer and progress.question_shown_at:
        elapsed = (_now() - progress.question_shown_at).total_seconds()
        if answer_text and elapsed > total_seconds + LATE_GRACE_SECONDS:
            detail = f"Answered {int(elapsed - total_seconds)} seconds after the {total_seconds}-second limit."
            outcome = record(user_id, progress, "late_answer", detail, settings)
            if outcome.get("terminated"):
                return dict(out, terminated=True, redirect=outcome["redirect"])
            if outcome.get("box"):
                session["pending_violation"] = outcome["box"]
        elif not answer_text and elapsed > total_seconds:
            out["timed_out"] = True
    if settings.proctor_typing_flags and answer_text:
        flag = _typing_flag(answer_text, form)
        if flag:
            record(user_id, progress, flag[0], flag[1], settings)
    return out


def _typing_flag(answer, form):
    """Review-only flags. Voice dictation is excluded because it inserts text without key presses."""
    if "t_ms" not in form:
        return None
    try:
        length = len(answer)
        elapsed_ms = int(form.get("t_ms", "0") or 0)
        keys = int(form.get("keys", "0") or 0)
        voice = (form.get("voice", "0") or "0") == "1"
    except ValueError:
        return None
    if voice or length < 120:
        return None
    if keys == 0:
        return ("no_typing", f"A {length}-character answer was submitted with no typing activity recorded at all, so the text was inserted by some other means.")
    if keys < length * 0.3:
        return ("no_typing", f"A {length}-character answer was submitted with only {keys} key presses recorded, so most of the text was probably inserted rather than typed.")
    if elapsed_ms < 4000:
        return ("fast_answer", f"A {length}-character answer was submitted {elapsed_ms / 1000:.1f} seconds after the question appeared.")
    return None


def template_context(user_id, settings):
    """What the interview page needs to run the integrity features in the browser."""
    progress = get_progress(user_id)
    return {
        "server_strikes": bool(settings.proctor_server_strikes),
        "strikes": (progress.strikes or 0) if progress else 0,
        "max_strikes": settings.max_strikes,
        "block_copy_paste": bool(settings.proctor_block_copy_paste),
        "fullscreen": bool(settings.proctor_fullscreen),
        "single_session": bool(settings.proctor_single_session),
        "typing_flags": bool(settings.proctor_typing_flags),
        "pending": session.pop("pending_violation", None),
    }
