"""Rapid Fire: a multiple-choice speed quiz. Deliberately kept separate from interview_engine.py - it shares
no routes, no templates and no session keys with the normal interview flow, so nothing here can regress the
chat-based assessment/practice modes. All questions are generated in a single AI call up front (see
ai_client.generate_mcq_quiz); scoring is plain right/wrong matching, so no AI evaluation call is needed either."""
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, url_for

from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db
from MODULES.LAYER_2_DATA_PERSISTENCE.models import InterviewResult, User
from MODULES.LAYER_3_BUSINESS_SERVICES.ai_client import generate_mcq_quiz

rapid_fire_bp = Blueprint('rapid_fire_bp', __name__)

RAPIDFIRE_MARKER = "RAPIDFIRE_JSON::"


@rapid_fire_bp.route("/rapid-fire", methods=["GET", "POST"])
def rapid_fire():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")
    if session.get("interview_mode") != "rapid":
        return redirect("/practice-setup")

    quiz = session.get("rapid_quiz")
    if not quiz:
        topic = session.get("practice_topic") or "General Knowledge"
        quiz = generate_mcq_quiz(topic)
        session["rapid_quiz"] = quiz
        session["rapid_idx"] = 0
        session["rapid_answers"] = []
        session.modified = True

    idx = session.get("rapid_idx", 0)

    if request.method == "POST":
        try:
            selected = int(request.form.get("selected", -1))
        except (TypeError, ValueError):
            selected = -1
        if 0 <= selected <= 3 and idx < len(quiz):
            answers = session.get("rapid_answers", [])
            answers.append(selected)
            session["rapid_answers"] = answers
            idx += 1
            session["rapid_idx"] = idx
            session.modified = True

        if idx >= len(quiz):
            return _finish_quiz()
        return redirect(url_for("rapid_fire_bp.rapid_fire"))

    if idx >= len(quiz):
        return _finish_quiz()

    question = quiz[idx]
    return render_template(
        "rapid_fire.html",
        question=question["question"],
        options=question["options"],
        q_num=idx + 1,
        total=len(quiz),
        topic=session.get("practice_topic") or "General Knowledge",
    )


def _finish_quiz():
    user_id = session["user_id"]
    quiz = session.get("rapid_quiz", [])
    answers = session.get("rapid_answers", [])
    topic = session.get("practice_topic") or "General Knowledge"

    breakdown = []
    correct_count = 0
    for i, q in enumerate(quiz):
        chosen = answers[i] if i < len(answers) else -1
        is_correct = chosen == q["correct_index"]
        if is_correct:
            correct_count += 1
        breakdown.append({
            "question": q["question"],
            "options": q["options"],
            "chosen_index": chosen,
            "correct_index": q["correct_index"],
            "explanation": q.get("explanation", ""),
        })

    total = len(quiz) or 1
    score_num = round((correct_count / total) * 10, 1)

    result_record = InterviewResult(
        user_id=user_id,
        score=score_num,
        status="Rapid Fire (Practice)",
        summary=RAPIDFIRE_MARKER + json.dumps({"topic": topic, "correct": correct_count, "total": total, "items": breakdown}),
        domain=topic,
    )
    db.session.add(result_record)
    db.session.commit()
    result_id = result_record.id

    session.pop("interview_mode", None)
    session.pop("practice_topic", None)
    session.pop("rapid_quiz", None)
    session.pop("rapid_idx", None)
    session.pop("rapid_answers", None)
    session.modified = True

    return redirect(f"/rapid-fire-result/{result_id}")


@rapid_fire_bp.route("/rapid-fire-result/<int:result_id>")
def rapid_fire_result(result_id):
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    result = InterviewResult.query.filter_by(id=result_id, user_id=session["user_id"]).first()
    if not result or not (result.summary or "").startswith(RAPIDFIRE_MARKER):
        return redirect("/dashboard")

    data = json.loads(result.summary[len(RAPIDFIRE_MARKER):])
    return render_template(
        "rapid_fire_result.html",
        score=float(result.score or 0),
        correct=data.get("correct", 0),
        total=data.get("total", 0),
        domain=result.domain or data.get("topic", "General"),
        items=data.get("items", []),
        candidate_name=session.get("user_name", "Candidate"),
        report_date=result.interview_datetime.strftime("%B %d, %Y") if result.interview_datetime else datetime.now().strftime("%B %d, %Y"),
        session_code=result.session_code,
    )


@rapid_fire_bp.route("/rapid-fire/quit", methods=["POST"])
def rapid_fire_quit():
    if "user_id" not in session:
        return redirect("/login")
    session.pop("interview_mode", None)
    session.pop("practice_topic", None)
    session.pop("rapid_quiz", None)
    session.pop("rapid_idx", None)
    session.pop("rapid_answers", None)
    session.modified = True
    return redirect("/dashboard")
