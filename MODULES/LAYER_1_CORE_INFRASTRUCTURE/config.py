import os
import secrets
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth

# Locate and load root .env explicitly
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_env_file = os.path.join(_root_dir, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file, override=True)
else:
    load_dotenv(override=True)

# Core extensions instances
db = SQLAlchemy()
oauth = OAuth()

IS_PRODUCTION = bool(
    os.environ.get("DATABASE_URL")
    or os.environ.get("RENDER")
    or os.environ.get("RAILWAY_ENVIRONMENT")
    or os.environ.get("FLASK_ENV") == "production"
)

# Sessions and one-time codes are signed with this key, so it must be secret. A key written in the source code would be
# public, so there is no built-in fallback. Order of preference:
#   1. the SECRET_KEY environment variable (recommended: set a long random value in the hosting dashboard)
#   2. a key derived from the private DATABASE_URL (stable across restarts and workers, never in the source code), so a
#      hosted service that has no SECRET_KEY yet still starts safely
#   3. local development only: a random temporary key
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    _private = os.environ.get("DATABASE_URL")
    if _private:
        import hashlib
        SECRET_KEY = hashlib.sha256(("session-signing-key|" + _private).encode()).hexdigest()
        print(" * NOTE: SECRET_KEY is not set, so a private key derived from DATABASE_URL is used. Set SECRET_KEY for best practice.")
    else:
        SECRET_KEY = secrets.token_hex(32)
        print(" * NOTE: SECRET_KEY is not set, using a temporary random key (sessions reset when the server restarts).")

# Optional: require an e-mailed code for the admin sign-in as well (set ADMIN_2FA=true)
ADMIN_2FA = (os.environ.get("ADMIN_2FA") or "").strip().lower() in ("1", "true", "yes", "on")

# Admin credentials
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

if not ADMIN_EMAIL:
    ADMIN_EMAIL = f"admin_{secrets.token_hex(4)}@example.com"

if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(18)
    print(f" * SECURE WARNING: ADMIN_PASSWORD environment variable was not set.")
    print(f" * A random temporary password has been generated for this session: {ADMIN_PASSWORD}")

# Database: Neon PostgreSQL, selected with DATABASE_URL (the same database for local development and production).
db_url = (os.environ.get("DATABASE_URL") or "").strip()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if not db_url:
    if os.environ.get("RENDER"):
        # A silent SQLite fallback on Render would lose all data on the next deploy, so refuse to start.
        raise RuntimeError("DATABASE_URL is not set. Add your Neon connection string to the Render environment variables.")
    print(" * WARNING: DATABASE_URL is not set - using a local SQLite file. Data will NOT be stored in Neon.")
    db_url = "sqlite:///ai_interview_platform.db"
elif "neon.tech" in db_url and "sslmode=" not in db_url:
    db_url += ("&" if "?" in db_url else "?") + "sslmode=require"

SQLALCHEMY_DATABASE_URI = db_url
SQLALCHEMY_TRACK_MODIFICATIONS = False

SQLALCHEMY_ENGINE_OPTIONS = {}
if not db_url.startswith("sqlite"):
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,      # Neon suspends idle compute and drops connections: test a connection before using it
        'pool_recycle': 280,
        'pool_timeout': 20,
        'pool_size': 5,
        'max_overflow': 5,
    }
    if db_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {
            'connect_timeout': 15,  # a sleeping Neon database needs a few seconds to wake up
            'keepalives': 1, 'keepalives_idle': 30, 'keepalives_interval': 10, 'keepalives_count': 5,
        }

# File uploads — always an absolute path. A relative folder is resolved against the Flask
# package directory by send_from_directory(), so saved resumes could never be served back.
render_persistent_dir = "/var/data"
if os.environ.get("UPLOAD_FOLDER"):
    UPLOAD_FOLDER = os.path.abspath(os.environ["UPLOAD_FOLDER"])
elif os.environ.get("RENDER") and os.path.exists(render_persistent_dir):
    UPLOAD_FOLDER = os.path.join(render_persistent_dir, 'uploads')
else:
    UPLOAD_FOLDER = os.path.join(_root_dir, 'uploads')

MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB limit
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
ALLOWED_RESUME_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}

# Google OAuth credentials
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
has_google_oauth = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

# Public base URL used for links inside emails (set APP_BASE_URL in production)
APP_BASE_URL = (os.environ.get("APP_BASE_URL") or "https://ai-interview-platform-3-vdic.onrender.com").strip().rstrip("/")

# Where user feedback is e-mailed: FEEDBACK_TO_EMAIL if set, otherwise the mailbox the app already sends from.
FEEDBACK_TO_EMAIL = (os.environ.get("FEEDBACK_TO_EMAIL") or os.environ.get("MAIL_USERNAME") or os.environ.get("ADMIN_EMAIL") or "").strip()

# Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-flash-lite-latest"
