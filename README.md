

# 🎯 AI Interview Platform

An AI-powered mock interview web application that helps candidates practice job interviews with real-time, adaptive questioning and instant performance evaluation.



## 📖 About

This platform simulates a real job interview experience using Google's Gemini AI. Instead of static, pre-written questions, the AI dynamically generates each question based on the candidate's role and their previous answers — making every interview unique and adaptive.

After the interview, the AI evaluates the candidate's performance and provides a score out of 10, key strengths, areas for improvement, and a final verdict — Selected or Rejected.

All interview data is securely stored in a MySQL database, with a dedicated admin dashboard to review candidate performance.

## ✨ Features

- Secure Authentication — Registration and login with hashed passwords
- Dynamic AI Interviews — Adaptive questions generated in real-time based on candidate responses (5–8 questions per session)
- AI-Powered Evaluation — Automatic scoring, strengths, and improvement feedback
- Selection Verdict — Automatic Selected/Rejected decision based on performance
- Admin Dashboard — View all candidates, filter by today/all-time, view detailed candidate profiles, and manage records
- Candidate Profiles — Captures education level, course, and semester during registration

## 🛠️ Tech Stack

Backend — Python, Flask
Database — MySQL via Flask-SQLAlchemy
AI — Google Gemini API
Frontend — HTML, Bootstrap 5
Auth — Werkzeug password hashing, Flask sessions

## ⚙️ Setup & Installation

1. Clone the repository: `git clone https://github.com/MR360-TECH/AI_INTERVIEW_PLATFORM.git` then `cd AI_INTERVIEW_PLATFORM`
2. Install dependencies: `pip install flask flask_sqlalchemy pymysql werkzeug google-genai python-dotenv`
3. Set up MySQL by creating a database named `ai_interview_platform` and updating the database connection string in `app.py` with your MySQL credentials
4. Add your Gemini API key by creating a `.env` file in the project root with `GEMINI_API_KEY=your_api_key_here`, obtainable free at Google AI Studio
5. Run the app with `python app.py` and visit `http://127.0.0.1:5000` in your browser

## 🔐 Admin Access

Admin credentials are configured directly in `app.py`. Log in with the admin email/password to access the dashboard at `/admin`.

## 📊 Database Schema

The `users` table stores candidate registration details — name, email, password, education, course, and semester.
The `interview_results` table stores each interview attempt — score, status, strengths, improvements, and timestamp — linked to `users` via foreign key.

## 🚀 Future Improvements

Public deployment for remote access, voice-based interview support, export candidate reports as PDF, and multi-language question support.

## 👤 Author

**Gowtham V**


## 📝 License

This project was built for academic purposes as part of a BCA curriculum.

---

T
