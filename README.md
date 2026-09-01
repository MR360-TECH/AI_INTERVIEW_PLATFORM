# 🤖 AI Interview Platform

An enterprise-grade, full-stack conversational mock interview platform engineered to prepare candidates for modern technical and non-technical roles through highly realistic, adaptive, and personalized simulations. The system leverages state-of-the-art Large Language Models (specifically Google Gemini AI) acting as a dynamic examiner, while a robust relational database layer (featuring SQLAlchemy with native support for MySQL, PostgreSQL, and SQLite fallback) securely persists candidate personas, resume data, and chronological scorecards. Engineered with production-ready resiliency, the application integrates multi-provider OTP verification loops, real-time voice-to-text dictation, and complete administrative control dashboards to bridge the gap between academic preparation and professional recruitment standards.

> **Built for:** Final-year students, fresh graduates, and early-career professionals seeking structured, intelligent, and domain-specific mock interview practice — far beyond what static quiz platforms can offer.

---


## 🎯 Project Objective

This platform was conceived to address a fundamental gap in the job preparation ecosystem. While numerous resources exist for learning and practising technical concepts, candidates rarely get the opportunity to experience a true, unscripted interview simulation before facing one in a real recruitment context.

The AI Interview Platform delivers exactly that — an intelligent, conversational mock interview experience driven by a live AI examiner that adapts to each candidate's individual knowledge level, background, and professional domain. By integrating resume parsing, OTP-secured onboarding, voice dictation, and detailed AI-generated scorecards, the platform provides students and job seekers with actionable, personalised feedback that directly accelerates their interview readiness and professional confidence.

---

## 🚀 Core Innovations

* **Stateful Conversational Interview Engine**: Unlike conventional platforms that serve static question banks, this system models each interview as a live, stateful dialogue. On every interaction, the complete conversation transcript is forwarded to the AI examiner, enabling it to construct contextually intelligent follow-up questions that directly respond to the candidate's preceding answer — mirroring the reasoning pattern of a real human interviewer.

* **Adaptive Difficulty Scaling**: The assessment engine continuously evaluates response quality and recalibrates the complexity of subsequent questions accordingly. Strong, well-articulated answers trigger a progressive escalation in technical depth, while incomplete or uncertain responses prompt the AI to revisit foundational concepts — creating a self-correcting evaluation loop that reflects actual interview dynamics.

* **Resume-Driven Personalisation**: Candidates may upload their CV in PDF format. The platform parses and indexes the extracted text into the candidate's database profile, which is then embedded into the AI's prompt context at assessment time. This allows the examiner to ask role-specific, project-aware, and technology-relevant questions drawn directly from the candidate's professional background.

* **Persistent Session Architecture**: Rather than relying on browser-native cookie storage — which imposes a strict 4KB payload ceiling — active interview transcripts are serialised and persisted in a dedicated relational database table. This guarantees full session continuity across network interruptions, tab closures, or browser refreshes, without any loss of conversational state.

* **Zero-Downtime Schema Auto-Migration**: On every application boot, the platform introspects the live database schema and programmatically applies any missing column definitions. This eliminates manual migration steps, prevents schema drift across environments, and ensures backward compatibility when new candidate data fields are introduced.


---

## 🔄 End-to-End Application Workflow

The platform operates as a cohesive lifecycle that takes a candidate from registration to a final AI-generated scorecard.

```mermaid
flowchart TD
    Start([Candidate Visits Platform]) --> Auth[1. Authentication & Onboarding]
    Auth --> Resume[2. Resume Setup & Processing]
    Resume --> Config[3. Assessment Track Configuration]
    Config --> Prep[Optional: Explore Curated Prep Hub]
    Config --> Loop[4. Dynamic Conversational Interview Loop]
    Loop --> Evaluation[5. AI Grading & Result Persistence]
    Evaluation --> AdminPanel[6. Admin Dashboard Monitoring]
    AdminPanel --> End([Platform Lifecycle Complete])
```

### 1. Authentication & Onboarding
* Candidates can sign up locally or instantly log in via third-party OAuth providers (Google OAuth 2.0). 
* To ensure secure registrations, the backend runs a multi-provider OTP verification loop. Once a candidate submits their email, the system automatically dispatches a unique one-time password (OTP) via high-priority mail delivery channels before password configuration.

### 2. Resume Setup & Processing
* After verifying their account, candidates can upload their resume in PDF format.
* The backend extracts the raw text from the resume on submission. It saves this information to the database profile, creating a persistent technical persona that the AI can reference during assessments.

### 3. Assessment Track Configuration
* Candidates configure their practice session by selecting their target technical domain (e.g., Data Science, React Frontend, Backend Python), preferred difficulty level, and experience class (student or professional).
* Alternatively, candidates can browse the built-in Prep Hub, which surfaces curated external technical challenge sets and interview preparation guides for top-tier companies.

### 4. Dynamic Conversational Interview Loop
* Once the session starts, the application initialises a session-tracking record in the database.
* The system constructs a structured prompt payload incorporating candidate experience details, target difficulty, parsed resume context, and the full running chat transcript.
* The AI generates a tailored, domain-specific question on each iteration.
* Candidates respond via typed input or real-time voice dictation, which transcribes microphone audio directly into the answer field.
* The loop continues dynamically until the AI determines sufficient evaluation signal has been gathered, capping at a configurable maximum question count.

### 5. AI Grading & Result Persistence
* Upon completion, the full conversational transcript is submitted to Gemini's evaluation pipeline.
* The model assesses communication depth, analytical capability, and domain accuracy, producing a structured scorecard: overall score (out of 10), bulleted strengths, improvement areas, and an executive summary.
* The score is benchmarked against the configured pass threshold, the result is tagged Selected or Rejected, persisted to the database, and the active progress record is cleared.
* Candidates are redirected to an interactive scorecard interface with full transcript review and PDF export capabilities.

### 6. Admin Dashboard Monitoring
* Administrators access a protected dashboard surfacing aggregate metrics: all-time interview counts, daily activity, and candidate performance distributions.
* Admins can inspect individual candidate profiles, review full Q&A transcripts, prune obsolete records, and adjust global assessment parameters — pass score thresholds and question count limits — in real time.

---

## 🚀 Key Features

* **Dual-Method Authentication Gateway**: Seamless local registration with Werkzeug password hashing alongside Google OAuth 2.0 OpenID Connect flows.
* **Multi-Provider OTP Routing**: An email routing dispatcher that automatically tries Resend HTTP API, SendGrid HTTP API, and SMTP fallbacks sequentially, avoiding hosting-tier port restrictions.
* **Web Speech Voice Integration**: Hands-free voice dictation enabling candidates to speak their answers using client-side microphone APIs, transcribed in real-time.
* **Visual Evaluation Reports**: Detailed AI-graded scorecards mapping scores, strengths, weaknesses, and direct download links to printable PDF reports.
* **Operational Control Center**: Admin panel featuring real-time candidate lists, click-through transcript readers, and settings consoles to configure global question caps and pass score thresholds.
* **Curated Interview Prep Hub**: Integrated preparation resource hub linking to external technical challenges and interview guides across top-tier companies — Google, Amazon, Meta, Microsoft, TCS, Infosys, Wipro, Accenture, and more.
* **Theme-Optimised Design System**: High-performance Bootstrap 5 interface featuring dark-mode gradients, smooth state transitions, and fully responsive cards.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **Web Framework** | Flask 3.0+ |
| **Templating** | Jinja2 |
| **ORM** | Flask-SQLAlchemy |
| **Database (Production)** | MySQL 8.0+ / PostgreSQL |
| **Database (Development)** | SQLite (auto-fallback) |
| **AI Model** | Google Gemini (`gemini-flash-lite-latest`) |
| **AI SDK** | `google-genai` Python SDK |
| **Authentication** | Werkzeug (password hashing), Authlib (Google OAuth 2.0) |
| **Email Delivery** | Resend HTTP API, SendGrid HTTP API, Gmail SMTP |
| **Voice Input** | Web Speech API (`webkitSpeechRecognition`) |
| **Frontend** | HTML5, CSS3, Bootstrap 5, Bootstrap Icons |
| **Deployment** | Render (Gunicorn + Procfile + render.yaml) |
| **Version Control** | Git & GitHub |

---

## 🔐 Security Architecture

The platform is built with a security-first mindset across all layers of the stack:

| Concern | Implementation |
|---|---|
| **Password Storage** | All passwords are hashed using Werkzeug's PBKDF2-SHA256 algorithm before persistence — plaintext credentials are never stored |
| **Session Integrity** | Flask session cookies are cryptographically signed via a server-side `SECRET_KEY` and flagged `HttpOnly` and `SameSite=Lax` to prevent client-side tampering and CSRF abuse |
| **HTTPS Enforcement** | In production environments, `SESSION_COOKIE_SECURE` is activated and requests are normalised through `ProxyFix` middleware to correctly resolve HTTPS scheme headers from reverse proxies |
| **OAuth 2.0 Token Flow** | Google sign-in uses the Authlib OpenID Connect flow — no passwords are transmitted or stored for OAuth-authenticated users |
| **OTP Verification** | Email-based OTP codes are single-use, session-scoped, and invalidated immediately upon successful verification |
| **API Key Isolation** | All third-party API keys (Gemini, Resend, SendGrid, Google OAuth) are loaded exclusively from environment variables and are never committed to source control |
| **Route-Level Access Control** | All candidate and admin routes enforce session-based authentication checks — admin routes apply a secondary credential layer to ensure strict role isolation |
| **Automatic Security Headers** | An `after_request` hook injects production-grade HTTP security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) on every response |

---

## 📊 Detailed Database Schema & ER Model



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

### Database Tables Breakdown
1. **`users` Table**: Stores candidate profile information, registration method (local, OAuth, or OTP), and parsed resume texts used to tailor the interview.
2. **`interview_results` Table**: Persists the outcomes of completed mock interviews, containing the overall evaluation details (score, verdict status, strengths, improvements, domain, and completion times).
3. **`interview_progress` Table**: Backs up in-progress assessment states (including the serialized chat history) so candidates can resume if disconnected, bypassing browser session storage limits.
4. **`admin_settings` Table**: Holds global evaluation parameters editable by administrative accounts.

---

## 🧠 Gemini AI Prompt Mechanics & Logic Flow

The AI engine uses Google Gemini dynamically in two operational loops:

```
[Candidate starts practice]
       │
       ▼
1. Adaptive Question Loop
   ├── Input context: target domain + difficulty + parsed resume text + full chat history
   ├── Prompt constraint: Output strictly ONLY a single raw question (under 2 sentences). No fluff.
   └── Output: Next question served to candidate
       │
[Loop repeats 5 to 8 times until Gemini signals completion or max count is reached]
       │
       ▼
2. Full Transcript Evaluation
   ├── Input context: Full interview Q&A transcript
   ├── Prompt constraint: Output JSON with: score, strengths, improvements, summary
   └── Output: Record saved in DB, linked to user, evaluation screen displayed to user
```

* **Dynamic Constraints**: The AI is strictly bound to the target domain, references candidate experience parameters, and is barred from outputting preambles or conversational filler.
* **Score-to-Verdict Mapping**: The system compares the AI evaluation score against the threshold set in `admin_settings` to dynamically determine candidate selection status.

---

## ⚙️ Configuration Parameters (Environment Variables)

The application consumes environment configurations from a local `.env` file. These configurations define authentication and mail APIs conceptually:

* **Core Settings**:
  * `SECRET_KEY`: Used by Flask to sign session cookies securely.
* **Database Connection**:
  * `DATABASE_URL`: Connection string mapping to external engines (MySQL/PostgreSQL). If undefined, falls back automatically to SQLite.
* **AI Platform API**:
  * `GEMINI_API_KEY`: API access key for connecting to Google Gemini AI models.
* **OAuth Credentials**:
  * `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Client IDs and secrets required for Google OAuth 2.0 logins.
* **OTP Delivery APIs**:
  * `RESEND_API_KEY` / `SENDGRID_API_KEY`: Integrations for Resend or SendGrid HTTP mail delivery.
  * `MAIL_USERNAME` / `MAIL_PASSWORD`: Standard SMTP credentials used as fallback delivery.
* **Operations Credentials**:
  * `ADMIN_EMAIL` / `ADMIN_PASSWORD`: Administrative dashboard credentials (auto-generated if not supplied).

---

## 🚀 Execution & Run Guide

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
   *Note: On startup, the SQL engine verifies tables and implements migrations dynamically.*

---

## 👨‍💻 Developed By

**Gowtham V**
