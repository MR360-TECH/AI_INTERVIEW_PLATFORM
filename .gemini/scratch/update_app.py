import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add email_verified to User
content = content.replace(
    "    auth_provider = db.Column(db.String(20), default='local')\n    google_id = db.Column(db.String(100), unique=True, nullable=True)",
    "    auth_provider = db.Column(db.String(20), default='local')\n    email_verified = db.Column(db.Boolean, default=False)\n    google_id = db.Column(db.String(100), unique=True, nullable=True)"
)

# 2. Replace auth_google_callback
auth_google_callback_new = '''@app.route("/auth/google/callback")
def auth_google_callback():
    if not has_google_oauth:
        return redirect("/login")
    token = google.authorize_access_token()
    user_info = token.get("userinfo")

    if not user_info:
        return redirect("/login")

    google_id = user_info["sub"]
    email = user_info["email"]
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
        if not profile_is_complete(user):
            return redirect("/register")
        return redirect("/dashboard")
    else:
        session["pending_google_email"] = email
        session["pending_google_name"] = name
        session["pending_google_id"] = google_id
        return redirect("/register?google=1")'''

content = re.sub(r'@app\.route\("/auth/google/callback"\).*?def auth_google_callback\(\):.*?return redirect\("/register\?google=1"\)', auth_google_callback_new, content, flags=re.DOTALL)

# 3. Replace login
login_new = '''@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not is_valid_email(email):
            return render_template("login.html", error="Please enter a valid email address.", has_google_oauth=has_google_oauth)

        if ADMIN_EMAIL and email == ADMIN_EMAIL.strip().lower() and password == ADMIN_PASSWORD.strip():
            session.clear()
            session["is_admin"] = True
            session["user_name"] = "Admin"
            return redirect("/admin")

        user = User.query.filter_by(email=email).first()

        if password:
            if user and user.password and check_password_hash(user.password, password):
                session.clear()
                session["user_id"] = user.id
                session["user_name"] = user.full_name
                session["user_email"] = user.email
                return redirect("/dashboard")
            else:
                return render_template("login.html", error="Incorrect email or password", show_password=True, prefill_email=email, has_google_oauth=has_google_oauth)

        if user:
            return render_template("login.html", show_password=True, prefill_email=email, has_google_oauth=has_google_oauth)
        else:
            session["pending_register_email"] = email
            return redirect("/register")

    error_msg = None
    err_code = request.args.get("error")
    if err_code == "file_too_large":
        error_msg = "Uploaded file is too large. The maximum size limit is 10MB."
    elif err_code == "google_not_configured":
        error_msg = "Google Sign-in is not configured on this server."
    return render_template("login.html", error=error_msg, has_google_oauth=has_google_oauth)'''

content = re.sub(r'@app\.route\("/login", methods=\["GET", "POST"\]\).*?def login\(\):.*?return render_template\("login\.html", error=error_msg, has_google_oauth=has_google_oauth\)', login_new, content, flags=re.DOTALL)

# 4. Replace register and remove guest_signup
register_new = '''@app.route("/register", methods=["GET", "POST"])
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

        if not full_name:
            return render_template("register.html", error="Full name is required.",
                                   is_google=is_google, prefill_name="", prefill_email="")

        if "user_id" in session:
            user = db.session.get(User, session["user_id"])
            if user:
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
                return redirect("/dashboard")

        if session.get("pending_google_email"):
            email = session.pop("pending_google_email")
            google_id = session.pop("pending_google_id", None)
            session.pop("pending_google_name", None)
            new_user = User(
                full_name=full_name, email=email, password=None,
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
            return redirect("/dashboard")

        email = session.get("pending_register_email") or request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or "@" not in email:
            return render_template("register.html", error="Please enter a valid email address.",
                                   is_google=False, prefill_name=full_name, prefill_email=email)
        
        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="An account with this email already exists. Please login.",
                                   is_google=False, prefill_name=full_name, prefill_email=email)

        otp = str(random.randint(100000, 999999))
        session["reg_otp"] = otp
        session["reg_pending_user"] = {
            "full_name": full_name, "email": email, "password": generate_password_hash(password) if password else None,
            "gender": gender, "education": education, "course": course, "semester": semester,
            "user_type": user_type, "github_url": github_url, "linkedin_url": linkedin_url,
            "skills": skills, "years_of_experience": years_of_experience, "current_designation": current_designation
        }
        
        if send_otp_email(email, otp):
            return redirect("/auth/register/verify-otp")
        else:
            return render_template("register.html", error="Failed to send OTP email. Please try again.",
                                   is_google=False, prefill_name=full_name, prefill_email=email)

    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        prefill_name = user.full_name if user else ""
        prefill_email = user.email if user else ""
    else:
        prefill_name = session.get("pending_google_name", "")
        prefill_email = session.get("pending_google_email") or session.get("pending_register_email", "")

    return render_template("register.html", is_google=is_google,
                           prefill_name=prefill_name, prefill_email=prefill_email, error=None)'''

content = re.sub(r'@app\.route\("/register"\).*?def register\(\):.*?return render_template\("register\.html", is_google=is_google, is_guest=is_guest,\s*prefill_name=prefill_name, prefill_email=prefill_email, error=None\).*?@app\.route\("/guest-signup", methods=\\["POST"\\]\).*?def guest_signup\(\):.*?return redirect\("/register\?guest=1"\)', register_new, content, flags=re.DOTALL)

# 5. Replace send_otp / verify_otp
otp_new = '''@app.route("/auth/register/verify-otp", methods=["GET", "POST"])
def verify_register_otp():
    if "reg_otp" not in session or "reg_pending_user" not in session:
        return redirect("/register")

    user_data = session["reg_pending_user"]
    if request.method == "GET":
        return render_template("verify_otp.html", error=None, email=user_data.get("email", ""))

    entered = (request.form.get("otp") or "").strip()
    if entered == session.get("reg_otp"):
        session.pop("reg_otp", None)
        
        new_user = User(
            full_name=user_data.get("full_name"),
            email=user_data.get("email"),
            password=user_data.get("password"),
            gender=user_data.get("gender"),
            education=user_data.get("education"),
            course=user_data.get("course"),
            semester=user_data.get("semester"),
            auth_provider="local",
            email_verified=True,
            user_type=user_data.get("user_type"),
            github_url=user_data.get("github_url"),
            linkedin_url=user_data.get("linkedin_url"),
            skills=user_data.get("skills"),
            years_of_experience=user_data.get("years_of_experience"),
            current_designation=user_data.get("current_designation")
        )
        db.session.add(new_user)
        db.session.commit()
        session.pop("reg_pending_user", None)
        
        session["user_id"] = new_user.id
        session["user_name"] = new_user.full_name
        session["user_email"] = new_user.email
        return redirect("/dashboard")
        
    return render_template("verify_otp.html", error="Invalid OTP. Please try again.", email=user_data.get("email", ""))'''

content = re.sub(r'@app\.route\("/auth/otp/send", methods=\\["GET", "POST"\\]\).*?def send_otp\(\):.*?@app\.route\("/auth/otp/verify", methods=\\["GET", "POST"\\]\).*?def verify_otp\(\):.*?return render_template\("verify_otp\.html", error="Invalid OTP\. Please try again\.", email=session\.get\("otp_email", ""\)\)', otp_new, content, flags=re.DOTALL)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated app.py")
