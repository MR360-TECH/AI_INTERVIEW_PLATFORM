import os
import hmac
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, url_for, jsonify, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db, oauth, ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_APPROVAL_EMAIL, APP_BASE_URL, SECRET_KEY, has_google_oauth
from MODULES.LAYER_2_DATA_PERSISTENCE.models import User, AdminDevice, is_valid_email, profile_is_complete
from MODULES.LAYER_3_BUSINESS_SERVICES.mailer import send_otp_email
from MODULES.LAYER_3_BUSINESS_SERVICES.auth_security import (
    issue_otp, verify_otp as check_otp, throttle_seconds_left, throttle_fail, throttle_reset, minutes_text,
    LOGIN_MAX_FAILURES, IP_MAX_FAILURES, OTP_SEND_MAX_PER_IP
)
from MODULES.LAYER_3_BUSINESS_SERVICES.feedback_email import queue_welcome_email, queue_admin_mail
from MODULES.LAYER_3_BUSINESS_SERVICES import admin_access as AA
from MODULES.LAYER_3_BUSINESS_SERVICES.web_security import password_problem

login_bp = Blueprint('login_bp', __name__)
register_bp = login_bp  # Alias for backward compatibility

BAD_LOGIN_MESSAGE = "Incorrect email or password. If you signed up with Google, use 'Continue with Google' instead."
_DUMMY_PASSWORD_HASH = generate_password_hash("not-a-real-password")

OTP_MESSAGES = {
    "invalid": "Invalid code. Please try again.",
    "expired": "This code has expired or is no longer valid. Please request a new one.",
    "locked": "Too many incorrect attempts. Please request a new code.",
}


def _client_ip():
    return request.remote_addr or "unknown"


def _otp_send_blocked():
    """Limits how many verification emails one IP can trigger (stops the forms being used to spam inboxes)."""
    key = f"otpsend:{_client_ip()}"
    if throttle_seconds_left(key):
        return True
    throttle_fail(key, OTP_SEND_MAX_PER_IP)
    return False


def send_welcome_once(user, via_google=False):
    """Queues the one-time welcome email. The flag is saved first, so it can never be sent twice,
    and any failure here must never break registration."""
    try:
        if user.welcome_sent:
            return
        user.welcome_sent = True
        db.session.commit()
        queue_welcome_email(user.email, user.full_name, via_google=via_google)
    except Exception as e:
        db.session.rollback()
        print(f"[WELCOME] could not queue welcome email: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# HOME & STATIC INFORMATION
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    if session.get("is_admin"):
        return redirect("/admin")
    return render_template("index.html")


@login_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@login_bp.route("/terms")
def terms():
    """The Terms of Use are Section 'Terms of Use' of the combined legal page."""
    return redirect("/privacy#terms")


# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD & CREDENTIALS LOGIN
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        next_url = AA.safe_next(request.form.get("next"), "")
        # "Keep me signed in" is ticked by default; unticked (shared computer) the session ends with the browser.
        remember = request.form.get("remember") == "on" if "remember_box" in request.form else True

        if not is_valid_email(email):
            return render_template("login.html", error="Please enter a valid email address.", prefill_email=email, has_google_oauth=has_google_oauth)

        if not password:
            return render_template("login.html", error="Please enter your password.", prefill_email=email, has_google_oauth=has_google_oauth)

        ip = _client_ip()
        key = f"login:{email}|{ip}"
        wait = max(throttle_seconds_left(key), throttle_seconds_left(f"ip:{ip}"))
        if wait:
            return render_template("login.html", error=f"Too many failed attempts. Please try again in {minutes_text(wait)}.",
                                   prefill_email=email, has_google_oauth=has_google_oauth), 429

        def failed(message=None, **extra):
            throttle_fail(key, LOGIN_MAX_FAILURES)
            throttle_fail(f"ip:{ip}", IP_MAX_FAILURES)
            return render_template("login.html", error=message, prefill_email=email, has_google_oauth=has_google_oauth, **extra)

        # One message for every failure (unknown email, wrong password, Google-only account, admin), so this form cannot
        # be used to find out which emails are registered.
        bad_login = BAD_LOGIN_MESSAGE

        # Admin check (constant-time comparison)
        if ADMIN_EMAIL and email == ADMIN_EMAIL.strip().lower():
            if ADMIN_PASSWORD and hmac.compare_digest(password.encode(), ADMIN_PASSWORD.strip().encode()):
                throttle_reset(key)
                return _admin_password_ok(next_url, remember)
            return failed(bad_login)

        user = User.query.filter_by(email=email).first()

        # Unknown emails and Google-only accounts still run one password hash check, so response time does not
        # reveal whether the account exists.
        stored_hash = user.password if user and user.password else _DUMMY_PASSWORD_HASH
        password_ok = check_password_hash(stored_hash, password) and bool(user and user.password)

        if user and password_ok:
            throttle_reset(key)
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.full_name
            session["user_email"] = user.email
            session["is_admin"] = False
            start_signed_in_session(remember)
            if not profile_is_complete(user):
                return redirect("/register")
            return redirect(next_url if next_url and not next_url.startswith("/admin") else "/dashboard")
        return failed(bad_login)

    error_msg = None
    err_code = request.args.get("error")
    if err_code == "file_too_large":
        error_msg = "Uploaded file is too large. The maximum size limit is 10MB."
    elif err_code == "google_not_configured":
        error_msg = "Google Sign-in is not configured on this server."
    elif err_code == "session_expired":
        error_msg = "Your session expired for security. Please sign in again."
    elif err_code == "device_removed":
        error_msg = "This device no longer has admin access. Sign in to request approval again."
    elif err_code == "device_cancelled":
        error_msg = "Request cancelled. Sign in again whenever you're ready."
    next_url = AA.safe_next(request.args.get("next"), "")
    return render_template("login.html", error=error_msg, has_google_oauth=has_google_oauth, next_url=next_url,
                           next_member=_member_in(next_url))


# ══════════════════════════════════════════════════════════════════════════════
# STAYING SIGNED IN, AND ADMIN DEVICE APPROVAL
# ══════════════════════════════════════════════════════════════════════════════

def start_signed_in_session(remember=True):
    """Marks a fresh sign-in. Remembered sessions last until Logout (the cookie survives closing the browser); others end
    with the browser. The password fingerprint is added on the next request (web_security)."""
    session["remember"] = bool(remember)
    session.permanent = bool(remember)


def admin_password_print():
    return AA.fingerprint(ADMIN_PASSWORD, "admin|" + (SECRET_KEY or ""))


def device_approval_on():
    return bool(ADMIN_APPROVAL_EMAIL)


def _member_in(next_url):
    """The member ID an e-mail button asked for ('/admin/users?q=AIP26A0001&open=1'), for the note on the sign-in page."""
    from urllib.parse import urlparse, parse_qs
    from MODULES.LAYER_2_DATA_PERSISTENCE.models import normalize_user_code
    if not next_url:
        return None
    return normalize_user_code((parse_qs(urlparse(next_url).query).get("q") or [""])[0])


def _current_device():
    token = request.cookies.get(AA.DEVICE_COOKIE)
    if not token:
        return None, None
    return token, AdminDevice.query.filter_by(token_hash=AA.token_hash(token)).first()


def _open_admin_session(device=None, next_url="", remember=True):
    session.clear()
    session["is_admin"] = True
    session["user_name"] = "Admin"
    session["admin_print"] = admin_password_print()
    if device is not None:
        session["admin_device"] = device.id
    start_signed_in_session(remember)
    return redirect(AA.safe_next(next_url, "/admin") if (next_url or "").startswith("/admin") else "/admin")


def _alert_signin(device):
    if device_approval_on():
        queue_admin_mail(ADMIN_APPROVAL_EMAIL, "admin_signin_alert_email",
                         device_label=device.label if device else AA.device_label(request.headers.get("User-Agent")),
                         ip=_client_ip(), when_text=datetime.utcnow().strftime("%d %B %Y, %H:%M UTC"),
                         settings_url=f"{APP_BASE_URL}/admin/settings#devices")


def _admin_password_ok(next_url, remember=True):
    """The admin password was right. On an approved device the admin area opens; a new device waits for approval."""
    if not device_approval_on():
        _alert_signin(None)
        return _open_admin_session(None, next_url, remember)

    now = datetime.utcnow()
    token, device = _current_device()
    if device and device.status == "approved" and device.password_print == admin_password_print():
        device.last_seen_at = now
        db.session.commit()
        _alert_signin(device)
        return _open_admin_session(device, next_url, remember)

    recent = AdminDevice.query.filter(AdminDevice.requested_at >= now - AA.timedelta(hours=1)).count()
    if recent >= AA.APPROVAL_REQUESTS_PER_HOUR and not (device and device.status == "pending" and not AA.approval_expired(device, now)):
        return render_template("login.html", error="Too many approval requests in the last hour. Please try again later.",
                               has_google_oauth=has_google_oauth), 429

    new_cookie = None
    if not device:
        new_cookie = AA.new_token()
        device = AdminDevice(token_hash=AA.token_hash(new_cookie), created_at=now)
        db.session.add(device)
    device.label = AA.device_label(request.headers.get("User-Agent"))
    device.ip = _client_ip()
    link = AA.open_approval(device, now)
    db.session.commit()
    queue_admin_mail(ADMIN_APPROVAL_EMAIL, "admin_device_request_email", device_label=device.label, ip=device.ip,
                     when_text=now.strftime("%d %B %Y, %H:%M UTC"), review_url=f"{APP_BASE_URL}/admin/device/review/{link}",
                     minutes=AA.APPROVAL_LINK_MINUTES)

    session.clear()
    session["admin_waiting_device"] = device.id
    session["admin_next"] = next_url
    session["admin_remember"] = remember
    response = make_response(redirect("/admin/waiting"))
    if new_cookie:
        response.set_cookie(AA.DEVICE_COOKIE, new_cookie, max_age=AA.DEVICE_COOKIE_DAYS * 86400, httponly=True,
                            secure=request.is_secure, samesite="Lax")
    return response


@login_bp.route("/admin/waiting")
def admin_waiting():
    if not session.get("admin_waiting_device"):
        return redirect("/login")
    return render_template("admin_device.html", mode="waiting", mailbox=AA.masked(ADMIN_APPROVAL_EMAIL),
                           minutes=AA.APPROVAL_LINK_MINUTES)


@login_bp.route("/admin/device/cancel", methods=["POST"])
def admin_device_cancel():
    """The waiting device gives up by itself: its own pending request is denied, so the e-mailed link can no longer
    approve it either, even if the owner presses Approve afterwards."""
    device_id = session.get("admin_waiting_device")
    if device_id:
        device = db.session.get(AdminDevice, device_id)
        if device and device.status == "pending":
            device.status, device.approve_hash, device.approve_expires = "denied", None, None
            db.session.commit()
    session.clear()
    return redirect("/login?error=device_cancelled")


@login_bp.route("/admin/device/status")
def admin_device_status():
    """Polled by the waiting page: has the owner answered yet?"""
    device_id = session.get("admin_waiting_device")
    token, device = _current_device()
    if not device_id or not device or device.id != device_id:
        return jsonify({"status": "unknown"}), 400
    if device.status == "approved" and device.password_print == admin_password_print():
        next_url = session.get("admin_next") or ""
        remember = session.get("admin_remember", True)
        device.last_seen_at = datetime.utcnow()
        db.session.commit()
        _open_admin_session(device, next_url, remember)
        return jsonify({"status": "approved", "next": AA.safe_next(next_url, "/admin") if next_url.startswith("/admin") else "/admin"})
    if device.status == "denied":
        session.clear()
        return jsonify({"status": "denied"})
    if AA.approval_expired(device):
        session.clear()
        return jsonify({"status": "expired"})
    return jsonify({"status": "pending"})


def _device_for_link(link):
    device = AdminDevice.query.filter_by(approve_hash=AA.token_hash(link)).first() if link else None
    if not device or device.status != "pending" or AA.approval_expired(device):
        return None
    return device


@login_bp.route("/admin/device/review/<link>", methods=["GET", "POST"])
def admin_device_review(link):
    """The page the approval e-mail opens. Approving is a button press (POST), never the link itself, so an e-mail
    scanner that opens links cannot approve anything."""
    device = _device_for_link(link)
    if not device:
        return render_template("admin_device.html", mode="invalid"), 410
    if request.method == "GET":
        return render_template("admin_device.html", mode="review", device=device, minutes=AA.APPROVAL_LINK_MINUTES)
    action = request.form.get("action")
    now = datetime.utcnow()
    device.approve_hash, device.approve_expires = None, None
    if action == "approve":
        device.status, device.approved_at, device.password_print = "approved", now, admin_password_print()
        db.session.commit()
        return render_template("admin_device.html", mode="approved", device=device)
    device.status = "denied"
    db.session.commit()
    return render_template("admin_device.html", mode="denied", device=device)


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE OAUTH 2.0
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/auth/google")
def auth_google():
    if not has_google_oauth:
        return redirect("/login?error=google_not_configured")
    redirect_uri = url_for("login_bp.auth_google_callback", _external=True)
    google_client = getattr(oauth, 'google', None) or oauth.create_client('google')
    # prompt=select_account makes Google always show its account chooser (every Google account signed in on this
    # device/browser, plus "Use another account") instead of silently reusing the last one.
    return google_client.authorize_redirect(redirect_uri, prompt="select_account")


@login_bp.route("/auth/google/callback")
def auth_google_callback():
    if not has_google_oauth:
        return redirect("/login")
    google_client = getattr(oauth, 'google', None) or oauth.create_client('google')
    token = google_client.authorize_access_token()
    user_info = token.get("userinfo")

    if not user_info:
        return redirect("/login")

    google_id = user_info["sub"]
    email = (user_info["email"] or "").strip().lower()
    name = user_info.get("name", email.split("@")[0])

    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id = google_id
            user.auth_provider = "google"
            user.email_verified = True
            db.session.commit()

    if user:
        session.clear()
        session["user_id"] = user.id
        session["user_name"] = user.full_name
        session["user_email"] = user.email
        start_signed_in_session(True)
        if not profile_is_complete(user):
            session["pending_google_email"] = user.email
            return redirect("/register?google=1")
        return redirect("/dashboard")
    else:
        session["pending_google_email"] = email
        session["pending_google_name"] = name
        session["pending_google_id"] = google_id
        return redirect("/register?google=1")


# ══════════════════════════════════════════════════════════════════════════════
# FORGOT PASSWORD & RECOVERY
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not is_valid_email(email):
            return render_template("forgot_password.html", error="Please enter a valid email address.")
        if _otp_send_blocked():
            return render_template("forgot_password.html", error="Too many requests. Please try again in a few minutes.")

        # The answer is identical whether or not the account exists, so this form cannot be used to find out
        # which emails are registered. A code is only generated and emailed for real accounts.
        if User.query.filter_by(email=email).first():
            code, _reason = issue_otp("reset", email)
            if code and not send_otp_email(email, code):
                return render_template("forgot_password.html", error="Failed to send the code. Please try again.")
        session["fp_email"] = email
        return redirect("/forgot-password/verify")

    return render_template("forgot_password.html", error=None)


@login_bp.route("/forgot-password/verify", methods=["GET", "POST"])
def forgot_password_verify():
    email = session.get("fp_email")
    if not email:
        return redirect("/forgot-password")

    if request.method == "GET":
        return render_template("verify_otp.html", error=None, email=email, next_step="reset_password")

    status = check_otp("reset", email, request.form.get("otp"))
    if status == "ok":
        session["fp_verified_email"] = email
        session.pop("fp_email", None)
        return redirect("/forgot-password/reset")

    return render_template("verify_otp.html", error=OTP_MESSAGES[status], email=email, next_step="reset_password")


@login_bp.route("/forgot-password/reset", methods=["GET", "POST"])
def forgot_password_reset():
    email = session.get("fp_verified_email")
    if not email:
        return redirect("/forgot-password")

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        problem = password_problem(password, email)
        if problem:
            return render_template("set_password.html", error=problem, email=email, is_reset=True)
        if password != confirm:
            return render_template("set_password.html", error="Passwords do not match.", email=email, is_reset=True)

        user = User.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(password)
            db.session.commit()
        session.pop("fp_verified_email", None)
        return redirect("/login?msg=password_reset")

    return render_template("set_password.html", error=None, email=email, is_reset=True)


# ══════════════════════════════════════════════════════════════════════════════
# DIRECT OTP LOGIN
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/auth/otp/send", methods=["GET", "POST"])
def send_otp():
    if request.method == "GET":
        return render_template("send_otp.html", error=None)

    email = (request.form.get("email") or "").strip().lower()
    if not is_valid_email(email):
        return render_template("send_otp.html", error="Please enter a valid email address.")
    if _otp_send_blocked():
        return render_template("send_otp.html", error="Too many requests. Please try again in a few minutes.")

    code, reason = issue_otp("login", email)
    if reason == "limit":
        return render_template("send_otp.html", error="Too many codes requested for this email. Please try again later.")
    # reason == "cooldown": a code was sent moments ago and is still valid, so just continue to the verify page.
    if code and not send_otp_email(email, code):
        return render_template("send_otp.html", error="Failed to send the code. Please try again or use password login.")

    session["otp_email"] = email
    return redirect("/auth/otp/verify")


@login_bp.route("/auth/otp/verify", methods=["GET", "POST"])
def verify_otp():
    email = session.get("otp_email")
    if not email:
        return redirect("/auth/otp/send")

    if request.method == "GET":
        return render_template("verify_otp.html", error=None, email=email)

    status = check_otp("login", email, request.form.get("otp"))
    if status != "ok":
        return render_template("verify_otp.html", error=OTP_MESSAGES[status], email=email)

    user = User.query.filter_by(email=email).first()
    if not user:
        # Accounts created through an email code are only created once the mailbox has been proven.
        user = User(full_name=email.split("@")[0].capitalize(), email=email,
                    password=generate_password_hash(os.urandom(24).hex()), auth_provider="otp", email_verified=True)
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[OTP] Error creating account: {e}")
            return render_template("verify_otp.html", error="Something went wrong. Please try again.", email=email)

    session.clear()
    session["user_id"] = user.id
    session["user_name"] = user.full_name
    session["user_email"] = user.email
    if not profile_is_complete(user):
        return redirect("/register")
    return redirect("/dashboard")


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRATION & SIGNUP FLOWS
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not is_valid_email(email):
            return render_template("signup.html", error="Please enter a valid email address.", has_google_oauth=has_google_oauth)

        if User.query.filter_by(email=email).first():
            return render_template("signup.html", error="An account with this email already exists. Please login.", has_google_oauth=has_google_oauth)

        if _otp_send_blocked():
            return render_template("signup.html", error="Too many requests. Please try again in a few minutes.", has_google_oauth=has_google_oauth)

        code, reason = issue_otp("signup", email)
        if reason == "limit":
            return render_template("signup.html", error="Too many codes requested for this email. Please try again later.", has_google_oauth=has_google_oauth)
        if code and not send_otp_email(email, code):
            return render_template("signup.html", error="Failed to send the code. Please try again.", has_google_oauth=has_google_oauth)

        session["pending_signup_email"] = email
        return redirect("/auth/register/verify-otp")

    return render_template("signup.html", has_google_oauth=has_google_oauth, error=None)


@login_bp.route("/auth/register/verify-otp", methods=["GET", "POST"])
def verify_register_otp():
    email = session.get("pending_signup_email")
    if not email:
        if session.get("email_otp_verified"):
            return redirect("/signup/set-password")
        return redirect("/signup")

    if request.method == "GET":
        return render_template("verify_otp.html", error=None, email=email, next_step="set_password")

    status = check_otp("signup", email, request.form.get("otp"))
    if status == "ok":
        session["email_otp_verified"] = email
        return redirect("/signup/set-password")

    return render_template("verify_otp.html", error=OTP_MESSAGES[status], email=email, next_step="set_password")


@login_bp.route("/signup/set-password", methods=["GET", "POST"])
def signup_set_password():
    email = session.get("email_otp_verified")          # only an email whose code was entered correctly
    if not email:
        return redirect("/signup")

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        problem = password_problem(password, email)
        if problem:
            return render_template("set_password.html", error=problem, email=email)
        if password != confirm:
            return render_template("set_password.html", error="Passwords do not match.", email=email)

        session["verified_signup_email"] = email
        session["verified_signup_password"] = generate_password_hash(password)
        return redirect("/register")

    return render_template("set_password.html", error=None, email=email)


@login_bp.route("/register", methods=["GET", "POST"])
def register():
    is_google = request.args.get("google") == "1"

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        gender = request.form.get("gender")
        education = request.form.get("education")
        course = request.form.get("course")
        semester = request.form.get("semester")
        user_type = request.form.get("user_type", "student")
        github_url = request.form.get("github_url", "").strip() or None
        linkedin_url = request.form.get("linkedin_url", "").strip() or None
        skills = request.form.get("skills", "").strip() or None
        years_of_experience = request.form.get("years_of_experience", "").strip() or None
        current_designation = request.form.get("current_designation", "").strip() or None

        email = session.get("pending_google_email") or session.get("verified_signup_email")
        password = session.get("verified_signup_password")

        def render_register_error(error_msg):
            return render_template("register.html", error=error_msg,
                                   is_google=is_google, prefill_name=full_name, prefill_email=email or "",
                                   prefill_gender=gender, prefill_education=education, prefill_course=course,
                                   prefill_semester=semester, prefill_user_type=user_type,
                                   prefill_github_url=github_url, prefill_linkedin_url=linkedin_url,
                                   prefill_skills=skills, prefill_years_of_experience=years_of_experience,
                                   prefill_current_designation=current_designation)

        if not full_name:
            return render_register_error("Please fill in your full name.")

        if not gender:
            return render_register_error("Please select your gender.")

        existing_name = User.query.filter(User.full_name.ilike(full_name)).first()
        if existing_name and ("user_id" not in session or session.get("user_id") != existing_name.id):
            return render_register_error("This name is already taken. Please use a different name.")

        if user_type == "student":
            if not education:
                return render_register_error("Please select your education level.")
            if not course:
                return render_register_error("Please enter your course/branch.")
            if not semester:
                return render_register_error("Please enter your semester/year.")
        elif user_type == "professional":
            if not current_designation:
                return render_register_error("Please enter your current designation.")
            if not years_of_experience:
                return render_register_error("Please enter your years of experience.")

        # Logged-in user updating their profile
        if "user_id" in session:
            user = db.session.get(User, session["user_id"])
            if user:
                was_complete = profile_is_complete(user)
                user.full_name = full_name
                user.gender = gender
                user.education = education
                user.course = course
                user.semester = semester
                user.user_type = user_type
                user.github_url = github_url
                user.linkedin_url = linkedin_url
                user.skills = skills
                user.years_of_experience = years_of_experience
                user.current_designation = current_designation
                db.session.commit()
                session["user_name"] = user.full_name
                if not was_complete:
                    send_welcome_once(user, via_google=(user.auth_provider == "google"))
                return redirect("/dashboard")

        # Google OAuth new user
        if session.get("pending_google_email"):
            g_email = session.pop("pending_google_email")
            google_id = session.pop("pending_google_id", None)
            session.pop("pending_google_name", None)
            new_user = User(
                full_name=full_name, email=g_email, password=None,
                gender=gender, education=education, course=course, semester=semester,
                auth_provider="google", google_id=google_id, email_verified=True,
                user_type=user_type, github_url=github_url, linkedin_url=linkedin_url,
                skills=skills, years_of_experience=years_of_experience,
                current_designation=current_designation
            )
            db.session.add(new_user)
            db.session.commit()
            session["user_id"] = new_user.id
            session["user_name"] = new_user.full_name
            session["user_email"] = new_user.email
            send_welcome_once(new_user, via_google=True)
            return redirect("/dashboard")

        # Local signup (email verified via OTP, password already set)
        if session.get("verified_signup_email"):
            new_user = User(
                full_name=full_name, email=email, password=password,
                gender=gender, education=education, course=course, semester=semester,
                auth_provider="local", email_verified=True,
                user_type=user_type, github_url=github_url, linkedin_url=linkedin_url,
                skills=skills, years_of_experience=years_of_experience,
                current_designation=current_designation
            )
            db.session.add(new_user)
            db.session.commit()
            session.pop("verified_signup_email", None)
            session.pop("verified_signup_password", None)
            session["user_id"] = new_user.id
            session["user_name"] = new_user.full_name
            session["user_email"] = new_user.email
            send_welcome_once(new_user)
            return redirect("/dashboard")

        return redirect("/login")

    # GET
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        prefill_name = user.full_name if user else ""
        prefill_email = (user.email if user else "") or session.get("pending_google_email", "")
        if user and user.auth_provider == "google":
            is_google = True
    else:
        prefill_name = session.get("pending_google_name", "")
        prefill_email = session.get("pending_google_email") or session.get("verified_signup_email", "")
        if not prefill_email:
            return redirect("/login")

    return render_template("register.html", is_google=is_google,
                           prefill_name=prefill_name, prefill_email=prefill_email, error=None)


@login_bp.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if session.get("is_admin"):
        return redirect("/admin")
    if "user_id" not in session:
        return redirect("/login")

    user = db.session.get(User, session["user_id"])

    if not user:
        session.clear()
        return redirect("/login")

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if not full_name:
            return render_template("edit_profile.html", user=user, error="Full name cannot be empty.")
        name_taken = User.query.filter(User.full_name.ilike(full_name), User.id != user.id).first()
        if name_taken:
            return render_template("edit_profile.html", user=user, error="This name is already taken. Please use a different name.")

        user.full_name = full_name
        user.gender = request.form.get("gender")
        user.education = request.form.get("education")
        user.course = request.form.get("course")
        user.semester = request.form.get("semester")
        user.user_type = request.form.get("user_type", "student")
        user.github_url = request.form.get("github_url", "").strip() or None
        user.linkedin_url = request.form.get("linkedin_url", "").strip() or None
        user.skills = request.form.get("skills", "").strip() or None
        user.years_of_experience = request.form.get("years_of_experience", "").strip() or None
        user.current_designation = request.form.get("current_designation", "").strip() or None
        db.session.commit()
        session["user_name"] = user.full_name
        return render_template("edit_profile.html", user=user, success="Profile updated successfully.")

    return render_template("edit_profile.html", user=user)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION LOGOUT
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
