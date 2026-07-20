
BuddyGood instinct — hiding setup/access details from a public repo makes sense for a college project. Here's the revised version with those two sections removed and replaced with more presentation-friendly content instead.

# 🎯 AI Interview Platform

### Practice interviews the smart way — with an AI that actually listens.

An intelligent, full-stack mock interview platform that conducts real, adaptive interviews and evaluates candidates the way a human interviewer would — powered by Google's Gemini AI.



---

## 💡 Why This Project Exists

Most "mock interview" tools just recycle the same fixed question bank for everyone. This platform doesn't.

Every interview here is generated live — the AI listens to how a candidate answers, then decides what to ask next, just like a real interviewer would probe deeper based on your responses. No two interviews are ever the same, even for the same role.

At the end, instead of a generic pass/fail, the candidate gets a real evaluation: a score, specific strengths, specific gaps — and a clear verdict.

---

## ✨ What It Does

| | |
|---|---|
| 🔐 **Secure Accounts** | Registration & login with hashed passwords, session-based auth |
| 🤖 **Adaptive AI Interviews** | 5–8 dynamically generated questions, tailored to the candidate's answers in real time |
| 📊 **Instant AI Evaluation** | Score out of 10, key strengths, and specific improvement areas — generated fresh each time |
| ✅ **Selection Verdict** | Automatic Selected / Rejected decision based on performance threshold |
| 🗂️ **Candidate Profiles** | Captures education level, course, and semester at registration |
| 🛡️ **Admin Command Center** | Full dashboard — filter by today/all-time, drill into any candidate's full profile, manage records |

---

## 🧠 How the AI Interview Works

1. **Domain Discovery** — The first question always asks which role the candidate is interviewing for
2. **Adaptive Questioning** — Each following question is generated based on the entire conversation so far, going deeper into relevant topics
3. **Smart Wrap-Up** — After a minimum of 5 questions, the AI itself decides when it has enough information to judge the candidate (up to a max of 8)
4. **Structured Evaluation** — The full conversation is analyzed to produce a score, strengths, and areas for improvement
5. **Verdict** — A pass threshold determines whether the candidate is marked *Selected* or *Rejected*

This mirrors how a real interviewer thinks — not a fixed script, but a conversation that adapts.

---

## 🏗️ Built With

```
Backend      →  Python · Flask
Database     →  MySQL (via Flask-SQLAlchemy)
Intelligence →  Google Gemini API
Frontend     →  HTML5 · Bootstrap 5
Security     →  Werkzeug password hashing · Flask sessions
```

---

## 📂 Project Structure

```
ai_interview_platform/
├── app.py                     ← Application core
├── requirements.txt
├── static/
│   └── style.css
└── templates/
    ├── index.html
    ├── register.html
    ├── login.html
    ├── dashboard.html
    ├── interview.html
    ├── interview_result.html
    ├── admin.html
    └── admin_user_detail.html
```

---

## 🗄️ Database Design

**`users`**
Stores every candidate's profile — name, email, hashed password, education level, course, and semester.

**`interview_results`**
Stores every completed interview attempt — score, verdict, AI-generated strengths/improvements, and timestamp — linked back to `users` through a foreign key, so a candidate's full history is always traceable.

---

## 🎓 What I Learned Building This

This project took me through the full stack — from designing a relational database, to building secure authentication, to integrating a live external AI API and handling its real-world quirks (rate limits, model deprecation, structured prompt engineering). It taught me how much of real software development is about handling the unexpected gracefully, not just writing the "happy path" code.

---

## 🔮 Roadmap

- [ ] Public cloud deployment
- [ ] Voice-based interviews
- [ ] Downloadable PDF candidate reports
- [ ] Multi-language question support

---

## 👤 Author

**Gowtham V**

---

## 📄 License

Built for academic purposes as part of the academic curriculum.

---

Copy everything from `# 🎯 AI Interview Platform` down to `Built for academic purposes as part of the BCA curriculum.` and paste it into your GitHub README, replacing the previous version.

