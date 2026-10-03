"""Browser-facing security for the whole app, registered once in create_app().

  * CSRF protection: every state-changing request (POST/PUT/PATCH/DELETE) must carry the per-session token. The token is
    added to every HTML form and to every same-site fetch() automatically, so no template needs to remember it.
  * Session timeout: an idle admin is signed out after ADMIN_IDLE_MINUTES (30), an idle candidate after
    USER_IDLE_MINUTES (120); no session lives longer than SESSION_MAX_HOURS (12).
  * Content-Security-Policy and "do not cache signed-in pages" headers.
  * Password rules shared by sign-up and reset.
"""
import hmac
import os
import re
import secrets
import time

from flask import jsonify, redirect, request, session

ADMIN_IDLE_SECONDS = int(os.environ.get("ADMIN_IDLE_MINUTES", "30")) * 60
USER_IDLE_SECONDS = int(os.environ.get("USER_IDLE_MINUTES", "120")) * 60
SESSION_MAX_SECONDS = int(os.environ.get("SESSION_MAX_HOURS", "12")) * 3600

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://www.google.com https://www.gstatic.com",
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
    "font-src 'self' data: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com",
    "img-src 'self' data: blob: https:",
    "connect-src 'self' https://cdnjs.cloudflare.com",
    "media-src 'self' blob:",
    "worker-src 'self' blob: data:",
    "frame-src 'self' https://www.google.com",
    "object-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'self'",
])

# Added to every HTML page: the token in a <meta> tag, plus a tiny script that puts it on same-site fetch() calls and on
# any form that JavaScript creates later.
_CLIENT_SCRIPT = (
    '<meta name="csrf-token" content="{token}">'
    "<script>(function(){{var t='{token}',f=window.fetch;"
    "window.fetch=function(u,o){{o=o||{{}};var m=String(o.method||'GET').toUpperCase();"
    "if(m!=='GET'&&m!=='HEAD'&&(typeof u!=='string'||u.charAt(0)==='/'||u.indexOf(location.origin)===0)){{"
    "o.headers=new Headers(o.headers||{{}});o.headers.set('X-CSRF-Token',t);}}return f.call(this,u,o);}};"
    "document.addEventListener('submit',function(e){{var fm=e.target;"
    "if(fm&&String(fm.method).toLowerCase()==='post'&&!fm.querySelector('input[name=csrf_token]')){{"
    "var i=document.createElement('input');i.type='hidden';i.name='csrf_token';i.value=t;fm.appendChild(i);}}}},true);"
    "}})();</script>"
)
# Themed progress bar while another page loads; also clears any "loading" overlay when the browser restores a page from its
# back/forward cache, so a spinner can never be left stuck on screen.
_MOTION_SCRIPT = (
    "<script>(function(){var bar;function B(){if(!bar){bar=document.createElement('div');bar.id='navBar';"
    "(document.body||document.documentElement).appendChild(bar);}return bar;}"
    "function go(){var b=B();b.className='';void b.offsetWidth;b.className='on';}"
    "document.addEventListener('click',function(e){var a=e.target&&e.target.closest?e.target.closest('a[href]'):null;"
    "if(!a||e.defaultPrevented||e.button||e.ctrlKey||e.metaKey||e.shiftKey||a.target==='_blank'||a.hasAttribute('download'))return;"
    "var u;try{u=new URL(a.href,location.href);}catch(x){return;}"
    "if(u.origin!==location.origin||(u.pathname===location.pathname&&u.search===location.search))return;go();},true);"
    "document.addEventListener('submit',function(e){if(!e.defaultPrevented)go();},false);"
    "window.addEventListener('pageshow',function(){if(bar)bar.className='';var o=document.getElementById('loadingOverlay');"
    "if(o)o.classList.remove('active');});})();</script>"
)
_POST_FORM = re.compile(r"(<form\b[^>]*\bmethod\s*=\s*[\"']?post[\"']?[^>]*>)", re.IGNORECASE)


def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = session["_csrf"] = secrets.token_urlsafe(32)
    return token


def _wants_json():
    return request.is_json or "X-CSRF-Token" in request.headers or "application/json" in request.headers.get("Accept", "")


def _reject(code, message, login_error=None):
    if _wants_json():
        return jsonify({"status": "error", "error": code, "message": message}), (401 if code == "session_expired" else 400)
    if login_error:
        return redirect(f"/login?error={login_error}")
    return (f"<h3>{message}</h3><p><a href='/'>Back</a></p>", 400)


def init_web_security(app):
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def enforce_session_timeout():
        if request.path.startswith("/static/"):
            return None
        is_admin, is_user = session.get("is_admin"), session.get("user_id")
        if not (is_admin or is_user):
            return None
        now = time.time()
        started, last = session.setdefault("_started", now), session.get("_last_seen", now)
        idle_limit = ADMIN_IDLE_SECONDS if is_admin else USER_IDLE_SECONDS
        if now - last > idle_limit or now - started > SESSION_MAX_SECONDS:
            session.clear()
            return _reject("session_expired", "Your session expired for security. Please sign in again.", "session_expired")
        session["_last_seen"] = now
        return None

    @app.before_request
    def enforce_csrf():
        if request.method not in UNSAFE_METHODS or not app.config.get("CSRF_ENABLED", True):
            return None
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or ""
        expected = session.get("_csrf") or ""
        if expected and sent and hmac.compare_digest(sent, expected):
            return None
        return _reject("csrf", "This page expired or the request could not be verified. Please go back, reload the page and try again.")

    @app.after_request
    def add_page_protection(response):
        response.headers["Content-Security-Policy"] = CSP + ("; upgrade-insecure-requests" if os.environ.get("RENDER") else "")
        if response.mimetype == "text/html" and not response.direct_passthrough:
            if session.get("is_admin") or session.get("user_id"):
                response.headers["Cache-Control"] = "no-store"
            if response.status_code < 400 or response.status_code == 429:
                token = csrf_token()
                html = response.get_data(as_text=True)
                html = _POST_FORM.sub(lambda m: m.group(1) + f'<input type="hidden" name="csrf_token" value="{token}">', html)
                snippet = _CLIENT_SCRIPT.format(token=token) + _MOTION_SCRIPT
                html = html.replace("</head>", snippet + "</head>", 1) if "</head>" in html else snippet + html
                response.set_data(html)
        return response


# ──────────────────────────────────────────────────────────────────────────────
# Password rules (sign-up and reset)
# ──────────────────────────────────────────────────────────────────────────────

COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890", "qwerty123", "qwertyuiop", "iloveyou1",
    "admin123", "welcome1", "welcome123", "letmein123", "abc12345", "abcd1234", "test1234", "india123", "student123",
}


def password_problem(password, email=""):
    """Returns a short message when the password is not acceptable, otherwise None."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password must be at most 128 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    if password.lower() in COMMON_PASSWORDS:
        return "That password is too common. Please choose a less predictable one."
    local = (email or "").split("@")[0].lower()
    if len(local) >= 4 and local in password.lower():
        return "Password must not contain your email name."
    return None
