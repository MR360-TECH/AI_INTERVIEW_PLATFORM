import os
import re
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, session, send_from_directory, current_app, jsonify
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db, FEEDBACK_TO_EMAIL
from MODULES.LAYER_2_DATA_PERSISTENCE.models import (
    User,
    InterviewResult,
    InterviewProgress,
    Feedback,
    profile_is_complete,
    allowed_resume_file,
    get_settings,
    clear_progress,
    save_resume_file,
    delete_resume_file,
    resume_response
)
from MODULES.LAYER_3_BUSINESS_SERVICES.ai_client import analyze_attachment, attachment_analysis_failed
from MODULES.LAYER_3_BUSINESS_SERVICES.feedback_email import queue_feedback_notification

dashboard_bp = Blueprint('dashboard_bp', __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    current_user = db.session.get(User, session["user_id"])
    if not current_user:
        session.clear()
        return redirect("/login")

    if not profile_is_complete(current_user):
        return redirect("/register")

    progress = InterviewProgress.query.filter_by(user_id=session["user_id"]).first()
    has_progress = False
    if progress:
        try:
            chat_hist = json.loads(progress.chat_history or '[]')
            has_progress = bool(len(chat_hist) > 0 or (progress.q_count is not None and progress.q_count > 0))
        except Exception:
            has_progress = bool(progress.q_count and progress.q_count > 0)

    recent_results = InterviewResult.query.filter(
        InterviewResult.user_id == session["user_id"],
        InterviewResult.real_attempt_filter()
    ).order_by(InterviewResult.interview_datetime.desc()).limit(5).all()
    has_result = len(recent_results) > 0

    error_msg = None
    err_code = request.args.get("error")
    if err_code == "file_too_large":
        error_msg = "Uploaded file is too large. The maximum size limit is 10MB."
    elif err_code == "api_key_missing":
        error_msg = "AI Placement evaluation is not configured. Please set the GEMINI_API_KEY environment variable."
    elif err_code == "attempts_exceeded":
        error_msg = "You have reached your allocated assessment attempt limit. Please contact the administrator to request an attempt extension."
    elif err_code == "invalid_file_type":
        error_msg = "Unsupported resume file type. Please upload a PDF, DOC, DOCX, PNG or JPG file."
    elif err_code == "resume_save_failed":
        error_msg = "Your resume could not be saved on the server. Please try again."
    elif err_code == "resume_text_failed":
        error_msg = "Your resume was uploaded, but the AI could not read its text. Recruiters can still open the file; try a clearer PDF if you want the AI interviewer to use it."
    elif err_code == "assessment_in_progress":
        error_msg = "Your assessment was interrupted and is still saved. Continue it (or exit it from the interview screen) before starting a practice session."
    elif err_code == "evaluation_failed":
        error_msg = "The AI evaluation is temporarily unavailable. Your answers are saved and no attempt has been used. Please retry in a moment to get your result."

    # Check attempt limit status (for UI button state)
    settings = get_settings()
    is_locked = False
    attempts_used = 0
    extra_granted = current_user.extra_allowed_interviews or 0 if current_user else 0
    allowed_total = (settings.default_allowed_interviews or 2) + extra_granted
    remaining_tokens = allowed_total

    if settings.enable_attempt_limits:
        attempts_used = current_user.get_attempts_used() if current_user else 0
        remaining_tokens = max(0, allowed_total - attempts_used)
        if attempts_used >= allowed_total and not has_progress:
            is_locked = True

    return render_template("dashboard.html", name=session.get("user_name") or current_user.full_name, user=current_user,
                           has_progress=has_progress, has_result=has_result,
                           recent_results=recent_results, error=error_msg,
                           is_locked=is_locked, attempts_used=attempts_used,
                           allowed_total=allowed_total, remaining_tokens=remaining_tokens,
                           settings=settings, eval_retry=(err_code == "evaluation_failed"))


@dashboard_bp.route("/dashboard/update-resume", methods=["POST"])
def dashboard_update_resume():
    if "user_id" not in session:
        return redirect("/login")
    
    user = db.session.get(User, session["user_id"])
    if not user:
        return redirect("/dashboard")
        
    resume_file = request.files.get("resume_file")

    if resume_file and resume_file.filename:
        filename = resume_file.filename
        if not allowed_resume_file(filename):
            return redirect("/dashboard?error=invalid_file_type")

        ext = filename.rsplit('.', 1)[1].lower()
        file_bytes = resume_file.read()

        # The original file is the source of truth for admins, so record it even if text extraction fails.
        # It is stored in the database (a free host has no permanent disk) and replaces any earlier resume.
        try:
            save_resume_file(user, ext, file_bytes)
        except Exception as e:
            print(f"Error saving uploaded resume: {e}")
            db.session.rollback()
            return redirect("/dashboard?error=resume_save_failed")
        extracted_text = analyze_attachment(
            file_bytes, resume_file.mimetype,
            context_hint="Extract the text content and structure from this resume as cleanly as possible. Provide only the text transcription.",
            max_output_tokens=3000
        )
        text_ok = not attachment_analysis_failed(extracted_text)
        user.resume_text = extracted_text if text_ok else None
        try:
            db.session.commit()
        except Exception as e:
            print(f"Error recording uploaded resume: {e}")
            db.session.rollback()
            return redirect("/dashboard?error=resume_save_failed")
        if not text_ok:
            return redirect("/dashboard?error=resume_text_failed")

    return redirect("/dashboard")


@dashboard_bp.route("/dashboard/remove-resume", methods=["POST"])
def dashboard_remove_resume():
    if "user_id" not in session:
        return redirect("/login")
    user = db.session.get(User, session["user_id"])
    if user:
        delete_resume_file(user)
        user.resume_filename = None
        user.resume_text = None
        db.session.commit()
    return redirect("/dashboard")


@dashboard_bp.route("/uploads/resumes/<filename>")
def view_original_resume(filename):
    if not session.get("is_admin") and "user_id" not in session:
        return redirect("/login")
    if not session.get("is_admin"):
        user = db.session.get(User, session["user_id"])
        if not user or user.resume_filename != filename:
            return "Unauthorized", 403
    owner = db.session.query(User).filter_by(resume_filename=filename).first()
    response = resume_response(owner) if owner else None
    if response is None:
        return "Resume file not found on the server.", 404
    return response


@dashboard_bp.route("/latest-result")
def latest_result():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    result = InterviewResult.query.filter_by(user_id=session["user_id"]).order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).first()

    if not result:
        return redirect("/dashboard")
    if result.is_exited:
        return redirect(f"/my-history/{result.id}")

    is_term = bool(result.is_terminated or (result.status and "Terminated" in result.status))
    if is_term:
        label = "Disqualified"
        label_color = "#e74a3b"
        verdict = "Terminated (Breach)"
        verdict_message = "This assessment session was automatically terminated by the automated security proctoring system due to a breach of the Candidate Code of Conduct."
    else:
        label = "Excellent" if result.score and result.score >= 8 else "Good" if result.score and result.score >= 6 else "Fair" if result.score and result.score >= 4 else "Needs Work"
        label_color = "#1cc88a" if result.score and result.score >= 8 else "#4e73df" if result.score and result.score >= 6 else "#f6c23e" if result.score and result.score >= 4 else "#e74a3b"
        verdict = result.status
        verdict_message = "🎉 Congratulations! You have met the recruitment selection criteria and successfully passed the assessment." if result.status in ("Selected", "PASS") or (result.status and "WELL DONE" in result.status) else "Thank you for taking the assessment. We regret that you did not meet the selection threshold for this placement round. Keep developing your skills."

    return render_template(
        "interview_result.html",
        score=result.score,
        score_percent=min(int((float(result.score) / 10) * 100), 100) if result.score else 0,
        label=label,
        label_color=label_color,
        summary=result.summary,
        verdict=verdict,
        verdict_message=verdict_message,
        candidate_name=session.get("user_name", "Candidate"),
        report_date=result.interview_datetime.strftime("%B %d, %Y") if result.interview_datetime else datetime.now().strftime("%B %d, %Y"),
        domain=result.domain or "General",
        is_terminated=is_term,
        termination_reason=result.termination_reason or "Repeated window focus loss / tab switching detected during active assessment",
        session_code=result.session_code
    )


@dashboard_bp.route("/my-history")
def my_history():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    attempts = InterviewResult.query.filter_by(user_id=session["user_id"]).order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).all()

    return render_template("my_history.html", attempts=attempts)


@dashboard_bp.route("/my-history/<int:result_id>")
def view_past_result(result_id):
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    result = InterviewResult.query.filter_by(id=result_id, user_id=session["user_id"]).first()
    if not result:
        return redirect("/my-history")

    try:
        score_num = float(result.score)
    except:
        score_num = 0

    if score_num >= 8:
        label = "Excellent"
        label_color = "#1cc88a"
    elif score_num >= 6:
        label = "Good"
        label_color = "#4e73df"
    elif score_num >= 4:
        label = "Fair"
        label_color = "#f6c23e"
    else:
        label = "Needs Work"
        label_color = "#e74a3b"

    score_percent = min(int((score_num / 10) * 100), 100)
    verdict = result.status or "FAIL"
    is_terminated = bool(result.is_terminated or (result.status and "Terminated" in result.status))

    if result.is_exited:
        label = "Incomplete"
        label_color = "#f59e0b"
        verdict_message = "You exited this assessment before it was complete. This report covers only the questions you answered."
    elif is_terminated or "Terminated" in str(verdict):
        verdict = "Terminated (Breach)"
        label = "Disqualified"
        label_color = "#e74a3b"
        verdict_message = "This assessment session was automatically terminated by the automated security proctoring system due to a breach of the Candidate Code of Conduct."
    else:
        is_pass = verdict in ("PASS", "Selected") or "WELL DONE" in verdict
        if is_pass:
            verdict_message = "🎉 Congratulations! You have met the recruitment selection criteria and successfully passed the assessment."
        else:
            verdict_message = "Thank you for taking the assessment. We regret that you did not meet the selection threshold for this placement round. Keep developing your skills."

    return render_template(
        "interview_result.html",
        score=score_num,
        score_percent=score_percent,
        label=label,
        label_color=label_color,
        summary=result.summary,
        verdict=verdict,
        verdict_message=verdict_message,
        candidate_name=session.get("user_name", "Candidate"),
        report_date=result.interview_datetime.strftime("%B %d, %Y") if result.interview_datetime else datetime.now().strftime("%B %d, %Y"),
        domain=result.domain or "General",
        is_terminated=is_terminated,
        termination_reason=result.termination_reason or "Repeated window focus loss / tab switching detected during active assessment",
        session_code=result.session_code,
        back_url="/my-history",
        is_exited=result.is_exited
    )


# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK / REVIEWS (sent from the feedback box on the dashboard and on the result pages)
# ══════════════════════════════════════════════════════════════════════════════

FEEDBACK_CATEGORIES = {
    "experience": "My interview experience",
    "suggestion": "A suggestion or new feature",
    "bug": "Something is not working",
    "content": "Questions & prep resources",
    "praise": "A compliment",
    "other": "Something else",
}
FEEDBACK_PAGES = {"dashboard": "Dashboard", "result": "Interview result page"}
FEEDBACK_MIN_CHARS, FEEDBACK_MAX_CHARS, FEEDBACK_MAX_PER_HOUR = 10, 1000, 5


def _feedback_error(message, status):
    return jsonify({"status": "error", "message": message}), status


@dashboard_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    if "user_id" not in session or session.get("is_admin"):
        return _feedback_error("Please log in to send feedback.", 401)
    user = db.session.get(User, session["user_id"])
    if not user:
        return _feedback_error("Please log in to send feedback.", 401)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _feedback_error("Invalid request.", 400)

    message = str(data.get("message") or "").strip()
    if not FEEDBACK_MIN_CHARS <= len(message) <= FEEDBACK_MAX_CHARS:
        return _feedback_error(f"Please write between {FEEDBACK_MIN_CHARS} and {FEEDBACK_MAX_CHARS} characters.", 400)
    category = data.get("category")
    if category not in FEEDBACK_CATEGORIES:
        return _feedback_error("Please choose what your feedback is about.", 400)
    rating = data.get("rating")
    if rating in (None, "", 0):
        rating = None
    else:
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return _feedback_error("Invalid rating.", 400)
        if not 1 <= rating <= 5:
            return _feedback_error("Invalid rating.", 400)
    page = data.get("page") if data.get("page") in FEEDBACK_PAGES else "dashboard"
    session_code = re.sub(r"[^A-Z0-9\-]", "", str(data.get("session_code") or "").upper())[:20]
    contact_ok = bool(data.get("contact_ok", True))

    now = datetime.utcnow()
    recent = Feedback.query.filter(Feedback.user_id == user.id, Feedback.created_at >= now - timedelta(hours=1)).count()
    if recent >= FEEDBACK_MAX_PER_HOUR:
        return _feedback_error("You have sent several messages recently. Please try again a little later.", 429)

    try:
        db.session.add(Feedback(user_id=user.id, rating=rating, category=category, message=message, contact_ok=contact_ok,
                                page=page, session_code=session_code or None, created_at=now))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[FEEDBACK] could not save: {e}")
        return _feedback_error("Could not save your feedback right now. Please try again.", 500)

    # The e-mail is a bonus: the feedback is already saved, and a mail problem must never fail the request.
    queue_feedback_notification(
        FEEDBACK_TO_EMAIL, user_name=user.full_name, user_email=user.email, rating=rating,
        category_label=FEEDBACK_CATEGORIES[category], message=message, page_label=FEEDBACK_PAGES[page],
        session_code=session_code, when_text=now.strftime("%d %B %Y, %H:%M UTC"), contact_ok=contact_ok,
        user_id=user.id,
        account_type="Professional" if user.user_type == "professional" else "Student",
        course_or_role=(user.current_designation if user.user_type == "professional" else user.course) or "",
        member_since=user.registered_at.strftime("%d %B %Y") if user.registered_at else "",
        sign_in_method={"local": "Email and password", "google": "Google", "otp": "Email code"}.get(user.auth_provider, ""),
        reply_to=(user.email if contact_ok else None))
    return jsonify({"status": "ok"})
