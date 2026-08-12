import re

# 1. Update app.py
with open("app.py", "r", encoding="utf-8") as f:
    app_code = f.read()

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

        email = session.get("pending_google_email") or session.get("pending_register_email") or request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip() if not session.get("pending_google_email") else None
        
        def render_register_error(error_msg):
            return render_template("register.html", error=error_msg,
                                   is_google=is_google, prefill_name=full_name, prefill_email=email,
                                   prefill_gender=gender, prefill_education=education, prefill_course=course,
                                   prefill_semester=semester, prefill_user_type=user_type, prefill_github_url=github_url,
                                   prefill_linkedin_url=linkedin_url, prefill_skills=skills,
                                   prefill_years_of_experience=years_of_experience, prefill_current_designation=current_designation)

        if not full_name:
            return render_register_error("Full name is required.")

        # Check if full_name is unique
        existing_name = User.query.filter(User.full_name.ilike(full_name)).first()
        if existing_name and ("user_id" not in session or session["user_id"] != existing_name.id):
            return render_register_error("This name is already taken. Please use a different name.")

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

        if not email or "@" not in email:
            return render_register_error("Please enter a valid email address.")
        
        if User.query.filter_by(email=email).first():
            return render_register_error("An account with this email already exists. Please login.")

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
            return render_register_error("Failed to send OTP email. Please try again.")

    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        prefill_name = user.full_name if user else ""
        prefill_email = user.email if user else ""
    else:
        prefill_name = session.get("pending_google_name", "")
        prefill_email = session.get("pending_google_email") or session.get("pending_register_email", "")

    return render_template("register.html", is_google=is_google,
                           prefill_name=prefill_name, prefill_email=prefill_email, error=None)'''

app_code = re.sub(r'@app\.route\("/register", methods=\\["GET", "POST"\\]\).*?def register\(\):.*?return render_template\("register\.html", is_google=is_google,\s*prefill_name=prefill_name, prefill_email=prefill_email, error=None\)', register_new, app_code, flags=re.DOTALL)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_code)

# 2. Update register.html
with open("templates/register.html", "r", encoding="utf-8") as f:
    html = f.read()

# Make fields populate from prefill
# Gender
html = re.sub(r'<option value="Male">Male</option>', r'<option value="Male" {% if prefill_gender == "Male" %}selected{% endif %}>Male</option>', html)
html = re.sub(r'<option value="Female">Female</option>', r'<option value="Female" {% if prefill_gender == "Female" %}selected{% endif %}>Female</option>', html)
html = re.sub(r'<option value="Other">Other / Prefer not to say</option>', r'<option value="Other" {% if prefill_gender == "Other" %}selected{% endif %}>Other / Prefer not to say</option>', html)

# Education
html = re.sub(r'value="School" id="edu1"', r'value="School" id="edu1" {% if prefill_education == "School" %}checked{% endif %}', html)
html = re.sub(r'value="PU/12th" id="edu2"', r'value="PU/12th" id="edu2" {% if prefill_education == "PU/12th" %}checked{% endif %}', html)
html = re.sub(r'value="Degree" id="edu3"', r'value="Degree" id="edu3" {% if prefill_education == "Degree" %}checked{% endif %}', html)
html = re.sub(r'value="Post Graduate" id="edu4"', r'value="Post Graduate" id="edu4" {% if prefill_education == "Post Graduate" %}checked{% endif %}', html)

# Inputs
html = re.sub(r'name="course" class="form-control"([\s\S]*?)placeholder="e.g. BCA, B.Tech CSE">', r'name="course" class="form-control"\1placeholder="e.g. BCA, B.Tech CSE" value="{{ prefill_course or \'\' }}">', html)
html = re.sub(r'name="semester" class="form-control"([\s\S]*?)placeholder="e.g. 6th Sem, 3rd Year">', r'name="semester" class="form-control"\1placeholder="e.g. 6th Sem, 3rd Year" value="{{ prefill_semester or \'\' }}">', html)
html = re.sub(r'name="current_designation" class="form-control"([\s\S]*?)placeholder="e.g. Software Engineer, Product Manager">', r'name="current_designation" class="form-control"\1placeholder="e.g. Software Engineer, Product Manager" value="{{ prefill_current_designation or \'\' }}">', html)
html = re.sub(r'name="years_of_experience" class="form-control"([\s\S]*?)step="0.5">', r'name="years_of_experience" class="form-control"\1step="0.5" value="{{ prefill_years_of_experience or \'\' }}">', html)
html = re.sub(r'name="skills" class="form-control"([\s\S]*?)placeholder="e.g. Python, React, Machine Learning \(comma separated\)">', r'name="skills" class="form-control"\1placeholder="e.g. Python, React, Machine Learning (comma separated)" value="{{ prefill_skills or \'\' }}">', html)
html = re.sub(r'name="github_url" class="form-control"([\s\S]*?)placeholder="https://github.com/username">', r'name="github_url" class="form-control"\1placeholder="https://github.com/username" value="{{ prefill_github_url or \'\' }}">', html)
html = re.sub(r'name="linkedin_url" class="form-control"([\s\S]*?)placeholder="https://linkedin.com/in/username">', r'name="linkedin_url" class="form-control"\1placeholder="https://linkedin.com/in/username" value="{{ prefill_linkedin_url or \'\' }}">', html)

# User type toggle script
script_addition = '''
    // Apply prefilled user type
    {% if prefill_user_type == "professional" %}
        setType("professional");
    {% else %}
        setType("student");
    {% endif %}
'''
html = re.sub(r'function setType\(type\) \{', r'function setType(type) {', html) # ensure match
html = html.replace('</script>\n</body>', script_addition + '\n</script>\n</body>')

with open("templates/register.html", "w", encoding="utf-8") as f:
    f.write(html)
