# 🤖 AI Interview Studio & Assessment Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash%20Lite%20AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Database](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00E599?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Deployment](https://img.shields.io/badge/Deployment-Render%20Cloud-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/)

> **An enterprise-grade, full-stack AI-powered mock interview platform** that simulates realistic, unscripted hiring evaluations — powered by **Google Gemini AI**, built on **Flask & SQLAlchemy**, with a clean 4-layer modular architecture, adaptive assessments, voice dictation, Monaco code sandbox, automated anti-cheat proctoring, and printable PDF scorecards.

> **Designed for:** University students, aspiring engineers, and job seekers who want to master technical, behavioral, and domain-specific interviews through intelligent, real-time AI simulations — completely free.

---

## 💡 Why This Platform Was Built

The technical interview process is one of the most anxiety-inducing and poorly-prepared-for stages in a student's academic and professional journey. Most students realize too late that:

- **Mock interviews are expensive** — professional platforms charge monthly subscriptions, and human mentors are hard to access.
- **Generic question banks go stale** — static PDFs and YouTube videos don't simulate the real pressure of live questioning.
- **There is no personalization** — every student gets the same questions regardless of their resume, domain, or semester level.
- **Language barriers exist** — many students struggle to articulate technically correct ideas in English under time pressure.
- **Practice environments are disconnected** — code editors, voice practice, and company-specific prep live in different tools.

**This platform was built to solve all of that in one place** — a single, free, open-source solution where a student can upload their resume, select a domain, and get interrogated by an AI examiner that adapts dynamically to their answers, flags behavioral violations, and delivers an honest, structured performance report — just like a real recruiter would.

The platform was designed with the needs of **tier-2 and tier-3 engineering college students in India** specifically in mind, where access to quality placement training infrastructure is limited but the aspirations are not.

---

## 🎯 Key Capabilities & Highlights

* 🧠 **Adaptive AI Examiner**: Evaluates technical depth, analytical reasoning, and communication clarity in real-time, dynamically adjusting questions based on candidate performance.
* 🛡️ **Interview Integrity & Strikes**: Server-side strikes for every violation (tab switch, paste/copy, second session, late answer, optional fullscreen), a clear violation box showing the exact mistake, an admin-set strike limit, an admin-only integrity log, and an individual on/off switch for every rule plus a master switch.
* 🎓 **Multi-Track Practice Hub**:
  * **Academic Viva Voce**: Oral university exam simulations testing definitions, theoretical rigor, and algorithms.
  * **FluentFlow Language Practice**: Conversational multilingual practice with instant grammatical corrections and translations.
  * **Concept Drills**: Rapid-fire architectural and scenario reasoning challenges.
* 🏢 **Company-Specific Prep Hub**: Curated, categorized resource links for 11 top companies — Google, Microsoft, Amazon, Meta, Netflix, TCS, Infosys, Wipro, Accenture, Cognizant, and Capgemini — covering LeetCode, GeeksForGeeks, PrepInsta, and InterviewBit.
* 🎙️ **Hands-Free Voice Dictation**: Integrated client-side Web Speech API (`webkitSpeechRecognition`) with animated neural waveform visualizers.
* 💻 **Monaco Code Editor**: Built-in VS Code-style Python 3 programming sandbox for coding challenges.
* 📄 **Resume-Driven Questioning**: Automatic PDF/DOCX resume text extraction embedded into the candidate's interview context for hyper-personalized questioning.
* 📊 **Instant Competency Scorecards**: High-contrast score gauge rings, competency matrix breakdowns, qualitative executive summaries, and single-click printable PDF report generation.
* 🔐 **Triple-Redundant OTP Delivery**: Resend HTTP API, SendGrid HTTP API, and SMTP failover routing for ultra-reliable email authentication.
* ⚙️ **Executive Operations Dashboard**: Administrative candidate management, live assessment monitoring, candidate resume viewers, per-user attempt unlock, and real-time pass-score threshold configuration.
* 🔑 **Three Authentication Pathways**: Classic password login, Google OAuth 2.0 Single Sign-On, and passwordless OTP login — all under one unified session layer.
* 📚 **Preparation Library**: 92 curated links in one searchable page with track and format filters, bookmarks and three 7-day study plans. An admin-only Link Health checker finds broken links and can hide them.
* 🧭 **Interactive Admin Guide**: A 38-step guided tour with spotlight and pointer over illustrated admin screens, plus an 11-module manual.
* 🔁 **Error Recovery**: A server error never uses an attempt; the interview is saved on the server, and a professional error page with one Back button resumes it at the next question.
* 🏗️ **Clean 4-Layer Modular Architecture**: Codebase fully refactored into `MODULES/` with clear separation of Config, Models, Services, and Controllers for maintainability at scale.

---

## 🗺️ App Flow — Step-by-Step User Journey

This section walks through the **complete experience** of a candidate from first visit to final scorecard.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE CANDIDATE JOURNEY                           │
└─────────────────────────────────────────────────────────────────────────────┘

STEP 1 ─ LANDING & DISCOVERY
  └─► Candidate visits the platform landing page (/)
      ├── Reviews platform capabilities, features, and testimonials
      └── Clicks "Get Started" → routed to registration / login

STEP 2 ─ ACCOUNT CREATION & IDENTITY VERIFICATION
  └─► Three pathways available:
      ├── [A] Classic Registration (/register)
      │     ├── Fills in full name, email, password, education, course, semester
      │     └── PBKDF2-SHA256 hashed password stored securely
      ├── [B] Google OAuth (/auth/google)
      │     └── One-click sign-in via Google OpenID Connect, auto-profile sync
      └── [C] OTP Passwordless (/auth/otp/send → /auth/otp/verify)
            ├── Email entered → OTP dispatched via Resend → SendGrid → SMTP
            └── 6-digit code verified, session initialized

STEP 3 ─ CANDIDATE WORKSPACE DASHBOARD (/dashboard)
  └─► Personalized workspace loads:
      ├── Profile card: name, education, course, semester
      ├── Resume upload zone (PDF/DOCX, max 10 MB) → auto text extraction
      ├── Latest interview result summary with score gauge ring
      ├── Interview history progress chart (Chart.js trend line)
      ├── Quick-launch cards: Assessment, Practice, Tech Prep, History
      └── Edit profile (/edit-profile): update name, education, course, semester

STEP 4A ─ LIVE ASSESSMENT INTERVIEW (/interview)
  └─► Domain selection screen → Pick from:
      │   Web Dev, Python, Java, DSA, DBMS, OS, CN, AI/ML,
      │   System Design, Cybersecurity, Cloud, DevOps, and more
      ├── Resume context auto-injected into Gemini's system prompt
      ├── Anti-cheat proctoring activates immediately on page load
      │
      ├── QUESTION LOOP:
      │     ├── Gemini streams the first question (domain + resume aware)
      │     ├── Candidate types OR uses voice dictation (waveform animates)
      │     ├── Code questions → Monaco Editor sandbox appears
      │     ├── File questions → image/diagram upload enabled
      │     ├── Answer submitted → Gemini evaluates and generates next question
      │     └── Adaptive depth: deeper follow-ups if answers are strong
      │
      ├── PROCTORING LAYER (parallel):
      │     ├── Page visibility & window focus monitored via JS events
      │     ├── Strike 1: Tab switched → Full-screen red warning modal fires
      │     └── Strike 2: Another violation → Session auto-terminated & flagged
      │
      └── COMPLETION (after min. questions reached):
            └── Candidate clicks "Finish" → /finish-interview

STEP 4B ─ PRACTICE HUB (/practice-setup)
  └─► Select one of three modes:
      ├── 🎓 Viva Voce: Enter any academic subject → AI conducts oral Q&A
      ├── 💬 FluentFlow Language Practice:
      │     ├── Choose target language (English, Hindi, French, etc.)
      │     ├── Set focus: conversation / grammar / vocabulary / pronunciation
      │     └── Set level: beginner / intermediate / advanced
      └── ⚡ Concept Drills: Enter a topic → rapid-fire scenario challenges
      (Practice sessions are NOT scored or saved to history)

STEP 4C ─ COMPANY PREP HUB (/tech-questions)
  └─► Browse 11 companies (Google, Microsoft, Amazon, Meta, Netflix,
      TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini)
      └── Each company card → curated resource links:
            LeetCode tagged problems, GeeksForGeeks guides,
            PrepInsta placement papers, InterviewBit mock Q&A

STEP 5 ─ AI EVALUATION PIPELINE (/finish-interview)
  └─► Full chat transcript submitted to Gemini evaluation prompt
      ├── Scores 10-point scale: overall 1.0–10.0 competency rating
      ├── Generates qualitative executive summary (3 professional paragraphs)
      ├── Determines PASS / FAIL against admin-configured cutoff
      └── Result stored in DB → redirects to scorecard

STEP 6 ─ SCORECARD & REPORT (/interview-result)
  └─► High-contrast result card renders:
      ├── Score gauge ring with PASS / FAIL / TERMINATED badge
      ├── Unique Assessment Session Code (e.g. AIS-000042)
      ├── AI-written qualitative executive summary
      ├── "Print / Save PDF" button → browser print-to-PDF
      └── Navigation back to Dashboard or History

STEP 7 ─ HISTORY & PROGRESSION (/my-history)
  └─► Full attempt log table: date, domain, score, status
      ├── Click any row → detailed scorecard for that attempt
      └── Trend analysis via Chart.js score progression graph
```

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
    Dashboard --> TrackSelection[Mode Selection: Assessment vs Practice vs Prep Hub]
    
    TrackSelection --> InterviewEngine[Live Assessment Studio Engine]
    TrackSelection --> PracticeHub[Practice Hub: Viva / Language / Drills]
    TrackSelection --> CompanyPrep[Company Prep Hub: 11 Companies]
    ResumeUpload -.->|Embedded Context| InterviewEngine
    
    InterviewEngine --> Proctor[Active Anti-Cheat Proctoring Monitor]
    InterviewEngine --> VoiceInput[Web Speech Voice Transcription]
    InterviewEngine --> Monaco[Monaco Code Editor Sandbox]
    InterviewEngine --> GeminiEngine[Google Gemini Flash Lite AI Engine]
    
    GeminiEngine -->|Streaming Q&A| InterviewEngine
    Proctor -->|2nd Strike Breach| Terminate[Disqualification & Termination]
    
    InterviewEngine -->|Completion| ResultGen[Rapid AI Evaluation Pipeline]
    ResultGen --> Scorecard[Performance Evaluation Report & PDF]
    Scorecard --> History[Candidate Attempt Progression & History]
    
    Scorecard -.-> DB[(Neon PostgreSQL)]
    History -.-> DB
    
    AdminUser([Recruiter / Administrator]) --> AdminPanel[Admin Operations Control Center]
    AdminPanel --> DB
    AdminPanel --> ConfigMgmt[Global Settings & Cutoff Configuration]
    AdminPanel --> UserMgmt[User Management & Attempt Unlock]
```

---

## 🏗️ Modular 4-Layer Architecture

The codebase is fully organized under a `MODULES/` package with clean separation of concerns across four well-defined layers:

```mermaid
flowchart TD
    subgraph L1["LAYER 1 — Core Infrastructure"]
        Config["config.py\n─────────────────\n• Flask app factory settings\n• SQLAlchemy & OAuth init\n• DB URL resolution (MySQL→SQLite fallback)\n• Gemini model name & API key\n• Upload folder & file limits\n• Admin credential bootstrap"]
    end

    subgraph L2["LAYER 2 — Data Persistence"]
        Models["models.py\n─────────────────\n• User ORM model\n• InterviewResult ORM model\n• InterviewProgress ORM model\n• AdminSettings ORM model\n• SettingsSnapshot (cache DTO)\n• get_settings() with 5s TTL cache\n• save_progress() / clear_progress()\n• profile_is_complete() validator\n• allowed_file() / allowed_resume_file()"]
    end

    subgraph L3["LAYER 3 — Business Services"]
        AI["ai_client.py\n─────────────────\n• get_ai_client() (singleton)\n• analyze_attachment()\n• build_initial_question_prompt()\n• build_subsequent_question_prompt()\n• build_ajax_system_prompt()\n• build_evaluation_prompt()"]
        Mailer["mailer.py\n─────────────────\n• send_otp_email()\n• send_slot_unlocked_email()\n• Resend API → SendGrid → SMTP\n• Async threaded dispatch\n• HTML OTP email templates"]
    end

    subgraph L4["LAYER 4 — Route Controllers"]
        Login["login_env.py\n(login_bp)\n• / home\n• /login  /logout\n• /register  /signup\n• /auth/google  /auth/google/callback\n• /auth/otp/send  /auth/otp/verify\n• /forgot-password  /reset-password"]
        Dashboard["dashboard.py\n(dashboard_bp)\n• /dashboard\n• /upload-resume\n• /edit-profile\n• /my-history\n• /interview-result/<id>\n• /uploads/<filename>"]
        Interview["interview_engine.py\n(interview_bp)\n• /interview  GET/POST\n• /interview/submit  POST (AJAX)\n• /finish-interview  POST\n• /practice  GET/POST\n• /practice/submit  POST (AJAX)"]
        Admin["admin_env.py\n(admin_bp)\n• /admin\n• /admin/users\n• /admin/users/<id>\n• /admin/interview/<id>\n• /admin/unlock/<user_id>\n• /admin/settings\n• /admin/db-check"]
        Practice["practicemode.py\n(practice_bp)\n• /practice-setup\n• /practice\n• /practice/submit"]
        Resources["resources.py\n(resources_bp)\n• /tech-questions\n• /tech-questions/<company>"]
    end

    AppFactory["MODULES/__init__.py\ncreate_app() Factory\n─────────────────────\n• Instantiate Flask app\n• Security & performance headers\n• Error handlers (413, 500)\n• register_blueprints()"]

    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> AppFactory
    L1 --> AppFactory
```

---

## 🏢 Company Prep Hub — Supported Companies

The platform includes a curated preparation hub for **11 major tech companies**, each with 4 structured resource links:

| # | Company | Focus Areas |
|---|---|---|
| 1 | **Google** | DSA, Algorithms, System Design, Behavioral |
| 2 | **Microsoft** | OOP, OS, Networking, SDE/SDET roles |
| 3 | **Amazon** | Leadership Principles, System Design, SDE |
| 4 | **Meta (Facebook)** | Graphs, DP, System Design at Scale |
| 5 | **Netflix** | Distributed Systems, Microservices, Culture Fit |
| 6 | **TCS** | NQT Aptitude, Verbal, Logical, Coding |
| 7 | **Infosys** | InfyTQ, Aptitude, Verbal, Technical Rounds |
| 8 | **Wipro** | NLTH Aptitude, Written Communication, Coding |
| 9 | **Accenture** | Cognitive Ability, Verbal, Communication |
| 10 | **Cognizant** | GenC/GenC Next, Aptitude, Coding |
| 11 | **Capgemini** | Pseudocode, Essay Writing, Behavioral |

Each company page aggregates resources from **LeetCode**, **GeeksForGeeks**, **PrepInsta**, and **InterviewBit**.

---

## 📐 Class Diagram

```mermaid
classDiagram
    class User {
        +int id PK
        +String full_name
        +String email UK
        +String password
        +String gender
        +String education
        +String course
        +String semester
        +String auth_provider
        +Boolean email_verified
        +String google_id UK
        +DateTime registered_at
        +String user_type
        +String github_url
        +String linkedin_url
        +Text skills
        +String years_of_experience
        +String current_designation
        +Text resume_text
        +String resume_filename
        +int extra_allowed_interviews
        +int attempts_count
        +get_attempts_used() int
    }

    class InterviewResult {
        +int id PK
        +int user_id FK
        +Decimal score
        +String status
        +Text strengths
        +Text improvements
        +Text summary
        +String domain
        +Boolean is_terminated
        +Text termination_reason
        +DateTime interview_datetime
        +session_code() String
        +real_attempt_filter()$ BooleanClause
    }

    class InterviewProgress {
        +int id PK
        +int user_id FK UK
        +Text chat_history
        +int q_count
        +DateTime updated_at
    }

    class AdminSettings {
        +int id PK
        +int min_questions
        +int max_questions
        +int pass_score
        +String default_difficulty
        +int question_timer_seconds
        +Boolean enable_attempt_limits
        +int default_allowed_interviews
        +Boolean enable_warning_strikes
    }

    class SettingsSnapshot {
        +int min_questions
        +int max_questions
        +int pass_score
        +String default_difficulty
        +int question_timer_seconds
        +Boolean enable_attempt_limits
        +int default_allowed_interviews
        +Boolean enable_warning_strikes
        +__init__(s)
    }

    class AIClient {
        <<service>>
        +get_ai_client() Client
        +analyze_attachment(bytes, mime, hint) String
        +build_initial_question_prompt(mode, topic, lang, focus, level) String
        +build_subsequent_question_prompt(mode, topic, lang, focus, level, difficulty, q_count, min_q, convo) String
        +build_ajax_system_prompt(domain, difficulty, resume, is_practice, q_count, min_q, max_q) String
        +build_evaluation_prompt(mode, topic, lang, difficulty, domain, convo) String
    }

    class Mailer {
        <<service>>
        +send_otp_email(to_email, otp) void
        +send_slot_unlocked_email(to_email, name) void
        -_send_via_resend(to, subject, html) bool
        -_send_via_sendgrid(to, subject, html) bool
        -_send_via_smtp(to, subject, text, html, user, pass) bool
        -_otp_html_body(otp) String
    }

    class FlaskApp {
        <<factory>>
        +create_app() Flask
        +add_performance_headers(response)
        +apply_security_headers(response)
        +register_blueprints(app)
    }

    User "1" --> "0..*" InterviewResult : completes
    User "1" --> "0..1" InterviewProgress : tracks
    AdminSettings --> SettingsSnapshot : snapshot of
    FlaskApp ..> AIClient : uses
    FlaskApp ..> Mailer : uses
    FlaskApp ..> User : manages
    FlaskApp ..> InterviewResult : persists
    FlaskApp ..> AdminSettings : configures
```

---

## 📊 Database Entity-Relationship Diagram

```mermaid
erDiagram
    users ||--o{ interview_results : "completes"
    users ||--o| interview_progress : "tracks active session"

    users {
        int id PK
        varchar full_name
        varchar email UK
        varchar password "Hashed PBKDF2"
        varchar gender
        varchar auth_provider "local | google | otp"
        boolean email_verified
        varchar google_id UK
        datetime registered_at
        varchar user_type "student | professional"
        varchar github_url
        varchar linkedin_url
        text skills
        varchar years_of_experience
        varchar current_designation
        text resume_text
        varchar resume_filename
        int extra_allowed_interviews "Admin-granted extra attempts"
        int attempts_count "Cached attempt counter"
    }

    interview_results {
        int id PK
        int user_id FK
        decimal score "Score 1.0–10.0"
        varchar status "PASS | FAIL | Terminated | Selected"
        text strengths "AI-identified strengths"
        text improvements "AI-suggested improvements"
        text summary "3-paragraph AI Assessment Summary"
        varchar domain "Interview Domain"
        boolean is_terminated "Anti-cheat flag"
        text termination_reason
        datetime interview_datetime
    }

    interview_progress {
        int id PK
        int user_id FK UK
        text chat_history "JSON serialized conversation"
        int q_count "Question progress index"
        datetime updated_at
    }

    admin_settings {
        int id PK
        int min_questions "Default: 3"
        int max_questions "Default: 8"
        int pass_score "Cutoff score threshold"
        varchar default_difficulty "student | mid | senior"
        int question_timer_seconds "Default: 90"
        boolean enable_attempt_limits
        int default_allowed_interviews "Default: 2"
        boolean enable_warning_strikes
    }
```

---

## 🔄 Request-Response Sequence Diagram

```mermaid
sequenceDiagram
    participant C as Candidate Browser
    participant F as Flask App
    participant DB as Database
    participant G as Gemini AI

    C->>F: GET /interview (domain selected)
    F->>DB: Query InterviewProgress, User resume_text
    F->>G: build_initial_question_prompt()
    G-->>F: First question text + [TYPE: TEXT/CODE]
    F-->>C: Render interview.html + first question

    loop Question-Answer Loop
        C->>F: POST /interview/submit (answer + q_count)
        F->>DB: save_progress(chat_history, q_count)
        F->>G: build_ajax_system_prompt() + chat history
        G-->>F: Next question OR [END_INTERVIEW]
        F-->>C: JSON { question, q_num, done }
    end

    C->>F: POST /finish-interview
    F->>DB: clear_progress(user_id)
    F->>G: build_evaluation_prompt(transcript)
    G-->>F: SCORE + SUMMARY paragraphs
    F->>DB: INSERT InterviewResult (score, status, summary)
    F-->>C: Redirect → /interview-result/<id>
```

---

## 🗂️ Project Structure

```
ai_interview_platform/
│
├── app.py                              # Entry point: calls create_app() from MODULES
├── requirements.txt                    # Python package dependencies
├── Procfile                            # Gunicorn start command for Render/Heroku
├── render.yaml                         # Render cloud service configuration
├── runtime.txt                         # Python runtime version pin
├── .env                                # Local environment variables (never commit this)
├── .gitignore                          # Git ignore rules
│
├── MODULES/                            # 🏗️ Core application package (4-layer architecture)
│   ├── __init__.py                     # create_app() Flask factory function
│   │
│   ├── LAYER_1_CORE_INFRASTRUCTURE/
│   │   └── config.py                   # App config, DB URL resolution, OAuth, Gemini, uploads
│   │
│   ├── LAYER_2_DATA_PERSISTENCE/
│   │   └── models.py                   # SQLAlchemy ORM models, validators, settings cache
│   │
│   ├── LAYER_3_BUSINESS_SERVICES/
│   │   ├── ai_client.py                # Gemini AI prompt builders & client singleton
│   │   └── mailer.py                   # Multi-provider OTP email dispatcher
│   │
│   └── LAYER_4_ROUTE_CONTROLLERS/
│       ├── __init__.py                 # register_blueprints() aggregator
│       ├── login_env.py                # Auth routes: login, register, Google OAuth, OTP
│       ├── dashboard.py                # Dashboard, resume upload, history, results
│       ├── interview_engine.py         # Live interview, AJAX submit, evaluation pipeline
│       ├── admin_env.py                # Admin panel, user management, settings
│       ├── practicemode.py             # Viva, FluentFlow, Concept Drills practice routes
│       └── resources.py                # Company prep hub resource pages
│
├── templates/                          # Jinja2 HTML templates
│   ├── index.html                      # Landing page
│   ├── login.html                      # Login page (password + Google + OTP)
│   ├── signup.html                     # OTP-based signup entry
│   ├── register.html                   # Full registration form
│   ├── dashboard.html                  # Candidate workspace dashboard
│   ├── interview.html                  # Live interview studio
│   ├── interview_result.html           # Score report & competency card
│   ├── practice_setup.html             # Practice mode selector
│   ├── my_history.html                 # Attempt history log
│   ├── tech_questions.html             # Company prep hub index
│   ├── company_questions.html          # Per-company resource page
│   ├── admin.html                      # Admin operations dashboard
│   ├── admin_users.html                # User management table
│   ├── admin_user_detail.html          # Individual user profile view
│   ├── admin_interview_detail.html     # Individual result deep-dive
│   ├── admin_settings.html             # Platform settings configuration
│   ├── edit_profile.html               # Profile editor
│   ├── forgot_password.html            # Password reset request
│   ├── send_otp.html                   # OTP login entry
│   ├── verify_otp.html                 # OTP verification
│   └── privacy.html                    # Privacy policy
│
├── static/                             # CSS, JS, images, fonts
└── uploads/                            # Candidate resume file storage
```

---

## 🛠️ Technical Stack

| Component | Technology | Description |
|---|---|---|
| **Backend Framework** | Python 3.11+ / Flask 3.0+ | Core application server, routing, and session management |
| **Application Architecture** | 4-Layer MODULES package | Config → Models → Services → Controllers with Blueprint registration |
| **Database ORM** | Flask-SQLAlchemy 3.1+ | Relational ORM on Neon PostgreSQL (SQLite only as a local fallback) |
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

Scored assessments are protected by integrity rules that are **counted and stored on the server**, so clearing browser data or editing the page cannot reset them. Practice labs are never proctored. Every rule has its own switch under **Admin → Settings → Interview Settings → Integrity & proctoring**, with a master "All integrity features" switch and a strike limit (1 to 5, default 2).

```
   Violation (browser or server)  ──►  Strike counted on the server  ──►  Box shown to the candidate
                                                │                         (exact mistake, Strike x of y, warning)
                                                ▼
                                   Limit reached?  ── yes ──►  Session ended (Terminated), counts as an attempt,
                                                │                events attached to the stored result
                                                no
                                                ▼
                                   Interview continues  ·  every event is listed in the admin-only integrity log
```

| Rule (admin switch) | What it does | Strike |
|---|---|---|
| Proctoring & warning strikes (main switch) | Turns all integrity rules on or off | - |
| Server-side strikes | Counts every violation on the server | Yes |
| Leaving the exam window | Tab, window or app switch (with time away) | Yes |
| One active session | Another browser or device is refused and counted | Yes |
| Server-side timer | The clock lives on the server; a reload cannot reset it; late answers counted | Late answers |
| Block copy and paste | Paste into the answer box and copying the question are blocked | Yes |
| Require fullscreen (off by default) | Leaving fullscreen is a violation | Yes |
| Typing-pattern flags | Instant or inserted long answers are flagged for the admin | Review only |
| Integrity log on the report | Admin sees every event with time, question and details | Display |

* **Web protection**: CSRF token on every form and request, session idle timeout (admin 30 min, candidate 2 h, 12 h maximum), Content-Security-Policy, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` and HSTS in production, `HttpOnly` / `SameSite=Lax` / `Secure` cookies, no signed-in page caching.
* **Sign-in protection**: one-time codes stored only as keyed hashes with expiry and attempt limits, brute-force lockouts, password strength rules, one generic login error (no account enumeration), POST-only destructive actions, no hard-coded secret key (the server refuses to start on Render without `SECRET_KEY`), optional admin two-step sign-in with `ADMIN_2FA=true`.
* **Admin Credential Hardening**: If `ADMIN_PASSWORD` is not set, a random token is generated and printed once to the startup log; no predictable default is ever used.
* **Role-Based Access Control**: administrative pages and tools are separated from candidate pages by session checks.

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
# DATABASE CONFIGURATION - Neon PostgreSQL (use the SAME value locally and on Render)
# Copy the *pooled* connection string from the Neon dashboard.
# On Render the app refuses to start without it; locally, a missing value falls back
# to a throw-away SQLite file with a warning.
# -------------------------------------------------------------
DATABASE_URL=postgresql://user:password@ep-xxxx-pooler.region.aws.neon.tech/neondb?sslmode=require

# -------------------------------------------------------------
# GOOGLE GEMINI AI ENGINE
# -------------------------------------------------------------
GEMINI_API_KEY=your_gemini_api_key_here
# Optional reliability helpers (all safe to leave unset):
#   GEMINI_BACKUP_KEYS     comma-separated keys from OTHER Google projects; used when the main key is rate-limited
#   GEMINI_FALLBACK_MODELS comma-separated backup models (default: gemini-3.5-flash-lite,gemini-3.1-flash-lite);
#                          set it to an empty value to disable. The main model is always tried first.
#   APP_BASE_URL           public site URL used for links inside emails, e.g. https://your-app.onrender.com
#   FEEDBACK_TO_EMAIL      where feedback from the in-app feedback box is e-mailed (default: MAIL_USERNAME)
#   UPLOAD_FOLDER          override the folder where resumes are stored

# -------------------------------------------------------------
# GOOGLE OAUTH 2.0 (Optional - for Google Single Sign-On)
# -------------------------------------------------------------
GOOGLE_CLIENT_ID=your_google_oauth_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret

# -------------------------------------------------------------
# EMAIL DELIVERY & OTP SERVICES (Optional - with SMTP fallback)
# Priority: Resend → SendGrid → SMTP
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

> **Security Note:** Never commit your `.env` file to version control. The `.gitignore` already excludes it. For cloud deployments, set all variables directly in your hosting provider's environment dashboard.

---

## 🚀 Installation & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/MR360-TECH/AI_INTERVIEW_PLATFORM_3.git
cd AI_INTERVIEW_PLATFORM_3
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

### 4. Configure Environment Variables

Copy the environment template and fill in your credentials before running the app.

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

> **First Launch:** The application automatically creates all required database tables (with live schema migration for missing columns) and initializes the admin account on startup. No manual migration commands are needed.

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

> **Persistent Storage on Render:** SQLite data is written to `/var/data/` on Render's persistent disk when available, preventing data loss across deploys. Resume uploads are also stored in `/var/data/uploads/`.

---

## 🗺️ Roadmap

The platform is under active development. Planned improvements include:

| Status | Feature |
|---|---|
| ✅ Done | Live AI interview with adaptive questioning |
| ✅ Done | Anti-cheat proctoring (2-strike system, admin toggle) |
| ✅ Done | Voice dictation with waveform visualizer |
| ✅ Done | Resume-driven personalized questions |
| ✅ Done | Monaco code editor sandbox |
| ✅ Done | File/image upload for diagram questions |
| ✅ Done | Google OAuth + OTP + Password authentication |
| ✅ Done | Company-specific prep hub (11 companies) |
| ✅ Done | Admin control panel with attempt unlock |
| ✅ Done | Clean 4-layer modular MODULES architecture |
| ✅ Done | Professional + Student user type profiles |
| ✅ Done | Settings cache with TTL invalidation |
| 🔄 Planned | Webcam-based facial proctoring (optional) |
| 🔄 Planned | Multi-language UI localization |
| 🔄 Planned | Recruiter portal for candidate shortlisting |
| 🔄 Planned | Scheduled interview slots with email reminders |
| 🔄 Planned | Leaderboard and peer performance benchmarking |
| 🔄 Planned | Mobile PWA wrapper |

---

## ❓ Frequently Asked Questions

**Q: Does the platform save my interview chat transcript?**  
A: Only the active in-progress chat history is stored temporarily in the database (`interview_progress`) to support resume/refresh. After the interview is evaluated, only the final score, summary, and metadata are retained — not the raw question-answer chat log.

**Q: Can I retake the interview if I fail?**  
A: By default, 2 attempts are permitted per user to maintain assessment integrity. Admins can grant additional attempts individually from the admin panel using the "Unlock Attempt" feature, or configure the global default from Admin Settings.

**Q: What happens if I switch tabs during an interview?**  
A: The proctoring system detects it immediately. The first violation shows a warning modal. The second violation auto-terminates and flags your session as "Terminated" in the database. The admin can disable this behavior via `enable_warning_strikes` in settings.

**Q: Is an internet connection required for the code editor?**  
A: Yes — the Monaco Editor is loaded from CDN. However, the code editor is purely for input; Python code is not executed on the server — it is submitted as text and evaluated by the AI.

**Q: What database does the platform use?**
A: **Neon PostgreSQL**, configured with the `DATABASE_URL` environment variable (the same value for local development and production). Tables and missing columns are created automatically at startup. If `DATABASE_URL` is not set, local runs fall back to a temporary SQLite file with a warning, and a Render deployment refuses to start so data is never lost silently.

**Q: Is a paid API key required to run the platform?**  
A: The Google Gemini API has a generous free tier that covers typical usage. Email delivery via Resend and SendGrid also offer free tiers. The platform is designed to be **fully operational at zero cost** for personal and small-scale use.

**Q: What is the difference between Student and Professional user types?**  
A: Student profiles require Education, Course, and Semester fields. Professional profiles require Current Designation and Years of Experience instead. The AI difficulty level adapts accordingly.

---

## 🤝 Contributing

Contributions, bug reports, and feature suggestions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: add your feature description"`
4. Push to your branch: `git push origin feature/your-feature-name`
5. Open a Pull Request against the `main` branch

Please make sure your code follows PEP 8 style guidelines and that all new routes are properly secured with session checks. New controllers should be added as Blueprints under `MODULES/LAYER_4_ROUTE_CONTROLLERS/` and registered in `register_blueprints()`.

---

## 📄 License & Attribution

Distributed under the **MIT License**. Developed and maintained by **MR360-TECH**.

---

**Developed by Gowtham V, Akash S and Charitha M** · [MR360-TECH](https://github.com/MR360-TECH)
