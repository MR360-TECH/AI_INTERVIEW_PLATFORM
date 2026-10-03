import os
from flask import Flask, render_template, request, redirect, session, jsonify
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db, oauth
from MODULES.LAYER_1_CORE_INFRASTRUCTURE import config
from MODULES.LAYER_2_DATA_PERSISTENCE import models
from MODULES.LAYER_4_ROUTE_CONTROLLERS import register_blueprints

# Columns added after the first release. db.create_all() never alters existing tables, so older
# databases get them here. Defaults are portable (SQLite, MySQL and PostgreSQL all accept TRUE/FALSE).
_REQUIRED_COLUMNS = {
    'users': [
        ('resume_text', 'TEXT'),
        ('resume_filename', 'VARCHAR(255)'),
        ('extra_allowed_interviews', 'INTEGER DEFAULT 0'),
        ('attempts_count', 'INTEGER DEFAULT 0'),
        ('welcome_sent', 'BOOLEAN DEFAULT FALSE'),
    ],
    'interview_results': [
        ('is_terminated', 'BOOLEAN DEFAULT FALSE'),
        ('termination_reason', 'TEXT'),
    ],
    'admin_settings': [
        ('enable_warning_strikes', 'BOOLEAN DEFAULT TRUE'),
        ('enable_feedback_emails', 'BOOLEAN DEFAULT TRUE'),
        ('max_strikes', 'INTEGER DEFAULT 2'),
        ('proctor_server_strikes', 'BOOLEAN DEFAULT TRUE'),
        ('proctor_single_session', 'BOOLEAN DEFAULT TRUE'),
        ('proctor_server_timer', 'BOOLEAN DEFAULT TRUE'),
        ('proctor_block_copy_paste', 'BOOLEAN DEFAULT TRUE'),
        ('proctor_fullscreen', 'BOOLEAN DEFAULT FALSE'),
        ('proctor_typing_flags', 'BOOLEAN DEFAULT TRUE'),
        ('proctor_integrity_log', 'BOOLEAN DEFAULT TRUE'),
        ('enable_rate_limits', 'BOOLEAN DEFAULT TRUE'),
    ],
    'interview_progress': [
        ('strikes', 'INTEGER DEFAULT 0'),
        ('sid', 'VARCHAR(40)'),
        ('last_seen_at', 'TIMESTAMP'),
        ('question_shown_at', 'TIMESTAMP'),
    ],
}


def ensure_columns():
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    for table, columns in _REQUIRED_COLUMNS.items():
        if not inspector.has_table(table):
            continue
        existing = {c['name'] for c in inspector.get_columns(table)}
        for column_name, ddl in columns:
            if column_name in existing:
                continue
            # One transaction per column: on PostgreSQL a failed statement would otherwise abort the rest.
            try:
                with db.engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {ddl}"))
                print(f"Added column '{column_name}' dynamically to {table} table.")
                if (table, column_name) == ('users', 'welcome_sent'):
                    # Accounts that existed before this feature must never receive a "welcome" email.
                    with db.engine.begin() as conn:
                        conn.execute(text("UPDATE users SET welcome_sent = TRUE"))
            except Exception as schema_err:
                print(f"Schema check notice ({table}.{column_name}): {schema_err}")


def _rgb(hex_color):
    h = (hex_color or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _luminance(rgb):
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readable_color(hex_color, background="#08122a", minimum=5.2):
    """A company's brand colour is often dark navy/black. Used as TEXT on the app's dark cards it vanishes, so lighten
    it step by step until it reaches the minimum contrast against the card background (brand hue is preserved)."""
    try:
        rgb, bg = _rgb(hex_color), _rgb(background)
    except (ValueError, TypeError):
        return "#e2e8f0"
    for _ in range(25):
        lighter, darker = sorted((_luminance(rgb), _luminance(bg)), reverse=True)
        if (lighter + 0.05) / (darker + 0.05) >= minimum:
            break
        rgb = tuple(int(c + (255 - c) * 0.15) for c in rgb)
    return "#%02x%02x%02x" % rgb


def ink_on(hex_color):
    """Dark or white text, whichever is readable on a solid brand-colour background."""
    try:
        return "#020510" if _luminance(_rgb(hex_color)) > 0.35 else "#ffffff"
    except (ValueError, TypeError):
        return "#ffffff"


def create_app():
    # Set template and static folders relative to project root
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_folder = os.path.join(root_dir, 'templates')
    static_folder = os.path.join(root_dir, 'static')

    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder
    )
    app.secret_key = config.SECRET_KEY
    app.jinja_env.filters["readable"] = readable_color
    app.jinja_env.filters["ink_on"] = ink_on

    # Temporary helper text on the verification-code page while e-mails may land in spam (no verified domain yet).
    # Remove it later by setting SHOW_SPAM_HINT=false (or by deleting the marked block in verify_otp.html).
    @app.context_processor
    def inject_legal_contact():
        """The public contact address shown on the legal pages comes from configuration (FEEDBACK_TO_EMAIL / MAIL_USERNAME)."""
        return {"contact_email": getattr(config, "FEEDBACK_TO_EMAIL", "") or ""}

    @app.context_processor
    def inject_mail_hint():
        return {"show_spam_hint": (os.environ.get("SHOW_SPAM_HINT", "true").strip().lower() not in ("0", "false", "no", "off"))}

    # Session cookie security
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if config.IS_PRODUCTION:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["PREFERRED_URL_SCHEME"] = "https"

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    if config.SQLALCHEMY_ENGINE_OPTIONS:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = config.SQLALCHEMY_ENGINE_OPTIONS

    # Uploads configuration
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

    # Initialize extensions
    db.init_app(app)
    oauth.init_app(app)

    # Register Google OAuth provider
    if config.has_google_oauth:
        oauth.register(
            name='google',
            client_id=config.GOOGLE_CLIENT_ID,
            client_secret=config.GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )

    # Performance optimization: static asset caching
    @app.after_request
    def add_performance_headers(response):
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=86400'
        return response

    # Security headers
    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
        if config.IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # CSRF tokens, idle/absolute session timeout, Content-Security-Policy, no caching of signed-in pages
    from MODULES.LAYER_3_BUSINESS_SERVICES.rate_limit import init_rate_limits
    init_rate_limits(app)                      # friendly, very loose limits (registered first so floods are stopped cheaply)
    from MODULES.LAYER_3_BUSINESS_SERVICES.web_security import init_web_security
    init_web_security(app)

    # Error handlers
    @app.errorhandler(413)
    def request_entity_too_large(error):
        if "user_id" in session:
            return redirect("/dashboard?error=file_too_large")
        return redirect("/login?error=file_too_large")

    def _error_context():
        """Where the Back button should lead, and whether the person is in the middle of an interview."""
        path = request.path
        in_interview = ("user_id" in session and not session.get("is_admin") and path != "/interview-result"
                        and path.startswith(("/interview", "/finish-interview", "/practice", "/terminate-proctoring", "/quit-interview")))
        if in_interview:
            back_url = "/interview"                      # resumes the saved interview, never restarts it
        elif session.get("is_admin"):
            back_url = "/admin"
        elif "user_id" in session:
            back_url = "/dashboard"
        else:
            back_url = "/login"
        return in_interview, back_url

    def _wants_json():
        return (request.is_json or "X-CSRF-Token" in request.headers or path_is_ajax())

    def path_is_ajax():
        return request.path == "/interview/submit" or "application/json" in request.headers.get("Accept", "")

    @app.errorhandler(500)
    def internal_server_error(error):
        try:
            db.session.rollback()
        except Exception:
            pass
        import secrets as _secrets
        reference = "ERR-" + _secrets.token_hex(3).upper()
        print(f"[Internal Server Error {reference}] {request.method} {request.path}: {error}")
        in_interview, back_url = _error_context()
        message = ("Something went wrong on our side while loading this page." if not in_interview
                   else "Something went wrong on our side while processing your last step.")
        if _wants_json():
            # nothing is invented for the client: the saved interview is the source of truth, and Back resumes it
            return jsonify({"error": "server_error", "message": message, "back_url": back_url, "reference": reference,
                            "progress_saved": in_interview}), 500
        return render_template("error.html", code=500, title="We hit a problem", eyebrow="Server error", icon="bi-tools",
                               message=message, in_interview=in_interview, back_url=back_url, reference=reference), 500

    @app.errorhandler(404)
    def page_not_found(error):
        _, back_url = _error_context()
        if _wants_json():
            return jsonify({"error": "not_found", "message": "That page does not exist.", "back_url": back_url}), 404
        return render_template("error.html", code=404, title="Page not found", eyebrow="Error 404", icon="bi-compass",
                               message="The page you are looking for does not exist or has moved.", in_interview=False,
                               back_url=back_url, reference=None), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        _, back_url = _error_context()
        if _wants_json():
            return jsonify({"error": "method_not_allowed", "message": "That action is not available.", "back_url": back_url}), 405
        return render_template("error.html", code=405, title="That action is not available", eyebrow="Error 405", icon="bi-slash-circle",
                               message="This link cannot be opened directly. Please go back and use the buttons on the page instead.",
                               in_interview=False, back_url=back_url, reference=None), 405

    # Register blueprints
    register_blueprints(app)

    # Initialize tables and verify schema
    with app.app_context():
        try:
            db.create_all()
            ensure_columns()
            print("Database tables verified/created successfully.")
        except Exception as e:
            print(f"Error creating/verifying database tables: {e}")

    return app
