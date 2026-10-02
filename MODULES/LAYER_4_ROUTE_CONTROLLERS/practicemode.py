import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, jsonify, url_for
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db
from MODULES.LAYER_3_BUSINESS_SERVICES.feedback_email import queue_terminated_notice
from MODULES.LAYER_2_DATA_PERSISTENCE.models import User, InterviewResult, InterviewProgress, clear_progress, record_counted_attempt, attach_violations

practice_bp = Blueprint('practice_bp', __name__)


@practice_bp.route("/practice-setup")
def practice_setup():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")
    return render_template("practice_setup.html")


@practice_bp.route("/practice-start", methods=["POST"])
def practice_start():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    mode = request.form.get("mode")
    if mode not in ("viva", "lang", "drill", "debate", "convo"):
        return redirect("/practice-setup")

    viva_subject = request.form.get("viva_subject", "").strip()
    drill_subject = request.form.get("drill_subject", "").strip()

    session["interview_mode"] = mode
    if mode == "viva":
        session["practice_topic"] = viva_subject or "General Knowledge"
    elif mode == "drill":
        session["practice_topic"] = drill_subject or "General Concepts"
    elif mode == "debate":
        session["practice_topic"] = "Debate Practice"        # the AI asks for the topic and side in its opening line
    elif mode == "convo":
        session["practice_topic"] = "Healthy Conversation"   # the AI asks what to talk about in its opening line
    else:
        lang_target = request.form.get("lang_target", "").strip()
        lang_focus = request.form.get("lang_focus", "conversation").strip() or "conversation"
        lang_level = request.form.get("lang_level", "intermediate").strip() or "intermediate"

        session["lang_target"] = lang_target or "English"
        session["lang_focus"] = lang_focus
        session["lang_level"] = lang_level
        session["practice_topic"] = f"{session['lang_target']} ({lang_focus.capitalize()})"

    return redirect(url_for("interview_bp.interview", restart="1", practice="1"))


@practice_bp.route("/quit-interview", methods=["POST"])
def quit_interview():
    if "user_id" not in session:
        return redirect("/login")
    session.pop("chat_history", None)
    session.pop("q_count", None)
    session.pop("interview_mode", None)
    session.pop("practice_topic", None)
    session.pop("lang_target", None)
    session.pop("lang_focus", None)
    session.pop("lang_level", None)
    session.pop("interview_domain", None)
    session.pop("interview_difficulty", None)
    session.pop("resume_summary", None)
    clear_progress(session["user_id"])
    return redirect("/dashboard")


@practice_bp.route("/reset-assessment", methods=["POST"])
def reset_assessment():
    if "user_id" not in session:
        return jsonify({"status": "error", "reason": "not_logged_in"}), 401
    user_id = session["user_id"]
    is_practice = bool(session.get("interview_mode"))
    domain_val = session.get("interview_domain", "General")

    # Check DB for actual progress (more reliable than session q_count)
    db_progress = InterviewProgress.query.filter_by(user_id=user_id).first()
    has_real_progress = bool(db_progress and db_progress.q_count and db_progress.q_count > 0)

    if not is_practice and has_real_progress:
        try:
            res_rec = InterviewResult(
                user_id=user_id,
                score=0.0,
                status="Abandoned (Reset)",
                summary="Candidate initiated a fresh session reset mid-assessment.",
                domain=domain_val
            )
            db.session.add(res_rec)
            db.session.commit()
            attach_violations(user_id, res_rec.id)
        except Exception as e:
            print(f"[RESET ASSESSMENT LOG ERROR] {e}")
            db.session.rollback()

    session.pop("chat_history", None)
    session.pop("q_count", None)
    session.pop("interview_mode", None)
    session.pop("practice_topic", None)
    session.pop("lang_target", None)
    session.pop("lang_focus", None)
    session.pop("lang_level", None)
    session.pop("interview_domain", None)
    session.pop("interview_difficulty", None)
    session.pop("resume_summary", None)
    session.pop("resume_choice", None)
    session.modified = True
    clear_progress(user_id)
    return jsonify({"status": "ok"})


@practice_bp.route("/terminate-proctoring", methods=["POST"])
def terminate_proctoring():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "unauthorized"}), 401

    user_id = session["user_id"]

    # Only a live, scored assessment can be terminated. Practice sessions are never proctored, and a repeated
    # call (second tab, double-fired event) finds the progress already cleared, so nothing is charged twice.
    progress = InterviewProgress.query.filter_by(user_id=user_id).first()
    try:
        has_active_interview = bool(progress and json.loads(progress.chat_history or '[]'))
    except Exception:
        has_active_interview = bool(progress)
    if session.get("interview_mode") or not has_active_interview:
        return jsonify({"status": "ignored", "redirect": "/dashboard"})

    domain_val = session.get("interview_domain", "General")

    reason = "Repeated window focus loss / tab switching detected during active assessment"
    summary_msg = (
        "SESSION ENDED EARLY:\n\n"
        "This assessment session was closed automatically by the proctoring system because window focus loss "
        "or tab switching was detected on multiple occasions during the session.\n\n"
        "The session has been recorded as terminated and no evaluation score was generated. "
        "It remains available for administrator review."
    )

    try:
        result_record = InterviewResult(
            user_id=user_id,
            score=0.0,
            status="Terminated (Breach)",
            summary=summary_msg,
            domain=domain_val,
            is_terminated=True,
            termination_reason=reason
        )
        user_obj = db.session.get(User, user_id)
        record_counted_attempt(user_obj, result_record)
        db.session.commit()
        attach_violations(user_id, result_record.id)
        if user_obj and user_obj.email:
            queue_terminated_notice(
                user_obj.email, full_name=user_obj.full_name, domain=domain_val,
                session_code=result_record.session_code, result_id=result_record.id, when=datetime.now())
    except Exception as db_err:
        print(f"Error recording proctoring termination: {db_err}")
        db.session.rollback()

    session.pop("chat_history", None)
    session.pop("q_count", None)
    session.pop("resume_choice", None)
    session.pop("resume_summary", None)
    session.pop("interview_domain", None)
    session.pop("interview_difficulty", None)
    session.pop("interview_mode", None)
    session.pop("practice_topic", None)
    session.modified = True
    clear_progress(user_id)

    return jsonify({"status": "terminated", "redirect": "/interview-result?terminated=1"})
