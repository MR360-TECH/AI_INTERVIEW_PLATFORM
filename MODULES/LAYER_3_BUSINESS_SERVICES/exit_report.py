"""Exiting a scored assessment before it is complete.

Rules:
  * Exit erases the interview: it can never be resumed. (Only a server or network problem leaves a saved interview
    that can be continued, because the candidate never chose to leave.)
  * The questions answered so far are evaluated by the AI, so the candidate gets a real analysis of those answers.
    The candidate's report and e-mail show only that analysis (never the questions, and never how many questions the
    interview was meant to have, which is an admin setting). The questions and answers are kept for the admin report.
  * It counts as one attempt, like any finished or terminated assessment.
  * The candidate gets the "incomplete session" feedback e-mail (admin switch: feedback e-mails).
  * Leaving before the first interview question (only the role question was asked) records nothing and uses nothing.
"""
import json
from datetime import datetime

from flask import session

from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db
from MODULES.LAYER_2_DATA_PERSISTENCE.models import (
    InterviewProgress, InterviewResult, User, attach_violations, clear_progress, record_counted_attempt,
)
from MODULES.LAYER_3_BUSINESS_SERVICES.ai_client import build_evaluation_prompt, evaluate_interview

NO_ANSWER_SUMMARY = ("The candidate exited the assessment before answering any interview question, so there were no "
                     "answers to review.")
REVIEW_FAILED_SUMMARY = ("The candidate exited the assessment before it was complete. An AI analysis of the answers "
                         "given could not be generated at that moment.")

INTERVIEW_SESSION_KEYS = ("chat_history", "q_count", "resume_choice", "resume_summary", "interview_domain",
                          "interview_difficulty", "interview_mode", "practice_topic", "lang_target", "lang_focus",
                          "lang_level", "pending_violation")


def load_history(user_id):
    progress = InterviewProgress.query.filter_by(user_id=user_id).first()
    try:
        return json.loads(progress.chat_history or "[]") if progress else []
    except (TypeError, ValueError):
        return []


def has_unfinished_assessment(user_id):
    """True when a saved interview exists in which the candidate already answered something. Exit always erases the
    interview, so such a save only remains after a server or network problem, and it may be continued."""
    return any(entry.get("role") == "answer" for entry in load_history(user_id))


def build_transcript(history):
    """Question/answer pairs of the interview itself. The first question only asks for the role or domain, so it is
    left out. A question still waiting for an answer when the candidate exited is kept with answer None."""
    items, pending = [], None
    seen_role_question = False
    for entry in history:
        role, text = entry.get("role"), (entry.get("text") or "").strip()
        if role == "question":
            if not seen_role_question:
                seen_role_question = True
                pending = "__role__"
                continue
            pending = text
        elif role == "answer" and pending is not None:
            if pending != "__role__":
                items.append({"q": pending, "a": text})
            pending = None
    if pending and pending != "__role__":
        items.append({"q": pending, "a": None})
    return items


def _domain(history):
    if session.get("interview_domain"):
        return session["interview_domain"]
    for entry in history:
        if entry.get("role") == "answer" and entry.get("text"):
            return entry["text"].split("\n")[0].strip() or "General"
    return "General"


def record_exit(user_id, settings):
    """Ends the scored assessment the candidate chose to exit. Returns the new result id, or None when nothing was
    recorded (no interview, or only the role question was reached). The saved interview is always erased."""
    from MODULES.LAYER_3_BUSINESS_SERVICES.feedback_email import queue_exit_feedback

    history = load_history(user_id)
    started = any(entry.get("role") == "answer" for entry in history)     # the role question was answered
    result_id = None
    if started:
        transcript = build_transcript(history)
        answered = [item for item in transcript if item["a"]]
        domain = _domain(history)
        if answered:
            conversation = "".join(f"{e['role']}: {e['text']}\n" for e in history)
            prompt = build_evaluation_prompt(practice_mode=None, practice_topic="General", lang_target="English",
                                             difficulty=session.get("interview_difficulty") or settings.default_difficulty,
                                             domain_val=domain, conversation_text=conversation, ended_early=True)
            try:
                score, summary = evaluate_interview(prompt)
                reviewed = True
            except Exception as err:
                print(f"[EXIT REVIEW ERROR] {err}")
                score, summary, reviewed = 0.0, REVIEW_FAILED_SUMMARY, False
        else:
            score, summary, reviewed = 0.0, NO_ANSWER_SUMMARY, False

        try:
            user = db.session.get(User, user_id)
            record = InterviewResult(user_id=user_id, score=score, status=InterviewResult.EXITED_STATUS,
                                     summary=summary, domain=domain, transcript=json.dumps(transcript))
            record_counted_attempt(user, record)
            db.session.commit()
            result_id = record.id
            attach_violations(user_id, result_id)
            if settings.enable_feedback_emails and user and user.email:
                queue_exit_feedback(user.email, full_name=user.full_name, domain=domain, score=score,
                                    answered=len(answered), reviewed=reviewed, report_text=summary if reviewed else "",
                                    session_code=record.session_code, result_id=result_id, when=datetime.now(),
                                    difficulty=session.get("interview_difficulty") or settings.default_difficulty)
        except Exception as err:
            print(f"[EXIT RECORD ERROR] {err}")
            db.session.rollback()

    for key in INTERVIEW_SESSION_KEYS:
        session.pop(key, None)
    session.modified = True
    clear_progress(user_id)
    return result_id
