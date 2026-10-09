import os
import re
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, jsonify, url_for, current_app
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db
from MODULES.LAYER_2_DATA_PERSISTENCE.models import (
    User,
    InterviewResult,
    InterviewProgress,
    allowed_file,
    allowed_resume_file,
    get_settings,
    save_progress,
    clear_progress,
    record_counted_attempt,
    attach_violations
)
from MODULES.LAYER_3_BUSINESS_SERVICES import integrity
from MODULES.LAYER_3_BUSINESS_SERVICES.exit_report import has_unfinished_assessment
from MODULES.LAYER_3_BUSINESS_SERVICES.feedback_email import queue_assessment_feedback
from MODULES.LAYER_3_BUSINESS_SERVICES.ai_client import (
    analyze_attachment,
    attachment_analysis_failed,
    generate_text,
    pick_fallback_question,
    trim_history_for_prompt,
    build_initial_question_prompt,
    build_subsequent_question_prompt,
    build_ajax_system_prompt,
    build_evaluation_prompt,
    evaluate_interview
)

interview_bp = Blueprint('interview_bp', __name__)


def extract_domain_from_history(history, fallback="General"):
    """Recovers the candidate's chosen domain/role from their first answer in chat history."""
    for entry in history:
        if entry.get("role") == "answer" and entry.get("text"):
            first_ans = entry["text"].split("\n")[0].strip()
            first_ans = re.sub(r'\[Candidate Code.*?\]', '', first_ans, flags=re.DOTALL).strip()
            first_ans = re.sub(r'\[Attached file.*?\]', '', first_ans, flags=re.DOTALL).strip()
            if first_ans:
                return first_ans
    return fallback


def _guard_response(guard, as_json=False):
    """Turns a refusal from integrity.guard_session() into a response."""
    if guard.get("terminated"):
        return jsonify({"done": True, "redirect": guard["redirect"]}) if as_json else redirect(guard["redirect"])
    if as_json:
        return jsonify({"error": "interview_open_elsewhere", "message": guard["notice"], "redirect": "/dashboard"}), 409
    return render_template("error.html", code=409, title="Interview already open elsewhere", eyebrow="Integrity check", icon="bi-pc-display",
                           message="This interview is currently open in another browser or device, so it cannot be opened here.",
                           notice=guard["notice"], in_interview=False, back_url="/dashboard", reference=None), 409


def _integrity_view(settings, user_id, is_practice, timer_total, new_question):
    """Extra variables for interview.html: the server-side clock and the integrity features switched on by the admin."""
    if not integrity.proctored(settings, is_practice):
        return {"timer_seconds": timer_total, "timer_total": timer_total, "integrity": None}
    integrity.touch(user_id, new_question=new_question)
    left = integrity.seconds_left(integrity.get_progress(user_id), settings, timer_total)
    return {"timer_seconds": timer_total if left is None else left, "timer_total": timer_total,
            "integrity": integrity.template_context(user_id, settings)}


@interview_bp.route("/interview", methods=["GET", "POST"])
def interview():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    if not os.environ.get("GEMINI_API_KEY"):
        return redirect("/dashboard?error=api_key_missing")

    user_id = session["user_id"]

    settings = get_settings()
    MIN_QUESTIONS = settings.min_questions
    MAX_QUESTIONS = settings.max_questions
    timer_seconds = settings.question_timer_seconds or 90

    # One session at a time (scored assessments only): another browser holding this interview is refused and counted
    if integrity.proctored(settings, bool(session.get("interview_mode") or request.args.get("practice") == "1")):
        guard = integrity.guard_session(user_id, settings)
        if guard:
            return _guard_response(guard)

    # Handle restart FIRST — so the lock check below sees the cleared state
    if request.args.get("restart") == "1":
        # (practice-start always sets interview_mode first, so only a scored save can reach this without it)
        if not session.get("interview_mode") and has_unfinished_assessment(user_id):
            # A saved scored assessment only exists after a server or network problem: it is continued, never
            # discarded for a free fresh start (leaving on purpose is done with Exit, which is evaluated and counted).
            return redirect(url_for("interview_bp.interview"))

        clear_progress(user_id)
        session.pop("chat_history", None)
        session.pop("q_count", None)
        session.pop("resume_summary", None)
        session.pop("resume_choice", None)
        session.pop("interview_domain", None)
        session.pop("interview_difficulty", None)
        if request.args.get("practice") != "1":
            session.pop("interview_mode", None)
            session.pop("practice_topic", None)
            session.pop("lang_target", None)
            session.pop("lang_focus", None)
            session.pop("lang_level", None)
        session.modified = True
        # Redirect to the clean URL: the answer form posts back to the current URL, so keeping
        # ?restart=1 would wipe the saved progress again on every single answer.
        return redirect(url_for("interview_bp.interview"))

    # Enforce attempt limit AFTER restart (so cleared progress is seen correctly)
    is_practice = bool(session.get("interview_mode") or request.args.get("practice") == "1")
    if not is_practice and settings.enable_attempt_limits:
        current_user = db.session.get(User, user_id)
        attempts_used = current_user.get_attempts_used() if current_user else 0
        extra_granted = current_user.extra_allowed_interviews or 0 if current_user else 0
        allowed_total = (settings.default_allowed_interviews or 2) + extra_granted
        _existing_prog = InterviewProgress.query.filter_by(user_id=user_id).first()
        _has_active_prog = False
        if _existing_prog:
            try:
                _h = json.loads(_existing_prog.chat_history or '[]')
                _has_active_prog = bool(len(_h) > 0 or (_existing_prog.q_count is not None and _existing_prog.q_count > 0))
            except Exception:
                _has_active_prog = bool(_existing_prog.q_count and _existing_prog.q_count > 0)
        # Only block if no active in-progress interview
        if attempts_used >= allowed_total and not _has_active_prog:
            return redirect("/dashboard?error=attempts_exceeded")

    # Load chat history from DB
    try:
        _db_progress = InterviewProgress.query.filter_by(user_id=user_id).first()
        chat_history = json.loads(_db_progress.chat_history or '[]') if _db_progress else []
        # The saved interview is the source of truth. After an error or a browser Back, the cookie can be one step
        # ahead of what was actually saved; trusting the database keeps question numbers and the resume point right.
        if _db_progress:
            session["q_count"] = _db_progress.q_count or 0
        elif "q_count" not in session:
            session["q_count"] = 0
    except Exception as db_err:
        print(f"[DB LOAD ERROR] {db_err}")
        db.session.rollback()
        chat_history = session.get("chat_history", [])
    q_count = session.get("q_count", 0)

    # Recover domain and difficulty if missing from session
    if not session.get("interview_domain") and chat_history:
        current_user = db.session.get(User, user_id)
        session["interview_domain"] = extract_domain_from_history(chat_history, current_user.course if current_user and current_user.course else "General")
    if not session.get("interview_difficulty"):
        session["interview_difficulty"] = settings.default_difficulty or "student"

    if request.method == "POST":
        answer = request.form.get("answer", "").strip()
        code_answer = request.form.get("code_answer", "").strip()
        attachment = request.files.get("attachment")
        resume_file = request.files.get("resume")

        if q_count == 0 and not session.get("interview_mode") and resume_file and resume_file.filename and allowed_resume_file(resume_file.filename):
            try:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                ext = resume_file.filename.rsplit('.', 1)[1].lower()
                user = db.session.get(User, user_id)

                resume_file.seek(0)
                file_bytes = resume_file.read()

                if user:
                    resume_analysis = analyze_attachment(
                        file_bytes, resume_file.mimetype,
                        context_hint="Verify this is a candidate resume. If not, output NOT_A_RESUME. Otherwise summarize their role, key skills, and experience level in 2 concise sentences."
                    )
                    if "NOT_A_RESUME" not in resume_analysis:
                        saved_filename = f"user_{user.id}_resume.{ext}"
                        if user.resume_filename and user.resume_filename != saved_filename:
                            old_path = os.path.join(upload_folder, user.resume_filename)
                            if os.path.isfile(old_path):
                                os.remove(old_path)
                        with open(os.path.join(upload_folder, saved_filename), "wb") as f:
                            f.write(file_bytes)
                        user.resume_filename = saved_filename
                        if not attachment_analysis_failed(resume_analysis):
                            user.resume_text = resume_analysis
                            session["resume_summary"] = resume_analysis
                        db.session.commit()
            except Exception as e:
                print(f"Error handling interview resume upload: {e}")
                db.session.rollback()

        if integrity.proctored(settings, bool(session.get("interview_mode"))):
            checked = integrity.check_answer(user_id, settings, answer or code_answer, request.form, timer_seconds)
            if checked["terminated"]:
                return redirect(checked["redirect"])
            if checked["timed_out"] and not (answer or code_answer):
                answer = "[No answer was given before the time limit]"      # the clock ran out: move on, nothing is lost

        if answer or code_answer:
            if q_count == 0:
                if session.get("interview_mode"):
                    session["interview_domain"] = session.get("practice_topic", "Practice")
                else:
                    session["interview_domain"] = answer.strip()
                session["interview_difficulty"] = settings.default_difficulty or "student"

            full_answer = answer
            if code_answer:
                if full_answer:
                    full_answer += "\n\n[Candidate Code Input]:\n" + code_answer
                else:
                    full_answer = "[Candidate Code Input]:\n" + code_answer

            if attachment and attachment.filename and allowed_file(attachment.filename):
                file_bytes = attachment.read()
                mime_type = attachment.mimetype
                analysis = analyze_attachment(
                    file_bytes, mime_type,
                    context_hint="This was attached by the candidate alongside their answer during a job interview."
                )
                full_answer += " [Attached file analysis: " + analysis + "]"

            try:
                chat_history.append({"role": "answer", "text": full_answer})
                q_count += 1
                session["q_count"] = q_count
                session.modified = True
                save_progress(user_id, chat_history, q_count)
            except Exception as save_err:
                print(f"[SAVE PROGRESS ERROR] {save_err}")
                db.session.rollback()

    is_practice = bool(session.get("interview_mode"))
    if not is_practice and q_count >= MAX_QUESTIONS:
        return redirect("/interview-result")

    enable_warning_strikes = getattr(settings, "enable_warning_strikes", True)

    if chat_history and chat_history[-1]["role"] == "question":
        last_question_entry = chat_history[-1]
        last_question = last_question_entry["text"]
        question_type = last_question_entry.get("type", "text")
        return render_template(
            "interview.html",
            question=last_question,
            q_num=q_count + 1,
            total=MAX_QUESTIONS,
            question_type=question_type,
            is_practice=is_practice,
            enable_warning_strikes=enable_warning_strikes,
            **_integrity_view(settings, user_id, is_practice, timer_seconds, new_question=False)
        )

    conversation_text = ""
    for entry in trim_history_for_prompt(chat_history):
        conversation_text += f"{entry['role']}: {entry['text']}\n"
    question_text = ""
    prompt = ""
    try:
        current_user = db.session.get(User, user_id)
        if not session.get("resume_summary") and current_user and current_user.resume_text:
            session["resume_summary"] = current_user.resume_text

        if q_count == 0:
            practice_mode = session.get("interview_mode")
            practice_topic = session.get("practice_topic", "General")

            if practice_mode in ["viva", "lang", "drill", "debate", "convo"]:
                prompt = build_initial_question_prompt(
                    practice_mode=practice_mode,
                    practice_topic=practice_topic,
                    lang_target=session.get("lang_target", "English"),
                    lang_focus=session.get("lang_focus", "conversation"),
                    lang_level=session.get("lang_level", "intermediate")
                )
            else:
                if session.get("resume_summary"):
                    question_text = "Welcome! Based on your resume, which specific role or domain are you interviewing for? [TYPE: TEXT]"
                else:
                    question_text = "Which specific role or domain are you interviewing for? [TYPE: TEXT]"
        else:
            difficulty = session.get("interview_difficulty") or (settings.default_difficulty or "student")
            practice_mode = session.get("interview_mode")
            practice_topic = session.get("practice_topic", "General")

            prompt = build_subsequent_question_prompt(
                practice_mode=practice_mode,
                practice_topic=practice_topic,
                lang_target=session.get("lang_target", "English"),
                lang_focus=session.get("lang_focus", "conversation"),
                lang_level=session.get("lang_level", "intermediate"),
                difficulty=difficulty,
                q_count=q_count,
                min_questions=MIN_QUESTIONS,
                conversation_text=conversation_text,
                resume_summary=session.get("resume_summary") or ""
            )

        if not question_text:
            # conversational practice modes write a short reply plus a follow-up, so they get a little more room
            chatty = session.get("interview_mode") in ("debate", "convo")
            question_text = generate_text(prompt, max_output_tokens=110 if chatty else 80,
                                          temperature={"debate": 0.5, "convo": 0.7}.get(session.get("interview_mode"), 0.2))
    except Exception as e:
        print(f"[INTERVIEW ERROR] {e}")
        db.session.rollback()
        question_text = pick_fallback_question(chat_history)

    if not is_practice and q_count >= MIN_QUESTIONS and ("INTERVIEW_COMPLETE" in question_text.upper() or "[END_INTERVIEW]" in question_text.upper()):
        return redirect("/interview-result")

    # Parse TYPE tag
    question_type = "text"
    match = re.search(r'\[TYPE:\s*([A-Z]+)\]', question_text)
    if match:
        tag_type = match.group(1).lower()
        if tag_type in ["code", "file", "text"]:
            question_type = tag_type
        question_text = re.sub(r'\s*\[TYPE:\s*[A-Z]+\]', '', question_text).strip()

    chat_history.append({"role": "question", "text": question_text, "type": question_type})
    session.modified = True
    save_progress(user_id, chat_history, q_count)

    return render_template(
        "interview.html",
        question=question_text,
        q_num=q_count + 1,
        total=MAX_QUESTIONS,
        question_type=question_type,
        is_practice=is_practice,
        enable_warning_strikes=enable_warning_strikes,
        **_integrity_view(settings, user_id, is_practice, timer_seconds, new_question=True)
    )


@interview_bp.route("/interview/submit", methods=["POST"])
def interview_submit():
    if session.get("is_admin"):
        return jsonify({"redirect": "/admin"})
    if "user_id" not in session:
        return jsonify({"redirect": "/login"})
    if not os.environ.get("GEMINI_API_KEY"):
        return jsonify({"redirect": "/dashboard?error=api_key_missing"})

    user_id = session["user_id"]
    settings = get_settings()
    MIN_QUESTIONS = settings.min_questions
    MAX_QUESTIONS = settings.max_questions

    answer = (request.form.get("answer") or "").strip()
    code_answer = (request.form.get("code_answer") or "").strip()
    is_practice = bool(session.get("interview_mode"))

    if integrity.proctored(settings, is_practice):
        guard = integrity.guard_session(user_id, settings)
        if guard:
            return _guard_response(guard, as_json=True)
        checked = integrity.check_answer(user_id, settings, answer or code_answer, request.form, settings.question_timer_seconds or 90)
        if checked["terminated"]:
            return jsonify({"done": True, "redirect": checked["redirect"]})

    if not answer and not code_answer:
        return jsonify({"error": "empty_answer"})

    full_answer = answer
    if code_answer:
        if full_answer:
            full_answer += "\n\n[Candidate Code]:\n" + code_answer
        else:
            full_answer = "[Candidate Code]:\n" + code_answer

    _submit_progress = InterviewProgress.query.filter_by(user_id=user_id).first()
    submit_history = json.loads(_submit_progress.chat_history or '[]') if _submit_progress else []
    submit_q_count = ((_submit_progress.q_count or 0) if _submit_progress else session.get("q_count", 0)) + 1

    submit_history.append({"role": "answer", "text": full_answer})
    session["q_count"] = submit_q_count
    session.modified = True
    # Persist the answer immediately: if anything below fails, the answer is not lost and no attempt is consumed.
    save_progress(user_id, submit_history, submit_q_count)

    if not is_practice and submit_q_count >= MAX_QUESTIONS:
        return jsonify({"done": True, "redirect": "/interview-result"})

    try:
        current_user = db.session.get(User, user_id)
        if submit_q_count == 1:
            if session.get("interview_mode"):
                session["interview_domain"] = session.get("practice_topic", "Practice")
            else:
                session["interview_domain"] = answer.strip() if answer else (current_user.course if current_user and current_user.course else "Software Engineering")
            session["interview_difficulty"] = settings.default_difficulty or "student"

        domain = session.get("interview_domain") or (current_user.course if current_user and current_user.course else "Software Engineering")
        difficulty = session.get("interview_difficulty") or (settings.default_difficulty or "student")
        resume_summary = session.get("resume_summary") or (current_user.resume_text if current_user and current_user.resume_text else "")

        system_prompt = build_ajax_system_prompt(
            domain=domain,
            difficulty=difficulty,
            resume_summary=resume_summary,
            is_practice=is_practice,
            submit_q_count=submit_q_count,
            min_questions=MIN_QUESTIONS,
            max_questions=MAX_QUESTIONS,
            practice_mode=session.get("interview_mode")
        )

        chat_turns = []
        for msg in trim_history_for_prompt(submit_history):
            role = "user" if msg["role"] == "answer" else "model"
            chat_turns.append({"role": role, "parts": [{"text": msg["text"]}]})

        question_text = generate_text(chat_turns, system_instruction=system_prompt, max_output_tokens=120, temperature=0.3)

        if not is_practice and "[END_INTERVIEW]" in question_text.upper() and submit_q_count >= MIN_QUESTIONS:
            return jsonify({"done": True, "redirect": "/interview-result"})

    except Exception as e:
        print(f"[SUBMIT ERROR] {e}")
        db.session.rollback()
        question_text = pick_fallback_question(submit_history)

    question_type = "text"
    match = re.search(r'\[TYPE:\s*([A-Z]+)\]', question_text)
    if match:
        tag = match.group(1).lower()
        if tag in ["code", "file", "text"]:
            question_type = tag
        question_text = re.sub(r'\s*\[TYPE:\s*[A-Z]+\]', '', question_text).strip()

    submit_history.append({"role": "question", "text": question_text, "type": question_type})
    save_progress(user_id, submit_history, submit_q_count)
    if integrity.proctored(settings, is_practice):
        integrity.touch(user_id, new_question=True)

    return jsonify({
        "question": question_text,
        "q_num": submit_q_count + 1,
        "total": MAX_QUESTIONS,
        "question_type": question_type,
        "done": False,
    })


VIOLATION_KINDS = ("tab_switch", "fullscreen_exit", "paste", "copy")


@interview_bp.route("/interview/violation", methods=["POST"])
def interview_violation():
    """The browser reports an integrity violation. The server counts it, stores it and answers with the exact box to show."""
    if session.get("is_admin") or "user_id" not in session:
        return jsonify({"status": "error", "message": "unauthorized"}), 401
    user_id = session["user_id"]
    settings = get_settings()
    if not integrity.proctored(settings, bool(session.get("interview_mode"))):
        return jsonify({"status": "disabled"})
    data = request.get_json(silent=True) or {}
    kind = data.get("kind")
    if kind not in VIOLATION_KINDS:
        return jsonify({"status": "error", "message": "unknown violation"}), 400
    if not integrity.rule_enabled(settings, kind):
        return jsonify({"status": "disabled"})
    progress = integrity.get_progress(user_id)
    try:
        active = bool(progress and json.loads(progress.chat_history or "[]"))
    except Exception:
        active = bool(progress)
    if not active:
        return jsonify({"status": "ignored", "redirect": "/dashboard"})

    detail = ""
    if kind == "tab_switch":
        try:
            away = max(0, min(3600, int(float(data.get("away_s", 0)))))
        except (TypeError, ValueError):
            away = 0
        detail = f"Away from the exam window for about {away} second{'' if away == 1 else 's'}." if away else "Switched away from the exam window."
    elif kind == "paste":
        detail = "Paste attempted in the answer box."
    elif kind == "copy":
        detail = "Copy or cut attempted on the question text."
    elif kind == "fullscreen_exit":
        detail = "Fullscreen was exited during the assessment."

    outcome = integrity.record(user_id, progress, kind, detail, settings)
    if outcome.get("ignored"):
        return jsonify({"status": "ignored", "strikes": outcome["strikes"], "max": outcome["max"]})
    if outcome.get("terminated"):
        return jsonify({"status": "terminated", "redirect": outcome["redirect"]})
    return jsonify({"status": "counted" if outcome["counted"] else "noted", "box": outcome["box"],
                    "strikes": outcome["strikes"], "max": outcome["max"]})


@interview_bp.route("/interview/heartbeat", methods=["POST"])
def interview_heartbeat():
    """Keeps this browser registered as the active holder of the interview (used by the one-session rule)."""
    if session.get("is_admin") or "user_id" not in session:
        return jsonify({"status": "error"}), 401
    settings = get_settings()
    if not integrity.proctored(settings, bool(session.get("interview_mode"))):
        return jsonify({"status": "ok"})
    progress = integrity.get_progress(session["user_id"])
    if not progress:
        return jsonify({"status": "gone", "redirect": "/dashboard"})
    if settings.proctor_single_session and progress.sid and progress.sid != integrity.current_sid():
        return jsonify({"status": "displaced", "redirect": "/interview"})
    progress.last_seen_at = integrity._now()
    db.session.commit()
    return jsonify({"status": "ok", "strikes": progress.strikes or 0})


@interview_bp.route("/finish-interview", methods=["GET", "POST"])
def finish_interview():
    if "user_id" not in session:
        return redirect("/login")
    return redirect("/interview-result")


@interview_bp.route("/interview-result")
def interview_result():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    # If redirected from proctoring termination
    if request.args.get("terminated") == "1":
        latest_res = InterviewResult.query.filter_by(user_id=session["user_id"]).order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).first()
        summary_val = latest_res.summary if latest_res else "This assessment session was automatically terminated by the automated security proctoring system due to repeated tab switching / window focus loss."
        report_date_val = latest_res.interview_datetime.strftime("%B %d, %Y") if (latest_res and latest_res.interview_datetime) else datetime.now().strftime("%B %d, %Y")
        domain_val = latest_res.domain if (latest_res and latest_res.domain) else "General"
        reason_val = latest_res.termination_reason if (latest_res and latest_res.termination_reason) else "Repeated window focus loss / tab switching detected during active assessment"
        session_code_val = latest_res.session_code if latest_res else "AIS-TERMINATED"
        return render_template(
            "interview_result.html",
            score=0,
            score_percent=0,
            label="Disqualified",
            label_color="#e74a3b",
            summary=summary_val,
            verdict="Terminated (Breach)",
            verdict_message="This assessment session was automatically terminated by the automated security proctoring system due to a breach of the Candidate Code of Conduct.",
            is_practice=False,
            candidate_name=session.get("user_name", "Candidate"),
            report_date=report_date_val,
            domain=domain_val,
            is_terminated=True,
            termination_reason=reason_val,
            session_code=session_code_val
        )

    settings = get_settings()
    PASS_SCORE = settings.pass_score
    user_id = session["user_id"]

    _result_progress = InterviewProgress.query.filter_by(user_id=user_id).first()
    try:
        _result_history = json.loads(_result_progress.chat_history or '[]') if _result_progress else []
    except Exception:
        _result_history = []

    # Nothing to evaluate (page refresh after completion, direct URL, or an interview with zero answers):
    # show the last stored result if there is one. This must NEVER create a result or consume an attempt.
    if not any(entry.get("role") == "answer" for entry in _result_history):
        # Prefer the latest COMPLETED result (PASS/FAIL) — never show a Terminated/Abandoned
        # record as the result page for a genuine completion.
        completed_res = InterviewResult.query.filter(
            InterviewResult.user_id == user_id,
            InterviewResult.is_terminated == False,
            ~InterviewResult.status.in_(["Abandoned (Reset)", "Terminated (Breach)", InterviewResult.EXITED_STATUS])
        ).order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).first()

        latest_res = completed_res or InterviewResult.query.filter_by(
            user_id=user_id
        ).order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).first()

        if not latest_res:
            return redirect("/dashboard")
        if latest_res.is_exited:
            return redirect(f"/my-history/{latest_res.id}")      # the exited-session report (with its answers)

        latest_score = float(latest_res.score or 0)
        is_term = bool(latest_res.is_terminated or (latest_res.status and "Terminated" in latest_res.status))
        score_pct = min(int((latest_score / 10.0) * 100), 100)
        return render_template(
            "interview_result.html",
            score=latest_score,
            score_percent=score_pct,
            label="Disqualified" if is_term else ("Completed" if latest_score >= PASS_SCORE else "Needs Improvement"),
            label_color="#e74a3b" if is_term else ("#1cc88a" if latest_score >= PASS_SCORE else "#f6c23e"),
            summary=latest_res.summary,
            verdict="Terminated (Breach)" if is_term else latest_res.status,
            verdict_message="This assessment session was automatically terminated by the automated security proctoring system due to a breach of the Candidate Code of Conduct." if is_term else "Your official evaluation report is recorded.",
            is_practice=False,
            candidate_name=session.get("user_name", "Candidate"),
            report_date=latest_res.interview_datetime.strftime("%B %d, %Y") if latest_res.interview_datetime else datetime.now().strftime("%B %d, %Y"),
            domain=latest_res.domain or "General",
            is_terminated=is_term,
            termination_reason=latest_res.termination_reason or "Repeated window focus loss / tab switching detected during active assessment",
            session_code=latest_res.session_code
        )

    conversation_text = ""
    for entry in _result_history:
        conversation_text += entry["role"] + ": " + entry["text"] + "\n"

    is_practice = bool(session.get("interview_mode"))
    domain_val = session.get("interview_domain") or extract_domain_from_history(_result_history)

    # Evaluate first, store second. If the AI or the database fails for ANY reason we keep the saved
    # answers, store nothing and charge nothing, so the candidate can simply retry.
    try:
        prompt = build_evaluation_prompt(
            practice_mode=session.get("interview_mode"),
            practice_topic=session.get("practice_topic", "General"),
            lang_target=session.get("lang_target", "English"),
            difficulty=session.get("interview_difficulty", "student"),
            domain_val=domain_val,
            conversation_text=conversation_text
        )
        score_num, summary_text = evaluate_interview(prompt)

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

        if is_practice:
            if score_num >= PASS_SCORE:
                verdict = "WELL DONE"
                verdict_message = "You are on the right track. Keep up the great work!"
            else:
                verdict = "ALMOST"
                verdict_message = "A little more practice needed. You are getting closer — keep going!"
            db_verdict = f"{verdict} (Practice)"
        else:
            verdict = "PASS" if score_num >= PASS_SCORE else "FAIL"
            if verdict == "PASS":
                verdict_message = "Congratulations! You have met the recruitment selection criteria and successfully passed the assessment."
            else:
                verdict_message = "Thank you for taking the assessment. We regret that you did not meet the selection threshold for this placement round. Keep developing your skills."
            db_verdict = verdict

        result_record = InterviewResult(
            user_id=user_id,
            score=score_num,
            status=db_verdict,
            summary=summary_text,
            domain=domain_val
        )
        if is_practice:
            db.session.add(result_record)
        else:
            record_counted_attempt(db.session.get(User, user_id), result_record)
        db.session.commit()
        session_code_val = result_record.session_code
        result_id_val = result_record.id
        if not is_practice:
            attach_violations(user_id, result_id_val)

    except Exception as e:
        print(f"[RESULT EVALUATION ERROR] {e}")
        db.session.rollback()
        return redirect("/dashboard?error=evaluation_failed")

    # Feedback email for scored assessments only (admin can switch it off). It runs in the background and
    # can never affect the result.
    if not is_practice and settings.enable_feedback_emails:
        try:
            candidate = db.session.get(User, user_id)
            if candidate and candidate.email:
                queue_assessment_feedback(
                    candidate.email,
                    full_name=candidate.full_name, domain=domain_val, score=score_num, pass_score=PASS_SCORE,
                    answer_count=sum(1 for entry in _result_history if entry.get("role") == "answer"),
                    report_text=summary_text, session_code=session_code_val, result_id=result_id_val,
                    when=datetime.now(),
                    difficulty=session.get("interview_difficulty") or settings.default_difficulty)
        except Exception as mail_err:
            print(f"[MAIL] feedback email not queued: {mail_err}")

    session.pop("chat_history", None)
    session.pop("q_count", None)
    session.pop("resume_choice", None)
    session.pop("resume_summary", None)
    session.pop("interview_domain", None)
    session.pop("interview_difficulty", None)
    session.pop("interview_mode", None)
    session.pop("practice_topic", None)
    session.pop("lang_target", None)
    session.pop("lang_focus", None)
    session.pop("lang_level", None)
    clear_progress(user_id)

    return render_template(
        "interview_result.html",
        score=score_num,
        score_percent=score_percent,
        label=label,
        label_color=label_color,
        summary=summary_text,
        verdict=verdict,
        verdict_message=verdict_message,
        is_practice=is_practice,
        candidate_name=session.get("user_name", "Candidate"),
        report_date=datetime.now().strftime("%B %d, %Y"),
        domain=domain_val,
        session_code=session_code_val
    )
