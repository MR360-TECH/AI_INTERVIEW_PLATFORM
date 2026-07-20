from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1817@localhost/ai_interview_platform'
db = SQLAlchemy(app)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_NAME = "gemini-flash-lite-latest"


import re

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

MIN_QUESTIONS = 3
MAX_QUESTIONS = 8
PASS_SCORE = 3
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    gender = db.Column(db.String(10))
    education = db.Column(db.String(50))
    course = db.Column(db.String(100))
    semester = db.Column(db.String(20))
    registered_at = db.Column(db.DateTime, server_default=db.func.now())


class InterviewResult(db.Model):
    __tablename__ = 'interview_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Numeric(4, 2))
    status = db.Column(db.String(20))
    strengths = db.Column(db.Text)
    improvements = db.Column(db.Text)
    interview_datetime = db.Column(db.DateTime, server_default=db.func.now())


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        gender = request.form.get("gender")
        education = request.form.get("education")
        course = request.form.get("course")
        semester = request.form.get("semester")

        if not is_valid_email(email):
            return render_template("register.html", error="Please enter a valid email address.")

        if email == ADMIN_EMAIL:
            return render_template("register.html", error="This email is reserved. Please use a different email.")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template("register.html", error="Email already registered. Please login.")

        hashed_pw = generate_password_hash(password)
        new_user = User(
            full_name=full_name,
            email=email,
            password=hashed_pw,
            gender=gender,
            education=education,
            course=course,
            semester=semester
        )
        db.session.add(new_user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if not is_valid_email(email):
            return render_template("login.html",error="please enter a valid email address.")

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session.clear()
            session["is_admin"] = True
            session["user_name"] = "Admin"
            return redirect("/admin")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.full_name
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html", name=session["user_name"])


@app.route("/admin")
def admin():
    if "user_id" in session:
        return redirect("/dashboard")
    if not session.get("is_admin"):
        return redirect("/login")

    from datetime import date
    today = date.today()

    filter_type = request.args.get("filter", "all")

    all_results = db.session.query(InterviewResult, User).join(User, InterviewResult.user_id == User.id).order_by(InterviewResult.interview_datetime.desc()).all()

    today_count = sum(1 for r, u in all_results if r.interview_datetime.date() == today)
    total_count = len(all_results)

    if filter_type == "today":
        results = [(r, u) for r, u in all_results if r.interview_datetime.date() == today]
    else:
        results = all_results

    return render_template("admin.html", results=results, today_count=today_count, total_count=total_count, filter_type=filter_type)


@app.route("/admin/delete/<int:result_id>")
def delete_result(result_id):
    if not session.get("is_admin"):
        return redirect("/login")

    record = InterviewResult.query.get(result_id)
    if record:
        db.session.delete(record)
        db.session.commit()

    return redirect("/admin")

@app.route("/admin/delete-user/<int:user_id>")
def delete_user(user_id):
    if not session.get("is_admin"):
        return redirect("/login")

    InterviewResult.query.filter_by(user_id=user_id).delete()

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)

    db.session.commit()

    return redirect("/admin")


@app.route("/admin/user/<int:user_id>")
def admin_user_detail(user_id):
    if not session.get("is_admin"):
        return redirect("/login")

    user = User.query.get(user_id)
    if not user:
        return redirect("/admin")

    interviews = InterviewResult.query.filter_by(user_id=user_id).order_by(InterviewResult.interview_datetime.desc()).all()

    return render_template("admin_user_detail.html", user=user, interviews=interviews)


@app.route("/interview", methods=["GET", "POST"])
def interview():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    if "chat_history" not in session:
        session["chat_history"] = []
        session["q_count"] = 0

    if request.method == "POST":
        answer = request.form["answer"]
        session["chat_history"].append({"role": "answer", "text": answer})
        session["q_count"] += 1
        session.modified = True

    if session["q_count"] >= MAX_QUESTIONS:
        return redirect("/interview-result")

    conversation_text = ""
    for entry in session["chat_history"]:
        conversation_text += entry["role"] + ": " + entry["text"] + "\n"

    try:
        if session["q_count"] == 0:
            prompt = "You are an interviewer starting a mock job interview. Ask the candidate which role or domain they are interviewing for (e.g. Software Engineer, Marketing, Data Analyst). Only output the question, nothing else."
        else:
            can_end = session["q_count"] >= MIN_QUESTIONS
            if can_end:
                end_instruction = "You have asked at least 5 questions already, which is normally enough to judge a candidate. Strongly prefer ending now unless the candidate's answers were too short or vague to evaluate confidently. If you decide to end, output exactly: INTERVIEW_COMPLETE and nothing else. Only continue asking if truly necessary, and if so, ask"
            else:
                end_instruction = "Ask"

            prompt = "You are an interviewer conducting a mock job interview. Conversation so far (the first answer tells you the candidate's role/domain): " + conversation_text + " " + end_instruction + " ONE short, clear next interview question relevant to that role, going deeper based on their previous answers. Do not repeat previous questions. Only output the question (or INTERVIEW_COMPLETE), nothing else."

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        question_text = response.text.strip()

    except Exception as e:
        return "AI error: " + str(e)

    if question_text == "INTERVIEW_COMPLETE":
        return redirect("/interview-result")

    session["chat_history"].append({"role": "question", "text": question_text})
    session.modified = True

    return render_template("interview.html", question=question_text, q_num=session["q_count"] + 1, total=MAX_QUESTIONS)


@app.route("/interview-result")
def interview_result():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    conversation_text = ""
    for entry in session.get("chat_history", []):
        conversation_text += entry["role"] + ": " + entry["text"] + "\n"

    try:
        prompt = "You are an interview evaluator. Based on this mock interview conversation, respond in EXACTLY this format, nothing else, no markdown symbols like ** or #:\nSCORE: [a number out of 10]\nSTRENGTHS:\n1. [point]\n2. [point]\nIMPROVEMENTS:\n1. [point]\n2. [point]\n\nConversation: " + conversation_text

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        evaluation = response.text.strip()

        score = "N/A"
        strengths = []
        improvements = []
        current_section = None

        for raw_line in evaluation.split("\n"):
            line = raw_line.strip()
            if not line:
                continue

            upper_line = line.upper()

            if upper_line.startswith("SCORE"):
                score = line.split(":", 1)[-1].strip()
                current_section = None
            elif upper_line.startswith("STRENGTH"):
                current_section = "strengths"
            elif upper_line.startswith("IMPROVEMENT") or upper_line.startswith("AREAS"):
                current_section = "improvements"
            elif current_section:
                cleaned = line.lstrip("0123456789.-)*• ").strip()
                if cleaned:
                    if current_section == "strengths":
                        strengths.append(cleaned)
                    else:
                        improvements.append(cleaned)

        if not strengths:
            strengths = ["Not enough data to determine strengths."]
        if not improvements:
            improvements = ["Not enough data to determine improvements."]

        try:
            score_num = float(score.split("/")[0].strip())
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

        verdict = "Selected" if score_num >= PASS_SCORE else "Rejected"

        if verdict == "Selected":
            verdict_message = "🎉 Congratulations! You've been selected."
        else:
            verdict_message = "Better luck next time. Keep practicing!"

        result_record = InterviewResult(
            user_id=session["user_id"],
            score=score_num,
            status=verdict,
            strengths="; ".join(strengths),
            improvements="; ".join(improvements)
        )
        db.session.add(result_record)
        db.session.commit()

    except Exception as e:
        return "AI error: " + str(e)

    session.pop("chat_history", None)
    session.pop("q_count", None)

    return render_template(
        "interview_result.html",
        score=score,
        score_percent=score_percent,
        label=label,
        label_color=label_color,
        strengths=strengths,
        improvements=improvements,
        verdict=verdict,
        verdict_message=verdict_message
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)