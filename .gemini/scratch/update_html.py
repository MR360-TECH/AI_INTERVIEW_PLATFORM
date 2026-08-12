import re

# 1. Update login.html
with open("templates/login.html", "r", encoding="utf-8") as f:
    content = f.read()

login_form = '''
                    <div class="mb-3">
                        <a href="/auth/google" class="btn btn-google w-100 d-flex align-items-center justify-content-center gap-2 py-2">
                            <img src="https://www.google.com/favicon.ico" width="20" height="20" alt="Google">
                            Sign in with Google
                        </a>
                    </div>

                    <div class="divider">or login with credentials</div>

                    <form method="POST" id="loginForm" action="/login">
                        <div class="mb-3">
                            <label class="form-label" for="email">Email</label>
                            <input type="email" name="email" id="email" class="form-control" required placeholder="your@email.com" value="{{ prefill_email or '' }}" {% if show_password %}readonly{% endif %}>
                        </div>
                        
                        {% if show_password %}
                        <div class="mb-3">
                            <label class="form-label" for="password">Password</label>
                            <input type="password" name="password" id="password" class="form-control" required placeholder="Enter your password">
                        </div>
                        {% endif %}

                        <button type="submit" class="btn btn-login w-100 text-white mb-2">
                            Continue
                        </button>
                    </form>

                    <p class="text-center mt-4 mb-0 text-muted" style="font-size:0.9rem;">
                        Don't have an account? No problem! Just enter your email and we'll help you set one up.
                    </p>
'''

content = re.sub(r'<div class="mb-3">\s*<a href="/auth/otp/send".*?Sign in with Gmail \(OTP Verification\)\s*</a>\s*</div>\s*<div class="divider">or login with credentials</div>\s*<form method="POST" id="loginForm">.*?</form>\s*<p class="text-center mt-4 mb-0 text-muted".*?</p>', login_form, content, flags=re.DOTALL)
content = re.sub(r'<div class="recommend-note">.*?</div>', '', content, flags=re.DOTALL)

with open("templates/login.html", "w", encoding="utf-8") as f:
    f.write(content)

# 2. Update register.html
with open("templates/register.html", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'\{% elif is_guest %\}.*?\{% endif %\}', '{% endif %}', content, flags=re.DOTALL)
content = re.sub(r'<!-- Password: only for standalone signup -->.*?\{% if not prefill_email %\}.*?\{% endif %\}', '', content, flags=re.DOTALL)

with open("templates/register.html", "w", encoding="utf-8") as f:
    f.write(content)

# 3. Update admin templates
for tpl in ["templates/admin.html", "templates/admin_user_detail.html", "templates/admin_interview_detail.html"]:
    with open(tpl, "r", encoding="utf-8") as f:
        content = f.read()
    
    auth_badge_regex = r'\{% if (user|candidate)\.auth_provider == "google" or (user|candidate)\.auth_provider == "otp" %\}[\s\S]*?\{% endif %\}'
    
    new_badge = '''{% if \\1.auth_provider == "google" %}
                                <span class="auth-badge google">
                                    <svg class="google-g-icon" viewBox="0 0 48 48">
                                        <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12s5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24s8.955,20,20,20s20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
                                        <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
                                        <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
                                        <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
                                    </svg>
                                    Google (G)
                                </span>
                                {% elif \\1.auth_provider == "local" and \\1.email_verified %}
                                <span class="auth-badge" style="background:#f0fdf4;color:#16a34a;border:1.5px solid #bbf7d0;">
                                    <i class="bi bi-envelope-check-fill"></i> Verified Local (V)
                                </span>
                                {% elif \\1.auth_provider == "local" %}
                                <span class="auth-badge guest"><i class="bi bi-person-fill"></i> Local</span>
                                {% endif %}'''
    
    content = re.sub(auth_badge_regex, new_badge, content)
    
    with open(tpl, "w", encoding="utf-8") as f:
        f.write(content)

print("Updated HTML templates")
