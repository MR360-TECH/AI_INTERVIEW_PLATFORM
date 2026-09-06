# 🤖 AI Interview Studio & Assessment Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash%20Lite%20AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20PostgreSQL%20%7C%20SQLite-00758F?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Deployment](https://img.shields.io/badge/Deployment-Render%20Cloud-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/)

An enterprise-grade, full-stack AI-powered technical and situational mock interview platform designed to simulate realistic, unscripted hiring evaluations. Powered by state-of-the-art **Google Gemini AI** and built on a resilient **Flask & SQLAlchemy** foundation, the platform delivers adaptive assessments, real-time voice dictation, integrated code execution sandboxes, automated anti-cheat proctoring, multi-provider OTP authentication, and comprehensive competency scorecards with printable PDF reports.

> **Designed for:** University students, aspiring engineers, and job seekers aiming to master technical, behavioral, and domain-specific interviews through intelligent, real-time AI simulations.

---

## 🎯 Key Capabilities & Highlights

* 🧠 **Adaptive AI Examiner**: Evaluates technical depth, analytical reasoning, and communication clarity in real-time, dynamically adjusting questions based on candidate performance.
* 🛡️ **Automated Security Proctoring**: Real-time window focus tracking, tab-switch breach detection, two-strike disciplinary warning modals, and automatic session disqualification for code of conduct breaches.
* 🎓 **Multi-Track Practice Hub**:
  * **Academic Viva Voce**: Oral university exam simulations testing definitions, theoretical rigor, and algorithms.
  * **FluentFlow Language Practice**: Conversational multilingual practice with instant grammatical corrections and translations.
  * **Concept Drills**: Rapid-fire architectural and scenario reasoning challenges.
* 🎙️ **Hands-Free Voice Dictation**: Integrated client-side Web Speech API (`webkitSpeechRecognition`) with animated neural waveform visualizers.
* 💻 **Monaco Code Editor**: Built-in VS Code-style Python 3 programming sandbox for coding challenges.
* 📄 **Resume-Driven Questioning**: Automatic PDF/DOCX resume text extraction and embedding into the candidate's interview context.
* 📊 **Instant Competency Scorecards**: High-contrast score gauge rings, competency matrix breakdowns, qualitative executive summaries, and single-click printable PDF report generation.
* 🔐 **Triple-Redundant OTP Delivery**: Resend HTTP API, SendGrid HTTP API, and SMTP failover routing for ultra-reliable email authentication.
* ⚙️ **Executive Operations Dashboard**: Administrative candidate management, live assessment monitoring, candidate resume viewers, and real-time pass-score threshold configuration.

---

## 🔄 End-to-End Platform Architecture

```mermaid
flowchart TD
    User([Candidate / Job Seeker]) --> AuthLayer{Authentication Gateway}
    
    AuthLayer -->|Local Account| LocalLogin[PBKDF2 Password Auth]
    AuthLayer -->|Social Login| GoogleOAuth[Google OAuth 2.0]
    AuthLayer -->|Passwordless| OTPAuth[Multi-Provider OTP Dispatcher]
    
    LocalLogin --> Dashboard[Candidate Workspace Dashboard]
    GoogleOAuth --> Dashboard
    OTPAuth --> Dashboard
    
    Dashboard --> ResumeUpload[Resume Indexing & Text Extraction]
    Dashboard --> TrackSelection[Mode Selection: Assessment vs Practice]
    
    TrackSelection --> InterviewEngine[Live Assessment Studio Engine]
    ResumeUpload -.->|Embedded Context| InterviewEngine
    
    InterviewEngine --> Proctor[Active Anti-Cheat Proctoring Monitor]
    InterviewEngine --> VoiceInput[Web Speech Voice Transcription]
    InterviewEngine --> Monaco[Monaco Code Editor Sandbox]
    InterviewEngine --> GeminiEngine[Google Gemini Flash AI Engine]
    
    GeminiEngine -->|Streaming Q&A| InterviewEngine
    Proctor -->|2nd Strike Breach| Terminate[Disqualification & Termination]
    
    InterviewEngine -->|Completion| ResultGen[Rapid AI Evaluation Pipeline]
    ResultGen --> Scorecard[Performance Evaluation Report & PDF]
    Scorecard --> History[Candidate Attempt Progression & History]
    
    Scorecard -.-> DB[(Relational Database: MySQL / PostgreSQL)]
    History -.-> DB
    
    AdminUser([Recruiter / Administrator]) --> AdminPanel[Admin Operations Control Center]
    AdminPanel --> DB
    AdminPanel --> ConfigMgmt[Global Settings & Cutoff Configuration]
```

---

## 🛠️ Technical Stack

| Component | Technology | Description |
|---|---|---|
| **Backend Framework** | Python 3.11+ / Flask 3.0+ | Core application server, routing, and session management |
| **Database ORM** | Flask-SQLAlchemy 3.1+ | Unified relational ORM supporting MySQL, PostgreSQL, and SQLite |
| **AI Assessment Engine** | Google Gemini (`gemini-flash-lite-latest`) | High-speed, context-aware conversational questioning & grading |
| **Authentication & Security** | Werkzeug / Authlib / PyCryptodome | PBKDF2-SHA256 password hashing, Google OAuth 2.0 OpenID Connect |
| **Email Delivery Engine** | Resend API / SendGrid API / SMTP | Multi-provider fallback delivery system for verification codes |
| **Speech Processing** | Web Speech API | Client-side browser-native speech-to-text recognition |
| **Code Editor** | Monaco Editor CDN | Embedded VS Code syntax highlighter and code input |
| **Data Visualization** | Chart.js 4.4+ | Interactive score progression and trend lines |
| **Styling & Theme** | Bootstrap 5.3 + Custom CSS3 | Elite Cyber-Blue high-contrast dark theme with neural aurora backdrop |
| **Production WSGI** | Gunicorn | High-concurrency production HTTP application server |

---

## 🔐 Security & Anti-Cheat System

```
                      PROCTORING LIFECYCLE
                     
  [Active Interview] ────── Tab Switch / Focus Lost ──────► [Strike 1 Recorded]
          ▲                                                         │
          │                        Dismiss Modal                    ▼
          └──────────────────────── (Warning Only) ◄───── [Proctor Warning Modal]
                                                                    │
                                   Second Tab Switch                ▼
                             ─────────────────────────────► [Strike 2 Triggered]
                                                                    │
                                                                    ▼
                                                         [Immediate Disqualification]
                                                                    │
                                                                    ▼
                                                         [Record Flagged in DB]
```

* **Window Focus Detection**: Uses the browser Page Visibility API and `window.onblur` event listeners to monitor candidate window focus.
* **Two-Strike Escalation**: First focus violation triggers a full-screen red warning modal; second violation immediately disqualifies the session.
* **Encrypted Sessions**: Server-signed cryptographic session cookies (`HttpOnly`, `SameSite=Lax`, `Secure` in production).
* **Role-Based Access Control**: Strict multi-tier authentication barriers isolating administrative dashboards, user modification tools, and scoring metrics from standard users.

---

## 📊 Database Entity Model

```mermaid
erDiagram
    users ||--o{ interview_results : "completes"
    users ||--o| interview_progress : "tracks active session"

    users {
        int id PK
        varchar full_name
        varchar email UK
        varchar password "Hashed PBKDF2"
        varchar auth_provider "local | google | otp"
        varchar google_id UK
        varchar education
        varchar course
        varchar semester
        text resume_text
        varchar resume_filename
        datetime registered_at
    }

    interview_results {
        int id PK
        int user_id FK
        decimal score "Score out of 10"
        varchar status "PASS | FAIL | Terminated | Selected"
        text summary "AI Assessment Summary"
        varchar domain "Interview Domain"
        boolean is_terminated "Anti-cheat flag"
        text termination_reason
        datetime interview_datetime
    }

    interview_progress {
        int id PK
        int user_id FK
        text chat_history "Serialized conversation transcript"
        int q_count "Question progress index"
        datetime updated_at
    }

    admin_settings {
        int id PK
        int min_questions "Default: 5"
        int max_questions "Default: 5"
        int pass_score "Cutoff: 6"
        varchar default_difficulty
    }
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the root directory and configure the required environment variables:

```bash
# -------------------------------------------------------------
# CORE APPLICATION SETTINGS
# -------------------------------------------------------------
SECRET_KEY=your_secure_random_flask_secret_key_here
FLASK_ENV=production

# -------------------------------------------------------------
# DATABASE CONFIGURATION
# (Leave empty or unset to automatically fallback to local SQLite)
# -------------------------------------------------------------
DATABASE_URL=mysql+pymysql://username:password@hostname:3306/database_name

# -------------------------------------------------------------
# GOOGLE GEMINI AI ENGINE
# -------------------------------------------------------------
GEMINI_API_KEY=your_gemini_api_key_here

# -------------------------------------------------------------
# GOOGLE OAUTH 2.0 (Optional - for Google Single Sign-On)
# -------------------------------------------------------------
GOOGLE_CLIENT_ID=your_google_oauth_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret

# -------------------------------------------------------------
# EMAIL DELIVERY & OTP SERVICES (Optional - with SMTP fallback)
# -------------------------------------------------------------
RESEND_API_KEY=your_resend_api_key_here
SENDGRID_API_KEY=your_sendgrid_api_key_here
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_sender_email@gmail.com
MAIL_PASSWORD=your_email_app_password
MAIL_DEFAULT_SENDER=your_sender_email@gmail.com

# -------------------------------------------------------------
# ADMINISTRATOR CREDENTIALS (Auto-initialized on first launch)
# -------------------------------------------------------------
ADMIN_EMAIL=admin@platform.local
ADMIN_PASSWORD=your_custom_admin_password
```

---

## 🚀 Installation & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/MR360-TECH/AI_INTERVIEW_PLATFORM.git
cd AI_INTERVIEW_PLATFORM
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 🌐 Production Cloud Deployment (Render)

This repository includes native deployment support for **Render**:

1. Fork or push this repository to your GitHub account.
2. Log in to [Render Dashboard](https://dashboard.render.com/) and click **New + Web Service**.
3. Connect your repository and configure:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Under **Environment Variables**, add `SECRET_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`, and other optional credentials.
5. Deploy the service. The SQL engine will auto-verify database schemas and apply migrations automatically on startup.

---

## 📄 License & Attribution

Distributed under the MIT License. Developed and maintained by **MR360-TECH**.

---

**Developed with ❤️ by [Gowtham V](https://github.com/MR360-TECH)**
