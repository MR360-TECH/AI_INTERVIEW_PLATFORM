import os
import json
import smtplib
import threading
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import APP_BASE_URL
from MODULES.LAYER_3_BUSINESS_SERVICES import email_templates


def _send_via_smtp(to_email, subject, text_content, html_content, mail_user, mail_pass, reply_to=None):
    """Sends email via Gmail SMTP (port 587 TLS or port 465 SSL)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"AI Interview Platform <{mail_user}>"
    msg["To"] = to_email
    msg["Auto-Submitted"] = "auto-generated"
    if reply_to:
        msg["Reply-To"] = reply_to
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


def _send_via_resend(to_email, subject, text_content, html_content, api_key, reply_to=None):
    """Send via Resend HTTP API (port 443 HTTPS)."""
    resend_domain = (os.environ.get("RESEND_DOMAIN") or "").strip()
    if resend_domain and resend_domain != "resend.dev":
        from_addr = f"AI Interview Platform <notifications@{resend_domain}>"
    else:
        from_addr = "AI Interview Platform <onboarding@resend.dev>"

    body = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "text": text_content
    }
    if reply_to:
        body["reply_to"] = reply_to
    payload = json.dumps(body).encode("utf-8")

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


def _send_via_sendgrid(to_email, subject, text_content, html_content, api_key, reply_to=None):
    """Send via SendGrid HTTP API (port 443 HTTPS)."""
    from_addr = (os.environ.get("MAIL_USERNAME") or "aiinterviewplatform26@gmail.com").strip()
    body = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_addr, "name": "AI Interview Platform"},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_content},
            {"type": "text/html",  "value": html_content},
        ]
    }
    if reply_to:
        body["reply_to"] = {"email": reply_to}
    payload = json.dumps(body).encode("utf-8")

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


def send_email_notification(to_email, subject, text_content, html_content, reply_to=None):
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
        if _send_via_smtp(to_email, subject, text_content, html_content, mail_user, mail_pass, reply_to):
            return True

    # 2. Try Resend HTTP API
    resend_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    if resend_key:
        if _send_via_resend(to_email, subject, text_content, html_content, resend_key, reply_to):
            return True

    # 3. Try SendGrid HTTP API
    sg_key = (os.environ.get("SENDGRID_API_KEY") or "").strip()
    if sg_key:
        if _send_via_sendgrid(to_email, subject, text_content, html_content, sg_key, reply_to):
            return True

    print(f"[MAIL] All dispatch methods exhausted for {to_email}")
    return False


def send_otp_email(to_email, otp):
    """Sends login / verification OTP email."""
    subject, text_content, html_content = email_templates.otp_email(otp, APP_BASE_URL)
    return send_email_notification(to_email, subject, text_content, html_content)


def send_slot_unlocked_email(to_email, candidate_name):
    """Sends assessment slot unlocked notification email in a background thread."""
    subject, text_content, html_content = email_templates.slot_unlocked_email(candidate_name, APP_BASE_URL)

    def _dispatch():
        send_email_notification(to_email, subject, text_content, html_content)

    t = threading.Thread(target=_dispatch, daemon=True)
    t.start()
