import os
import random
from flask import Blueprint, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db, oauth, ADMIN_EMAIL, ADMIN_PASSWORD, has_google_oauth
from MODULES.LAYER_2_DATA_PERSISTENCE.models import User, is_valid_email, profile_is_complete
from MODULES.LAYER_3_BUSINESS_SERVICES.mailer import send_otp_email
from MODULES.LAYER_3_BUSINESS_SERVICES.feedback_email import queue_welcome_email

login_bp = Blueprint('login_bp', __name__)
register_bp = login_bp  # Alias for backward compatibility


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


# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD & CREDENTIALS LOGIN
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not is_valid_email(email):
            return render_template("login.html", error="Please enter a valid email address.", prefill_email=email, has_google_oauth=has_google_oauth)

        if not password:
            return render_template("login.html", error="Please enter your password.", prefill_email=email, has_google_oauth=has_google_oauth)

        # Admin check
        if ADMIN_EMAIL and email == ADMIN_EMAIL.strip().lower():
            if ADMIN_PASSWORD and password == ADMIN_PASSWORD.strip():
                session.clear()
                session["is_admin"] = True
                session["user_name"] = "Admin"
                return redirect("/admin")
            else:
                return render_template("login.html", error="Wrong password. Please check your password and try again.", prefill_email=email, has_google_oauth=has_google_oauth)

        user = User.query.filter_by(email=email).first()

        if not user:
            return render_template("login.html", show_signup_prompt=True, prefill_email=email, has_google_oauth=has_google_oauth)

        # Check if user registered via Google OAuth without a password
        if user.auth_provider == "google" and not user.password:
            return render_template("login.html", error="This account was registered with Google. Please click 'Continue with Google' above.", prefill_email=email, has_google_oauth=has_google_oauth)

        if user.password and check_password_hash(user.password, password):
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.full_name
            session["user_email"] = user.email
            session["is_admin"] = False
            if not profile_is_complete(user):
                return redirect("/register")
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Wrong password. Please check your password and try again.", prefill_email=email, has_google_oauth=has_google_oauth)

    error_msg = None
    err_code = request.args.get("error")
    if err_code == "file_too_large":
        error_msg = "Uploaded file is too large. The maximum size limit is 10MB."
    elif err_code == "google_not_configured":
        error_msg = "Google Sign-in is not configured on this server."
    return render_template("login.html", error=error_msg, has_google_oauth=has_google_oauth)


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE OAUTH 2.0
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/auth/google")
def auth_google():
    if not has_google_oauth:
        return redirect("/login?error=google_not_configured")
    redirect_uri = url_for("login_bp.auth_google_callback", _external=True)
    google_client = getattr(oauth, 'google', None) or oauth.create_client('google')
    return google_client.authorize_redirect(redirect_uri)


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

        if not email or "@" not in email:
            return render_template("forgot_password.html", error="Please enter a valid email address.")

        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template("forgot_password.html", error="No account found with this email address.")

        otp = str(random.randint(100000, 999999))
        session["fp_otp"] = otp
        session["fp_email"] = email

        if send_otp_email(email, otp):
            return redirect("/forgot-password/verify")
        else:
            return render_template("forgot_password.html", error="Failed to send OTP. Please try again.")

    return render_template("forgot_password.html", error=None)


@login_bp.route("/forgot-password/verify", methods=["GET", "POST"])
def forgot_password_verify():
    if "fp_otp" not in session or "fp_email" not in session:
        return redirect("/forgot-password")

    email = session["fp_email"]
    if request.method == "GET":
        return render_template("verify_otp.html", error=None, email=email, next_step="reset_password")

    entered = (request.form.get("otp") or "").strip()
    if entered == session.get("fp_otp"):
        session.pop("fp_otp", None)
        session["fp_verified_email"] = email
        session.pop("fp_email", None)
        return redirect("/forgot-password/reset")

    return render_template("verify_otp.html", error="Invalid OTP. Please try again.", email=email, next_step="reset_password")


@login_bp.route("/forgot-password/reset", methods=["GET", "POST"])
def forgot_password_reset():
    email = session.get("fp_verified_email")
    if not email:
        return redirect("/forgot-password")

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not password or len(password) < 6:
            return render_template("set_password.html", error="Password must be at least 6 characters.", email=email, is_reset=True)
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

    try:
        email = (request.form.get("email") or "").strip().lower()
        if not email or "@" not in email:
            return render_template("send_otp.html", error="Please enter a valid email address.")

        user = User.query.filter_by(email=email).first()
        if not user:
            user_name = email.split("@")[0].capitalize()
            user = User(
                full_name=user_name,
                email=email,
                password=generate_password_hash(os.urandom(24).hex()),
                auth_provider="otp",
                email_verified=True
            )
            db.session.add(user)
            try:
                db.session.commit()
                print(f"[OTP] Auto-created user account for {email}")
            except Exception as e:
                db.session.rollback()
                print(f"[OTP] Error auto-creating user account: {e}")

        otp = str(random.randint(100000, 999999))
        session["otp_code"] = otp
        session["otp_email"] = email

        if send_otp_email(email, otp):
            return redirect("/auth/otp/verify")
        else:
            return render_template("send_otp.html", error="Failed to send OTP email. Please try again or use password login.")

    except Exception as e:
        print(f"[send_otp] Unexpected error: {e}")
        db.session.rollback()
        return render_template("send_otp.html", error="Something went wrong. Please try again.")


@login_bp.route("/auth/otp/verify", methods=["GET", "POST"])
def verify_otp():
    if "otp_code" not in session:
        return redirect("/auth/otp/send")

    if request.method == "GET":
        return render_template("verify_otp.html", error=None, email=session.get("otp_email", ""))

    entered = (request.form.get("otp") or "").strip()
    if entered == session.get("otp_code"):
        email = session.pop("otp_email", None)
        session.pop("otp_code", None)
        user = User.query.filter_by(email=email).first()
        if user:
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.full_name
            session["user_email"] = user.email
            if not profile_is_complete(user):
                return redirect("/register")
            return redirect("/dashboard")
    return render_template("verify_otp.html", error="Invalid OTP. Please try again.", email=session.get("otp_email", ""))


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRATION & SIGNUP FLOWS
# ══════════════════════════════════════════════════════════════════════════════

@login_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email or "@" not in email:
            return render_template("signup.html", error="Please enter a valid email address.", has_google_oauth=has_google_oauth)

        if User.query.filter_by(email=email).first():
            return render_template("signup.html", error="An account with this email already exists. Please login.", has_google_oauth=has_google_oauth)

        otp = str(random.randint(100000, 999999))
        session["reg_otp"] = otp
        session["pending_signup_email"] = email

        if send_otp_email(email, otp):
            return redirect("/auth/register/verify-otp")
        else:
            return render_template("signup.html", error="Failed to send OTP email. Please try again.", has_google_oauth=has_google_oauth)

    return render_template("signup.html", has_google_oauth=has_google_oauth, error=None)


@login_bp.route("/auth/register/verify-otp", methods=["GET", "POST"])
def verify_register_otp():
    email = session.get("pending_signup_email") or session.get("email_otp_verified")
    if not email or "reg_otp" not in session:
        if session.get("email_otp_verified"):
            return redirect("/signup/set-password")
        return redirect("/signup")

    if request.method == "GET":
        return render_template("verify_otp.html", error=None, email=email, next_step="set_password")

    entered = (request.form.get("otp") or "").strip()
    if entered == session.get("reg_otp"):
        session.pop("reg_otp", None)
        session["email_otp_verified"] = email
        return redirect("/signup/set-password")

    return render_template("verify_otp.html", error="Invalid OTP. Please try again.", email=email, next_step="set_password")


@login_bp.route("/signup/set-password", methods=["GET", "POST"])
def signup_set_password():
    email = session.get("email_otp_verified") or session.get("pending_signup_email")
    if not email:
        return redirect("/signup")

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not password or len(password) < 6:
            return render_template("set_password.html", error="Password must be at least 6 characters.", email=email)
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
