# 🤖 AI Interview Platform

A full-stack, AI-powered mock interview web application built to help candidates prepare for technical and non-technical job roles through realistic, adaptive mock interviews. The platform is driven by Google Gemini AI and backed by a relational database schema supporting PostgreSQL, MySQL, and SQLite (fallback).

---

## 🚀 Key Innovation: Adaptive vs. Scripted Q&A

Most online mock interview tools rely on predefined question banks. The system picks $N$ static questions from a database and presents them in a fixed sequence.

This platform operates as a true **conversational state machine**:
* **Zero Scripting**: There is no pre-written question bank. Every single question is generated live and dynamically.
* **Contextual Memory**: The system submits the full transcript of all preceding rounds to the Google Gemini model. The model assesses the candidate's last answer and determines the most logical follow-up question.
* **Performance Adaptation**: The AI naturally probes deeper into weak areas, moves past topics where the candidate demonstrates mastery, and gracefully shifts down to simpler fundamentals if the candidate answers "I don't know."
* **Smart Endings**: Instead of a fixed length, the AI itself decides (between 5 and 8 questions) when it has gathered sufficient signal to output a reliable score and evaluation.

---

## 🛠️ System Architecture & Component Breakdown

The project follows a modular Model-View-Controller style architecture where database operations, AI clients, session controllers, and templates are separated.

### 1. Backend Core (`app.py`)
`app.py` acts as the orchestrator for the entire application. It executes the following roles:
* **Database Mapping & Auto-Migrations**: Defines the models (`User`, `InterviewResult`, `InterviewProgress`, `AdminSettings`) and inspects the schema on boot to dynamically add missing columns (`resume_text`, `resume_filename`) for backward compatibility.
* **Routing State Machine**: Controls candidates' flow through registration, OTP validation, profile completions, active assessments, and dashboard visualizations.
* **Email API Dispatcher**: Prioritizes modern HTTP Email APIs (Resend first, SendGrid second) to bypass port 25/587 blocks common on free-tier hosting platforms like Render, falling back to Gmail SMTP for local testing.
* **Gemini AI Client Interface**: Wraps the new `google-genai` SDK, feeding structured prompt structures to the `gemini-2.0-flash` model.

### 2. Frontend Templates (`templates/`)
A collection of responsive, Bootstrap 5 templates implementing a dark-theme system:
* **Public & Auth Pages**:
  * [`index.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/index.html): Explains the platform features and includes call-to-actions.
  * [`login.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/login.html): Supports local email/password login and redirects to Google OAuth.
  * [`signup.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/signup.html): Step 1 of registration (checks email, triggers OTP).
  * [`verify_otp.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/verify_otp.html): Generic validation UI serving registration and password resets.
  * [`set_password.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/set_password.html): Secure password entry and confirmation screen.
  * [`register.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/register.html): Captures education level, course, semester, skills, years of experience, current designation, and resume uploads.
* **Candidate Panel**:
  * [`dashboard.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/dashboard.html): Displays resume management tools, active interview status, and previous results.
  * [`practice_setup.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/practice_setup.html): Lets candidates select their target domain, difficulty, and experience level.
  * [`interview.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/interview.html): The core assessment console featuring response fields, timer alerts, and a microphone speech recording button.
  * [`interview_result.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/interview_result.html): Visualized dashboard showing overall score, Selected/Rejected badge, executive summary, and bulleted lists of strengths and areas for improvement.
  * [`interview_resume.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/interview_resume.html): Detailed side-by-side display of the full conversation transcript for deep review.
  * [`my_history.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/my_history.html): Chronological table of all completed assessments.
* **Administrator Portal**:
  * [`admin.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/admin.html): Aggregates user metrics, search bars, and database deletion buttons.
  * [`admin_settings.html`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/templates/admin_settings.html): Interface to adjust pass score, question count limits, and difficulty rules.

### 3. Static Client Scripts (`static/`)
* **[`style.css`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/static/css/style.css)**: Implements custom radial gradients, dark-mode cards styling, transition animations, and responsive navigation layouts.
* **[`speech.js`](file:///c:/Users/pavan/OneDrive/Desktop/ai_interview_platform/static/js/speech.js)**: Configures and manages the Web Speech API (`webkitSpeechRecognition`). Handles local microphone access, detects voice inputs, handles punctuation formatting, and dynamically updates text area fields.

---

## 📊 Detailed Database Schema & ER Model

The system uses a relational database schema designed to support local environment fallbacks (SQLite) and enterprise production deployments (MySQL / PostgreSQL).

```mermaid
erDiagram
    users ||--o{ interview_results : "has many"
    users ||--o| interview_progress : "maintains active"

    users {
        int id PK "Auto Increment"
        varchar full_name "User's Full Name"
        varchar email UK "Unique Email Address"
        varchar password "Hashed Password (nullable for Google OAuth)"
        varchar gender "User Gender"
        varchar education "Education Level"
        varchar course "Course / Specialization"
        varchar semester "Semester / Year"
        varchar auth_provider "local | google | otp"
        varchar google_id UK "Google Account Identifier (nullable)"
        text resume_text "Parsed text from resume upload"
        varchar resume_filename "Path or filename of resume"
        datetime registered_at "Registration Timestamp"
    }

    interview_results {
        int id PK "Auto Increment"
        int user_id FK "Linked to users.id"
        decimal score "Interview score out of 10"
        varchar status "Selected | Rejected"
        text strengths "Bullet points of strengths"
        text improvements "Bullet points of improvements"
        text summary "Executive assessment summary"
        varchar domain "Target Job Role or Technical Domain"
        datetime interview_datetime "Completion timestamp"
    }

    interview_progress {
        int id PK "Auto Increment"
        int user_id FK "Linked to users.id (Unique)"
        text chat_history "Serialized JSON conversation stream"
        int q_count "Current question index"
        datetime updated_at "Last updated timestamp"
    }

    admin_settings {
        int id PK "Auto Increment"
        int min_questions "Minimum rounds required (default: 5)"
        int max_questions "Maximum rounds capped (default: 8)"
        int pass_score "Score cutoff for selection (default: 6)"
        varchar default_difficulty "Default difficulty level"
    }
```

### 1. `users` Table
Stores candidates' credentials, professional attributes, and resume metadata.
* `id` (*Integer, Primary Key*): Unique auto-incrementing identifier.
* `full_name` (*String*): Candidate's full name.
* `email` (*String, Unique*): Checked for duplicate registration records during signups.
* `password` (*String, Nullable*): Securely hashed passwords using PBKDF2/SHA256 via Werkzeug. Left empty when using third-party providers (Google OAuth).
* `gender` (*String*), `education` (*String*), `course` (*String*), `semester` (*String*): Education levels, course branches, and semesters (e.g. B.Tech, CSE, 7th Semester).
* `auth_provider` (*String*): Tells the authentication handler how the user logged in: `local`, `google`, or `otp`.
* `google_id` (*String, Unique, Nullable*): Stores the unique sub identifier from Google OpenID Connect profile payloads.
* `resume_text` (*Text, Nullable*): Extracted raw text content parsed from uploaded resume PDF files.
* `resume_filename` (*String, Nullable*): Local disk filename of the uploaded PDF file.
* `registered_at` (*DateTime*): Automatically logged during record creation.

### 2. `interview_results` Table
Persists evaluation sheets generated by Gemini AI after an assessment.
* `id` (*Integer, Primary Key*): Auto-incrementing identifier.
* `user_id` (*Integer, Foreign Key*): Points to `users.id` with cascade deletion support.
* `score` (*Decimal*): Numeric grade assigned by the AI evaluator (scaled 0-10).
* `status` (*String*): Either `Selected` or `Rejected` based on whether the score matches or exceeds the current admin pass cutoff.
* `strengths` (*Text*), `improvements` (*Text*): Structured feedback lists parsed into bullet items.
* `summary` (*Text*): Short paragraphs of executive summary detailing the candidate's communication skills and domain depth.
* `domain` (*String*): The job role domain (e.g., Data Science, Backend Developer).
* `interview_datetime` (*DateTime*): Completed timestamp.

### 3. `interview_progress` Table
Tracks active, in-progress interview sessions, enabling resumption on disconnect.
* `id` (*Integer, Primary Key*): Auto-incrementing identifier.
* `user_id` (*Integer, Foreign Key, Unique*): Link to the candidate (one-to-one relationship).
* `chat_history` (*Text*): JSON-serialized conversation log (all developer/user prompt iterations). Moving this to the database prevents browser cookie overflow crashes.
* `q_count` (*Integer*): Current question sequence count.
* `updated_at` (*DateTime*): Tracks the last activity timestamp.

### 4. `admin_settings` Table
Provides global runtime controls for the interview loop.
* `id` (*Integer, Primary Key*): Config record identifier.
* `min_questions` (*Integer*): Lower bound of questions asked before Gemini can choose to finish (default: 5).
* `max_questions` (*Integer*): Hard limit of questions allowed before forcing a conclusion (default: 8).
* `pass_score` (*Integer*): Grade cutoff used to output Selected or Rejected badges (default: 6).
* `default_difficulty` (*String*): Default target difficulty level if not set by user.

---

## 🧠 Gemini AI Prompt Mechanics & Flow

The AI pipeline divides operations into two distinct stages:

```
[Candidate starts practice]
       │
       ▼
1. Adaptive Question Loop (/interview/submit)
   ├── Input context: target domain + difficulty + parsed resume text + full chat history
   ├── Prompt constraint: Output strictly ONLY a single raw question (under 2 sentences). No fluff.
   └── Output: Next question served to candidate
       │
[Loop repeats 5 to 8 times until Gemini signals completion or max count is reached]
       │
       ▼
2. Full Transcript Evaluation (/finish-interview)
   ├── Input context: Full interview Q&A transcript
   ├── Prompt constraint: Output JSON with: {score: X, strengths: [...], improvements: [...], summary: "..."}
   └── Output: Record saved in DB, linked to user, evaluation screen displayed to user
```

### System Prompt Guidelines for Question Generation
The backend builds custom system prompts on each iteration to guide the model:
* **Strict Domain Limits**: The AI is instructed to stay 100% within the user's selected domain (e.g., React Frontend).
* **Resume Adaptation**: If a candidate uploads a resume, the AI reads the parsed text and shapes its initial questions around projects or technologies found in it.
* **No Preamble**: The AI is barred from prefixing questions with conversational fluff ("Sure, let me ask...", "Excellent answer, now..."), ensuring clean user interfaces.

---

## 🔐 Environment Variables Configuration

Deployments read credentials from environment variables. Create a local `.env` file in your root folder:

```ini
# Core Flask Settings
SECRET_KEY="your-cryptographic-flask-session-key"

# Database Connection (MySQL / PostgreSQL)
# If left empty, the application automatically boots on SQLite (ai_interview_platform.db)
DATABASE_URL="mysql+pymysql://db_user:password@localhost/ai_interview_platform"

# Google Gemini API Key
GEMINI_API_KEY="AIzaSy..."

# Google OAuth Credentials (Optional)
GOOGLE_CLIENT_ID="123456-googleusercontent.com"
GOOGLE_CLIENT_SECRET="GOCSPX-secretkey..."

# Email API Providers (Optional - falls back to Gmail SMTP or console print in Dev mode)
RESEND_API_KEY="re_..."
SENDGRID_API_KEY="SG.xxx..."

# Gmail SMTP Fallback Credentials (Optional)
MAIL_USERNAME="noreply@gmail.com"
MAIL_PASSWORD="gmailapppassword"

# Optional Admin Credentials (auto-generates a secure random fallback on boot if missing)
ADMIN_EMAIL="admin@platform.com"
ADMIN_PASSWORD="secureadminpassword"
```

---

## 🚀 Local Installation & Run Guide

Follow these steps to deploy the application on your local workstation:

1. **Clone the Repository**
   ```bash
   git clone https://github.com/MR360-TECH/AI_INTERVIEW_PLATFORM.git
   cd AI_INTERVIEW_PLATFORM
   ```

2. **Establish Python Virtual Environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On MacOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify / Run the Application**
   ```bash
   python app.py
   ```
   *Note: On startup, the SQLAlchemy ORM automatically verifies schema tables, creates the SQLite file if no external Database URL is set, and runs migrations for resume support columns.*

---

## 👨‍💻 Developed By

**Gowtham V**
