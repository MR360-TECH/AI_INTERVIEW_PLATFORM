import os
import json
import smtplib
import threading
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _otp_html_body(otp):
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px; background: #080e1e; color: #e2e8f0; border-radius: 16px; border: 1px solid rgba(0, 255, 255, 0.25);">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="background: rgba(0, 255, 255, 0.12); color: #00ffff; border: 1px solid rgba(0, 255, 255, 0.3); border-radius: 100px; padding: 6px 18px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;">
          Platform Access Code
        </span>
      </div>
      <h2 style="color: #ffffff; font-size: 22px; font-weight: 800; margin-bottom: 8px; text-align: center;">
        Your Temporary Login Code
      </h2>
      <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin-bottom: 24px; text-align: center;">
        Hi there, <br><br>
        You recently requested to access the AI Assessment Studio. Please use the secure code below to complete your login securely.
      </p>
      <div style="background: rgba(0, 255, 255, 0.06); border: 1.5px solid rgba(0, 255, 255, 0.3); border-radius: 14px; text-align: center; padding: 28px 0; margin-bottom: 24px;">
        <span style="font-size: 42px; font-weight: 900; letter-spacing: 12px; color: #00ffff;">{otp}</span>
      </div>
      <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 28px;">
        <div style="color: #00ffff; font-weight: 700; font-size: 14px; margin-bottom: 6px;">
          ✓ Important Security Note
        </div>
        <div style="color: #cbd5e1; font-size: 13px; line-height: 1.6;">
          This code will expire in 10 minutes. If you did not request this code, you can safely ignore this email.
        </div>
      </div>
      <p style="color: #475569; font-size: 11px; text-align: center; margin: 0;">
        This is an automated notification from AI Assessment Studio. Please do not reply.
      </p>
    </div>
    """


def _send_via_smtp(to_email, subject, text_content, html_content, mail_user, mail_pass):
    """Sends email via Gmail SMTP (port 587 TLS or port 465 SSL)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"AI Assessment Studio <{mail_user}>"
    msg["To"] = to_email
    msg["Auto-Submitted"] = "auto-generated"
    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    # Try Port 587 (TLS)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=6) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(mail_user, mail_pass)
            server.sendmail(mail_user, [to_email], msg.as_string())
        print(f"[MAIL] Gmail SMTP (587) sent successfully to {to_email}")
        return True
    except Exception as e587:
        print(f"[MAIL] Gmail SMTP (587) notice: {e587}")

    # Try Port 465 (SSL)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=6) as server:
            server.ehlo()
            server.login(mail_user, mail_pass)
            server.sendmail(mail_user, [to_email], msg.as_string())
        print(f"[MAIL] Gmail SMTP (465) sent successfully to {to_email}")
        return True
    except Exception as e465:
        print(f"[MAIL] Gmail SMTP (465) notice: {e465}")

    return False


def _send_via_resend(to_email, subject, text_content, html_content, api_key):
    """Send via Resend HTTP API (port 443 HTTPS)."""
    resend_domain = (os.environ.get("RESEND_DOMAIN") or "").strip()
    if resend_domain and resend_domain != "resend.dev":
        from_addr = f"AI Assessment Studio <notifications@{resend_domain}>"
    else:
        from_addr = "AI Assessment Studio <onboarding@resend.dev>"

    payload = json.dumps({
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "text": text_content
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = resp.read().decode()
            print(f"[MAIL] Resend HTTP response: {resp.status} {body[:100]}")
            return resp.status in (200, 201)
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode() if http_err.fp else ""
        print(f"[MAIL] Resend HTTP error {http_err.code}: {err_body[:200]}")
        return False
    except urllib.error.URLError as url_err:
        print(f"[MAIL] Resend URL error: {url_err.reason}")
        return False


def _send_via_sendgrid(to_email, subject, text_content, html_content, api_key):
    """Send via SendGrid HTTP API (port 443 HTTPS)."""
    from_addr = (os.environ.get("MAIL_USERNAME") or "aiinterviewplatform26@gmail.com").strip()
    payload = json.dumps({
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_addr, "name": "AI Assessment Studio"},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_content},
            {"type": "text/html",  "value": html_content},
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            print(f"[MAIL] SendGrid HTTP response: {resp.status}")
            return resp.status == 202
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode() if http_err.fp else ""
        print(f"[MAIL] SendGrid HTTP error {http_err.code}: {err_body[:200]}")
        return False
    except urllib.error.URLError as url_err:
        print(f"[MAIL] SendGrid URL error: {url_err.reason}")
        return False


def send_email_notification(to_email, subject, text_content, html_content):
    """
    Master email dispatcher with multi-provider failover:
      1. Gmail SMTP (port 587 TLS / port 465 SSL)
      2. Resend HTTP API (port 443 HTTPS)
      3. SendGrid HTTP API (port 443 HTTPS)
    """
    to_email = (to_email or "").strip()
    if not to_email:
        return False

    # 1. Try Gmail SMTP
    mail_user = (os.environ.get("MAIL_USERNAME") or "").strip()
    mail_pass = (os.environ.get("MAIL_PASSWORD") or "").replace(" ", "").strip()
    if mail_user and mail_pass:
        if _send_via_smtp(to_email, subject, text_content, html_content, mail_user, mail_pass):
            return True

    # 2. Try Resend HTTP API
    resend_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    if resend_key:
        if _send_via_resend(to_email, subject, text_content, html_content, resend_key):
            return True

    # 3. Try SendGrid HTTP API
    sg_key = (os.environ.get("SENDGRID_API_KEY") or "").strip()
    if sg_key:
        if _send_via_sendgrid(to_email, subject, text_content, html_content, sg_key):
            return True

    print(f"[MAIL] All dispatch methods exhausted for {to_email}")
    return False


def send_otp_email(to_email, otp):
    """Sends login OTP verification email."""
    subject = "Your AI Assessment Studio login code"
    text_content = (
        f"Hi there,\n\n"
        f"You recently requested to access the AI Assessment Studio. "
        f"Please use the secure code below to complete your login securely.\n\n"
        f"Code: {otp}\n\n"
        f"This code will expire in 10 minutes. If you did not request this code, you can safely ignore this email.\n\n"
        f"Visit: https://ai-interview-platform-3-vdic.onrender.com"
    )
    html_content = _otp_html_body(otp)
    return send_email_notification(to_email, subject, text_content, html_content)


def send_slot_unlocked_email(to_email, candidate_name):
    """Sends assessment slot unlocked notification email in a background thread."""
    subject = "Your Assessment Slot Has Been Unlocked - AI Assessment Studio"
    candidate_display = (candidate_name or "Candidate").strip()

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px; background: #080e1e; color: #e2e8f0; border-radius: 16px; border: 1px solid rgba(0, 255, 255, 0.25);">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="background: rgba(0, 255, 255, 0.12); color: #00ffff; border: 1px solid rgba(0, 255, 255, 0.3); border-radius: 100px; padding: 6px 18px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;">
          Assessment Status Update
        </span>
      </div>
      <h2 style="color: #ffffff; font-size: 22px; font-weight: 800; margin-bottom: 8px; text-align: center;">
        New Interview Slot Authorized!
      </h2>
      <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin-bottom: 24px; text-align: center;">
        Great news, <strong>{candidate_display}</strong>! An additional standard evaluation slot has been unlocked for your account on AI Assessment Studio.
      </p>
      <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 28px;">
        <div style="color: #00ffff; font-weight: 700; font-size: 14px; margin-bottom: 6px;">
          What is Next?
        </div>
        <div style="color: #cbd5e1; font-size: 13px; line-height: 1.6;">
          Log in to your workspace dashboard to launch your new assessment session. Ensure your camera, microphone, and quiet environment are ready.
        </div>
      </div>
      <div style="text-align: center; margin-bottom: 24px;">
        <a href="https://ai-interview-platform-3-vdic.onrender.com" style="background: linear-gradient(135deg, #00ffff, #0284c7); color: #020510; text-decoration: none; padding: 12px 32px; border-radius: 10px; font-weight: 800; font-size: 15px; display: inline-block;">
          Open AI Assessment Studio &rarr;
        </a>
      </div>
      <p style="color: #475569; font-size: 11px; text-align: center; margin: 0;">
        This is an automated notification from AI Assessment Studio. Please do not reply.
      </p>
    </div>
    """

    text_content = (
        f"Hello {candidate_display},\n\n"
        f"Your standard assessment slot has been unlocked! Log in to your workspace to begin your new evaluation session.\n\n"
        f"Open AI Assessment Studio: https://ai-interview-platform-3-vdic.onrender.com"
    )

    def _dispatch():
        send_email_notification(to_email, subject, text_content, html_content)

    t = threading.Thread(target=_dispatch, daemon=True)
    t.start()
