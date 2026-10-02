"""Pure email builders: no database, no network. Every function returns (subject, text, html)."""
import re
from html import escape

APP_NAME = "AI Assessment Studio"

_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
_INK = "#0f172a"
_MUTED = "#475569"
_ACCENT = "#0284c7"
_NAVY = "#0b1633"


# ──────────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────────

def first_name_for_greeting(full_name):
    """First name in proper case, or None when the stored name is not a reliable real name
    (OTP accounts get a name derived from the email address, e.g. 'pw123')."""
    token = (full_name or "").strip().split(" ")[0]
    if not re.fullmatch(r"[^\W\d_][^\W\d_'\-]{1,29}", token):
        return None
    if token.isupper() or token.islower():
        token = token[0].upper() + token[1:].lower()
    return token


def greeting_for(full_name):
    name = first_name_for_greeting(full_name)
    return f"Hi {name}," if name else "Hi there,"


def one_line(value, limit=60):
    """Collapse to a single safe line (also prevents header injection in subjects)."""
    cleaned = re.sub(r"\s+", " ", re.sub(r"[\r\n\t]", " ", value or "")).strip()
    return (cleaned[:limit].rstrip() + "…") if len(cleaned) > limit else cleaned


# ──────────────────────────────────────────────────────────────────────────────
# Building blocks (HTML)
# ──────────────────────────────────────────────────────────────────────────────

def _paragraph(text):
    return (f'<p style="margin:0 0 16px 0;font-family:{_FONT};font-size:15px;line-height:1.65;'
            f'color:{_MUTED};">{escape(text)}</p>')


def _button(url, label):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 20px 0;"><tr>'
            f'<td align="center" bgcolor="{_ACCENT}" style="border-radius:8px;">'
            f'<a href="{escape(url, quote=True)}" target="_blank" style="display:inline-block;padding:13px 30px;'
            f'font-family:{_FONT};font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;'
            f'border-radius:8px;">{escape(label)}</a></td></tr></table>')


def _summary_table(rows):
    cells = []
    for index, (label, value) in enumerate(rows):
        border = "" if index == len(rows) - 1 else "border-bottom:1px solid #e2e8f0;"
        cells.append(
            f'<tr><td style="padding:11px 16px;{border}font-family:{_FONT};font-size:13px;color:#64748b;'
            f'width:38%;">{escape(label)}</td>'
            f'<td style="padding:11px 16px;{border}font-family:{_FONT};font-size:14px;font-weight:600;'
            f'color:{_INK};">{escape(value)}</td></tr>')
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:4px 0 22px 0;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;">'
            + "".join(cells) + '</table>')


def _note_box(title, text):
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 22px 0;">'
            f'<tr><td style="background:#f0f9ff;border-left:4px solid {_ACCENT};border-radius:6px;padding:16px 18px;">'
            f'<div style="font-family:{_FONT};font-size:12px;font-weight:700;letter-spacing:0.06em;'
            f'text-transform:uppercase;color:{_ACCENT};margin-bottom:6px;">{escape(title)}</div>'
            f'<div style="font-family:{_FONT};font-size:15px;line-height:1.65;color:{_INK};">{escape(text)}</div>'
            f'</td></tr></table>')


def _bullet_list(items):
    rows = "".join(
        f'<tr><td valign="top" style="padding:4px 10px 4px 0;font-family:{_FONT};font-size:15px;color:{_ACCENT};">&#10003;</td>'
        f'<td style="padding:4px 0;font-family:{_FONT};font-size:15px;line-height:1.55;color:{_MUTED};">{escape(item)}</td></tr>'
        for item in items)
    return f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 20px 0;">{rows}</table>'


def _code_box(code):
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:6px 0 22px 0;">'
            f'<tr><td align="center" style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:22px 0;'
            f'font-family:Consolas,Menlo,monospace;font-size:34px;font-weight:700;letter-spacing:10px;color:{_NAVY};">'
            f'{escape(code)}</td></tr></table>')


def _layout(title, preheader, body_html, footer_reason):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;">
<tr><td align="center" style="padding:32px 12px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
    <tr><td style="background:{_NAVY};padding:20px 32px;">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td style="width:12px;height:12px;background:#22d3ee;border-radius:3px;font-size:0;line-height:0;">&nbsp;</td>
        <td style="padding-left:10px;font-family:{_FONT};font-size:17px;font-weight:700;letter-spacing:0.01em;color:#ffffff;">{APP_NAME}</td>
      </tr></table>
    </td></tr>
    <tr><td style="height:3px;background:{_ACCENT};font-size:0;line-height:0;">&nbsp;</td></tr>
    <tr><td style="padding:34px 32px 18px 32px;">{body_html}</td></tr>
    <tr><td style="padding:20px 32px 26px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;">
      <p style="margin:0 0 6px 0;font-family:{_FONT};font-size:12px;line-height:1.6;color:#64748b;">{escape(footer_reason)}</p>
      <p style="margin:0;font-family:{_FONT};font-size:12px;line-height:1.6;color:#94a3b8;">{APP_NAME} &middot; This is an automated message, please do not reply.</p>
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>"""


def _build(subject, preheader, title, greeting, paragraphs, footer_reason, rows=None, note=None,
           bullets=None, code=None, button=None, secondary=None, closing=None):
    body = [f'<h1 style="margin:0 0 18px 0;font-family:{_FONT};font-size:24px;line-height:1.3;color:{_INK};">{escape(title)}</h1>',
            _paragraph(greeting)]
    text = [title, "", greeting, ""]
    for paragraph in paragraphs:
        body.append(_paragraph(paragraph))
        text += [paragraph, ""]
    if code:
        body.append(_code_box(code))
        text += [f"Code: {code}", ""]
    if bullets:
        body.append(_bullet_list(bullets))
        text += [f"  - {item}" for item in bullets] + [""]
    if rows:
        body.append(_summary_table(rows))
        text += [f"{label}: {value}" for label, value in rows] + [""]
    if note:
        body.append(_note_box(note[0], note[1]))
        text += [f"{note[0]}: {note[1]}", ""]
    if button:
        body.append(_button(button[1], button[0]))
        text += [f"{button[0]}: {button[1]}", ""]
    if secondary:
        body.append(f'<p style="margin:0 0 14px 0;font-family:{_FONT};font-size:14px;color:{_MUTED};">'
                    f'{escape(secondary[0])} <a href="{escape(secondary[2], quote=True)}" style="color:{_ACCENT};'
                    f'text-decoration:none;font-weight:600;">{escape(secondary[1])} &rarr;</a></p>')
        text += [f"{secondary[0]} {secondary[1]}: {secondary[2]}", ""]
    if closing:
        body.append(_paragraph(closing))
        text += [closing, ""]
    text += ["--", footer_reason, f"{APP_NAME} - automated message, please do not reply."]
    html = _layout(title, preheader, "".join(body), footer_reason)
    return subject, "\n".join(text), html


# ──────────────────────────────────────────────────────────────────────────────
# The emails
# ──────────────────────────────────────────────────────────────────────────────

def welcome_email(full_name, base_url, via_google=False):
    if via_google:
        opening = ("Welcome to AI Assessment Studio. Your Google account is now linked and your workspace is ready. "
                   "Upload your resume to get interview questions that fit your experience.")
    else:
        opening = ("Welcome to AI Assessment Studio, and thank you for registering. Your workspace is ready, and the best "
                   "way to start is by uploading your resume so your interviews match your experience.")
    return _build(
        subject=f"Welcome to {APP_NAME}",
        preheader="Your workspace is ready.",
        title=f"Welcome to {APP_NAME}",
        greeting=greeting_for(full_name),
        paragraphs=[opening, "Here is what you can do:"],
        bullets=["Take adaptive AI interviews tailored to your domain and resume",
                 "Build confidence in the practice lab: viva, language and concept drills",
                 "Prepare with curated resources for leading employers",
                 "Review a detailed written report after every assessment"],
        button=("Open your dashboard", f"{base_url}/dashboard"),
        footer_reason="You received this email because you registered an account on our platform.")


def assessment_email(full_name, opening, note, domain, score, session_code, date_text, result_id, base_url,
                     brief=False):
    domain_line = one_line(domain) or "General"
    return _build(
        subject=(f"Your {domain_line} assessment summary · {session_code}" if brief
                 else f"Your {domain_line} assessment is complete · {session_code}"),
        preheader=f"Your report {session_code} is ready.",
        title=f"Your {domain_line} assessment is complete",
        greeting=greeting_for(full_name),
        paragraphs=[opening],
        rows=[("Session ID", session_code), ("Domain", domain_line), ("Date", date_text),
              ("Score", f"{score:.1f} / 10")],
        note=("A note for you", note) if note else None,
        button=("View your full report", f"{base_url}/my-history/{result_id}"),
        secondary=("Ready to keep improving?", "Start a practice session", f"{base_url}/practice-setup"),
        footer_reason="You received this email because you completed an assessment on our platform.")


def terminated_email(full_name, domain, session_code, date_text, result_id, base_url):
    domain_line = one_line(domain) or "General"
    return _build(
        subject=f"Update on your assessment session · {session_code}",
        preheader=f"Details of session {session_code}.",
        title="Your assessment session has ended",
        greeting=greeting_for(full_name),
        paragraphs=["Your assessment session ended early because the platform detected activity outside the exam window. "
                    "The details are in your report. Practice sessions are a good way to get comfortable with the exam format."],
        rows=[("Session ID", session_code), ("Domain", domain_line), ("Date", date_text),
              ("Status", "Session ended early")],
        button=("View session details", f"{base_url}/my-history/{result_id}"),
        secondary=("Want to get comfortable with the format?", "Try a practice session", f"{base_url}/practice-setup"),
        footer_reason="You received this email because a session was recorded on your account.")


def otp_email(otp, base_url):
    return _build(
        subject=f"Your {APP_NAME} login code",
        preheader=f"Your code is {otp}. It expires in 10 minutes.",
        title="Your login code",
        greeting="Hi there,",
        paragraphs=["Use the secure code below to complete your sign-in. It expires in 10 minutes."],
        code=otp,
        closing="If you did not request this code, you can safely ignore this email.",
        footer_reason="You received this email because a sign-in or verification was requested for this address.")


def slot_unlocked_email(full_name, base_url):
    return _build(
        subject=f"Your assessment slot has been unlocked - {APP_NAME}",
        preheader="A new assessment slot is available on your account.",
        title="A new assessment slot is available",
        greeting=greeting_for(full_name),
        paragraphs=["An additional assessment slot has been unlocked for your account. Log in to your workspace when you "
                    "are ready, and make sure you have a quiet environment and uninterrupted time."],
        button=(f"Open {APP_NAME}", f"{base_url}/dashboard"),
        footer_reason="You received this email because an administrator updated your assessment access.")
