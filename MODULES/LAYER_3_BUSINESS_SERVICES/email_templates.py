"""Pure email builders: no database, no network. Every function returns (subject, text, html).

Look: the app's own "cyber blue" theme (deep navy surfaces, cyan accents, white headings) so an email feels like
a continuation of the website.

Layout rules (so the emails read well on phones as well as desktops):
  * one fluid 600px column, table based, inline CSS (the fixed width only applies to Outlook)
  * body text 16px, buttons become full width on narrow screens, the score card stacks on narrow screens
"""
import os
import re
from html import escape

APP_NAME = "AI Interview Platform"


def _logo_url():
    """The app logo (same icon as the top-left of the website). Mail clients can only load it from a public https address."""
    base = (os.environ.get("APP_BASE_URL") or "https://ai-interview-platform-r8u8.onrender.com").strip().rstrip("/")
    return f"{base}/static/images/logo-icon.png" if base.startswith("https://") else ""

_FONT = "'Outfit',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

# Theme (matches the website: --bg #020510, --surface #08122a, cyan #00ffff, blue #0284c7)
_BG = "#020510"
_SURFACE = "#08122a"
_PANEL = "#0b1633"
_BORDER = "#1e3a52"
_LINE = "#1e293b"
_TEXT = "#e2e8f0"
_MUTED = "#cbd5e1"
_SOFT = "#94a3b8"
_CYAN = "#00ffff"
_ON_CYAN = "#020510"

# Result chip per tone band: (label, background, text colour, border). Deliberately no red / no verdict words.
BAND_STYLE = {
    "outstanding": ("Outstanding performance", "#3b2f06", "#fcd34d", "#a16207"),
    "excellent": ("Excellent performance", "#052e2b", "#34d399", "#065f46"),
    "done_well": ("Strong performance", "#052e2b", "#34d399", "#065f46"),
    "close": ("Almost there", "#0c2a4d", "#7dd3fc", "#075985"),
    "developing": ("Room to grow", "#1e1b4b", "#a5b4fc", "#3730a3"),
    "foundation": ("Building foundations", "#1e1b4b", "#a5b4fc", "#3730a3"),
    "brief": ("Short session", "#1e293b", "#cbd5e1", "#475569"),
    "exited": ("Incomplete session", "#3b2a06", "#fbbf24", "#92400e"),
}

# The feedback e-mail per band: (accent colour, hero tint, headline, closing line). The subject is chosen in
# FEEDBACK_SUBJECTS: an upbeat subject for the top results, a neutral one otherwise (a low score is never announced in
# the inbox).
FEEDBACK_LOOK = {
    "outstanding": ("#fcd34d", "#2a2208", "An outstanding performance", "Congratulations on a truly outstanding result."),
    "excellent": ("#34d399", "#062a22", "An excellent performance", "Well done, and thank you for the effort you put in."),
    "done_well": ("#34d399", "#062a22", "You have done well", "Good work. A little more depth will take you even further."),
    "close": ("#7dd3fc", "#0a2238", "You were very close", "You are nearly there. Keep going."),
    "developing": ("#a5b4fc", "#17153d", "Your assessment is complete", "Every improvement starts with a first step, and you have taken it."),
    "foundation": ("#a5b4fc", "#17153d", "Your learning plan starts here", "Take it one topic at a time. Progress comes quickly with regular practice."),
    "brief": ("#cbd5e1", "#1e293b", "Your session was short", "We look forward to seeing a complete session from you."),
    "exited": ("#fbbf24", "#2a1f06", "Your assessment ended early", "We look forward to seeing a complete session from you."),
}
FEEDBACK_SUBJECTS = {
    "outstanding": "Outstanding result in your assessment · {code}",
    "excellent": "Excellent work on your assessment · {code}",
    "done_well": "Your assessment is complete · {code}",
    "brief": "Your assessment summary · {code}",
    "exited": "Your assessment report · {code}",
}
NEUTRAL_SUBJECT = "Your assessment report is ready · {code}"
SIGN_OFF = "The AI Interview Platform team"
_TAKEAWAY_ICONS = ["&#9733;", "&#9678;", "&#10148;"]

# Colour of the numbered badge of each coaching section, by position.
_SECTION_COLOURS = ["#00ffff", "#38bdf8", "#2dd4bf"]


# ──────────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────────

def display_name(full_name):
    """The candidate's full name in proper case, or None when the stored name does not look like a real name
    (OTP accounts get a name derived from the email address, e.g. 'pw123')."""
    parts = (full_name or "").split()
    if not 1 <= len(parts) <= 4 or len(re.sub(r"[^\w]|\d|_", "", parts[0])) < 2:
        return None
    cleaned = []
    for token in parts:
        if not re.fullmatch(r"[^\W\d_][^\W\d_'\-]*\.?", token) or len(token) > 30:
            return None
        cleaned.append(token[0].upper() + token[1:].lower() if (token.isupper() or token.islower()) else token)
    return " ".join(cleaned)


def greeting_for(full_name):
    name = display_name(full_name)
    return f"Dear {name}," if name else "Dear Candidate,"


def one_line(value, limit=60):
    """Collapse to a single safe line (also prevents header injection in subjects)."""
    cleaned = re.sub(r"\s+", " ", re.sub(r"[\r\n\t]", " ", value or "")).strip()
    return (cleaned[:limit].rstrip() + "…") if len(cleaned) > limit else cleaned


# ──────────────────────────────────────────────────────────────────────────────
# Building blocks (HTML)
# ──────────────────────────────────────────────────────────────────────────────

def _badge(text):
    return (f'<div style="margin:0 0 16px 0;"><span style="display:inline-block;padding:6px 14px;border-radius:999px;'
            f'background:#062a3b;border:1px solid #0e7490;font-family:{_FONT};font-size:12px;font-weight:700;'
            f'letter-spacing:0.09em;text-transform:uppercase;color:{_CYAN};">{escape(text)}</span></div>')


def _callout(title, text):
    """Titled box with a cyan outline, like 'Important Security Note' / 'What is Next?' in the original emails."""
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px 0;">'
            f'<tr><td style="background:#062a3b;border:1.5px solid #0e7490;border-radius:12px;padding:16px 18px;">'
            f'<div style="font-family:{_FONT};font-size:14px;font-weight:700;color:{_CYAN};margin-bottom:6px;">'
            f'&#10003; {escape(title)}</div>'
            f'<div style="font-family:{_FONT};font-size:15px;line-height:1.6;color:{_MUTED};">{escape(text)}</div>'
            '</td></tr></table>')


def _quote_box(title, text):
    """The user's own words: keeps line breaks, wraps long words, always HTML-escaped."""
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px 0;">'
            f'<tr><td style="background:{_PANEL};border:1px solid {_BORDER};border-left:4px solid {_CYAN};border-radius:10px;padding:16px 18px;">'
            f'<div style="font-family:{_FONT};font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
            f'color:{_CYAN};margin-bottom:8px;">{escape(title)}</div>'
            f'<div style="font-family:{_FONT};font-size:16px;line-height:1.65;color:{_TEXT};white-space:pre-wrap;'
            f'word-break:break-word;">{escape(text)}</div></td></tr></table>')


def _paragraph(text):
    return (f'<p style="margin:0 0 18px 0;font-family:{_FONT};font-size:16px;line-height:1.7;'
            f'color:{_MUTED};">{escape(text)}</p>')


def _button(url, label):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" class="btn-tbl" style="margin:6px 0 22px 0;"><tr>'
            f'<td align="center" bgcolor="#06b6d4" class="btn-td" '
            f'style="border-radius:10px;background:{_CYAN};background-image:linear-gradient(135deg,#00ffff,#0284c7);">'
            f'<a href="{escape(url, quote=True)}" target="_blank" class="btn-a" style="display:inline-block;padding:15px 32px;'
            f'font-family:{_FONT};font-size:16px;font-weight:800;color:{_ON_CYAN};text-decoration:none;'
            f'border-radius:10px;">{escape(label)}</a></td></tr></table>')


def _summary_table(rows):
    cells = []
    for index, (label, value) in enumerate(rows):
        border = "" if index == len(rows) - 1 else f"border-bottom:1px solid {_LINE};"
        cells.append(
            f'<tr><td style="padding:12px 16px;{border}font-family:{_FONT};font-size:14px;color:{_SOFT};'
            f'width:38%;">{escape(label)}</td>'
            f'<td style="padding:12px 16px;{border}font-family:{_FONT};font-size:15px;font-weight:600;'
            f'color:#ffffff;">{escape(value)}</td></tr>')
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:4px 0 24px 0;background:{_PANEL};border:1px solid {_BORDER};border-radius:12px;">'
            + "".join(cells) + '</table>')


def _result_card(score, band, rows):
    """Score hero + tone chip, then the session facts. Stacks on narrow screens."""
    label, chip_bg, chip_fg, chip_border = BAND_STYLE[band]
    facts = "".join(
        f'<tr><td style="padding:10px 0;border-top:1px solid {_LINE};font-family:{_FONT};font-size:13px;color:{_SOFT};'
        f'width:36%;">{escape(k)}</td>'
        f'<td style="padding:10px 0;border-top:1px solid {_LINE};font-family:{_FONT};font-size:15px;font-weight:600;'
        f'color:#ffffff;">{escape(v)}</td></tr>' for k, v in rows)
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="margin:4px 0 28px 0;background:{_PANEL};border:1px solid {_BORDER};border-radius:14px;">'
        '<tr><td class="card-pad" style="padding:22px 22px 6px 22px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td class="stack" valign="middle" style="font-family:{_FONT};">'
        f'<span class="score" style="font-size:52px;font-weight:800;line-height:1;color:{_CYAN};">{score:.1f}</span>'
        f'<span style="font-size:20px;font-weight:600;color:{_SOFT};"> / 10</span></td>'
        f'<td class="stack chip-cell" align="right" valign="middle" style="font-family:{_FONT};">'
        f'<span style="display:inline-block;padding:8px 16px;border-radius:999px;background:{chip_bg};color:{chip_fg};'
        f'border:1px solid {chip_border};font-size:13px;font-weight:700;">{escape(label)}</span></td>'
        '</tr></table></td></tr>'
        f'<tr><td class="card-pad" style="padding:8px 22px 14px 22px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{facts}</table></td></tr></table>')


def _section_heading(text):
    return (f'<div style="margin:2px 0 14px 0;padding-top:4px;font-family:{_FONT};font-size:13px;font-weight:700;'
            f'letter-spacing:0.08em;text-transform:uppercase;color:{_SOFT};">{escape(text)}</div>')


def _coaching_sections(sections):
    """Numbered rows: badge + small heading + one short sentence."""
    out = []
    for index, section in enumerate(sections):
        colour = _SECTION_COLOURS[index % len(_SECTION_COLOURS)]
        out.append(
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0;"><tr>'
            f'<td width="46" valign="top" style="padding:0 14px 20px 0;">'
            f'<div style="width:32px;height:32px;line-height:32px;border-radius:16px;background:{colour};color:{_ON_CYAN};'
            f'text-align:center;font-family:{_FONT};font-size:14px;font-weight:800;">{index + 1}</div></td>'
            f'<td valign="top" style="padding:0 0 20px 0;">'
            f'<div style="font-family:{_FONT};font-size:12px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;'
            f'color:{colour};margin-bottom:4px;">{escape(section["title"])}</div>'
            f'<div style="font-family:{_FONT};font-size:16px;line-height:1.6;color:{_TEXT};">{escape(section["text"])}</div>'
            f'</td></tr></table>')
    return "".join(out)


def _bullet_list(items):
    rows = "".join(
        f'<tr><td valign="top" style="padding:5px 12px 5px 0;font-family:{_FONT};font-size:16px;color:{_CYAN};">&#10003;</td>'
        f'<td style="padding:5px 0;font-family:{_FONT};font-size:16px;line-height:1.6;color:{_MUTED};">{escape(item)}</td></tr>'
        for item in items)
    return f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 22px 0;">{rows}</table>'


def _code_box(code):
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:6px 0 24px 0;">'
            f'<tr><td align="center" class="code" style="background:#062a3b;border:1.5px solid #0e7490;border-radius:12px;padding:24px 0;'
            f'font-family:Consolas,Menlo,monospace;font-size:34px;font-weight:700;letter-spacing:10px;color:{_CYAN};">'
            f'{escape(code)}</td></tr></table>')


_RESPONSIVE_CSS = """
body,table,td,a{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}
@media only screen and (max-width:520px){
  .wrap{padding:12px 6px !important}
  .px{padding-left:20px !important;padding-right:20px !important}
  .h1{font-size:23px !important;line-height:1.3 !important}
  .score{font-size:46px !important}
  .ring-cell{padding-top:16px !important;text-align:left !important}
  .stack{display:block !important;width:100% !important;text-align:left !important}
  .chip-cell{padding-top:12px !important}
  .card-pad{padding-left:18px !important;padding-right:18px !important}
  .btn-tbl,.btn-td{width:100% !important;display:block !important}
  .btn-a{display:block !important;text-align:center !important}
  .code{font-size:28px !important;letter-spacing:7px !important}
}"""


def _layout(title, preheader, body_html, footer_reason, hero=""):
    logo = _logo_url()
    logo_cell = (f'<td width="40" style="width:40px;"><img src="{logo}" width="40" height="40" alt="" '
                 'style="display:block;border:0;outline:none;width:40px;height:40px;border-radius:11px;"></td>') if logo else (
                 f'<td style="width:12px;height:12px;background:{_CYAN};border-radius:3px;font-size:0;line-height:0;">&nbsp;</td>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<meta name="supported-color-schemes" content="dark light">
<title>{escape(title)}</title>
<style>{_RESPONSIVE_CSS}</style>
</head>
<body style="margin:0;padding:0;background:{_BG};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{_BG}" style="background:{_BG};">
<tr><td align="center" class="wrap" style="padding:32px 12px;">
<!--[if mso]><table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0"><tr><td><![endif]-->
  <table role="presentation" cellpadding="0" cellspacing="0" bgcolor="{_SURFACE}" style="width:100%;max-width:600px;background:{_SURFACE};border:1px solid {_BORDER};border-radius:16px;overflow:hidden;">
    <tr><td class="px" bgcolor="#0a1a35" style="background:#0a1a35;background-image:linear-gradient(135deg,#0a2540,#0c3a63);padding:20px 32px;">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        {logo_cell}
        <td style="padding-left:12px;font-family:{_FONT};font-size:19px;font-weight:800;letter-spacing:-0.01em;color:#ffffff;">{APP_NAME}</td>
      </tr></table>
    </td></tr>
    <tr><td style="height:3px;background:{_CYAN};background-image:linear-gradient(90deg,#00ffff,#0284c7);font-size:0;line-height:0;">&nbsp;</td></tr>
    {hero}
    <tr><td class="px" style="padding:32px 32px 14px 32px;">{body_html}</td></tr>
    <tr><td class="px" bgcolor="#050b1c" style="padding:20px 32px 26px 32px;background:#050b1c;border-top:1px solid {_LINE};">
      <p style="margin:0 0 6px 0;font-family:{_FONT};font-size:12px;line-height:1.6;color:{_SOFT};">{escape(footer_reason)}</p>
      <p style="margin:0;font-family:{_FONT};font-size:12px;line-height:1.6;color:#7c8ba1;">{APP_NAME} &middot; This is an automated message, please do not reply.</p>
    </td></tr>
  </table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr>
</table>
</body>
</html>"""


def _build(subject, preheader, title, greeting, paragraphs, footer_reason, rows=None, card=None, sections=None,
           sections_title=None, bullets=None, code=None, button=None, closing=None, badge=None, callout=None,
           quote=None, groups=None):
    body = ([_badge(badge)] if badge else []) + [
        f'<h1 class="h1" style="margin:0 0 18px 0;font-family:{_FONT};font-size:26px;line-height:1.3;color:#ffffff;">{escape(title)}</h1>',
        _paragraph(greeting)]
    text = ([badge.upper(), ""] if badge else []) + [title, "", greeting, ""]
    for paragraph in paragraphs:
        body.append(_paragraph(paragraph))
        text += [paragraph, ""]
    if code:
        body.append(_code_box(code))
        text += [f"Code: {code}", ""]
    if bullets:
        body.append(_bullet_list(bullets))
        text += [f"  - {item}" for item in bullets] + [""]
    if card:                                   # (score, band, rows)
        body.append(_result_card(*card))
        text += ["YOUR RESULT", f"Score: {card[0]:.1f} / 10 ({BAND_STYLE[card[1]][0]})"] + [f"{k}: {v}" for k, v in card[2]] + [""]
    if rows:
        body.append(_summary_table(rows))
        text += [f"{label}: {value}" for label, value in rows] + [""]
    for group_title, group_rows in (groups or []):
        body.append(_section_heading(group_title))
        body.append(_summary_table(group_rows))
        text += [group_title.upper()] + [f"{k}: {v}" for k, v in group_rows] + [""]
    if quote:
        body.append(_quote_box(*quote))
        text += [f"{quote[0]}:", quote[1], ""]
    if sections:
        if sections_title:
            body.append(_section_heading(sections_title))
            text += [sections_title.upper()]
        body.append(_coaching_sections(sections))
        for section in sections:
            text += [f"{section['title']}: {section['text']}"]
        text += [""]
    if callout:
        body.append(_callout(*callout))
        text += [f"{callout[0]}: {callout[1]}", ""]
    if button:
        body.append(_button(button[1], button[0] + " →"))
        text += [f"{button[0]}: {button[1]}", ""]
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
        opening = ("Welcome to AI Interview Platform. Your Google account is now linked and your workspace is ready. "
                   "Upload your resume to get interview questions that fit your experience.")
    else:
        opening = ("Welcome to AI Interview Platform, and thank you for registering. Your workspace is ready, and the best "
                   "way to start is by uploading your resume so your interviews match your experience.")
    return _build(
        subject=f"Welcome to {APP_NAME}",
        preheader="Your workspace is ready.",
        badge="Welcome Aboard",
        title=f"Welcome to {APP_NAME}",
        greeting=greeting_for(full_name),
        paragraphs=[opening, "Here is what you can do:"],
        bullets=["Take adaptive AI interviews tailored to your domain and resume",
                 "Build confidence in the practice lab: viva, language and concept drills",
                 "Prepare with curated resources for leading employers",
                 "Review a detailed written report after every assessment"],
        button=("Open your dashboard", f"{base_url}/dashboard"),
        footer_reason="You received this email because you registered an account on our platform.")


def plain_text(value):
    """The opening paragraphs mark key phrases with **...**; the plain-text part shows them without the markers."""
    return (value or "").replace("**", "")


def _rich_paragraph(text):
    """A paragraph whose **...** phrases become bold white text. Escaped first, so nothing else can become HTML."""
    body = re.sub(r"\*\*(.+?)\*\*", r'<strong style="color:#ffffff;font-weight:700;">\1</strong>', escape(text))
    return (f'<p style="margin:0 0 24px 0;font-family:{_FONT};font-size:16px;line-height:1.75;'
            f'color:{_MUTED};">{body}</p>')


def _feedback_hero(band, headline, meta_line, score):
    """Tinted top band: result chip, headline, the domain / level / date line and (when there is a score) a ring."""
    tone, tint = FEEDBACK_LOOK[band][0], FEEDBACK_LOOK[band][1]
    label = BAND_STYLE[band][0]
    ring = ""
    bar = ""
    if score is not None:
        ring = (f'<td width="124" class="stack ring-cell" align="right" valign="middle">'
                f'<div style="width:104px;height:104px;border-radius:58px;background:{_BG};border:6px solid {tone};text-align:center;">'
                f'<div style="font-family:{_FONT};font-size:32px;font-weight:900;color:#ffffff;line-height:1;padding-top:26px;">{score:.1f}</div>'
                f'<div style="font-family:{_FONT};font-size:11px;font-weight:700;color:{_SOFT};margin-top:4px;">out of 10</div></div></td>')
        pct = max(0, min(100, int(round(score * 10))))
        bar = ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;"><tr>'
               f'<td style="height:8px;background:{_LINE};border-radius:8px;font-size:0;line-height:0;">'
               f'<div style="width:{pct}%;height:8px;background:{tone};border-radius:8px;font-size:0;line-height:0;">&nbsp;</div>'
               '</td></tr></table>')
    return (
        f'<tr><td class="px" bgcolor="{tint}" style="padding:30px 32px 26px 32px;background:{tint};'
        f'background-image:linear-gradient(160deg,{tint} 0%,{_SURFACE} 100%);border-bottom:1px solid {_BORDER};">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        '<td class="stack" valign="middle">'
        f'<div style="display:inline-block;padding:5px 12px;border-radius:999px;background:{_BG};border:1px solid {tone};'
        f'font-family:{_FONT};font-size:11px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:{tone};">{escape(label)}</div>'
        f'<div class="h1" style="font-family:{_FONT};font-size:26px;font-weight:800;line-height:1.25;color:#ffffff;margin:12px 0 6px;">{escape(headline)}</div>'
        f'<div style="font-family:{_FONT};font-size:14px;line-height:1.5;color:{_MUTED};">{escape(meta_line)}</div>'
        f'</td>{ring}</tr></table>{bar}</td></tr>')


def _takeaway_cards(band, sections):
    tone, tint = FEEDBACK_LOOK[band][0], FEEDBACK_LOOK[band][1]
    rows = []
    for index, section in enumerate(sections):
        icon = _TAKEAWAY_ICONS[index % len(_TAKEAWAY_ICONS)]
        rows.append(
            '<tr><td style="padding:0 0 12px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:{_PANEL};border:1px solid {_BORDER};border-left:4px solid {tone};border-radius:12px;"><tr>'
            f'<td width="52" valign="top" style="padding:16px 0 16px 16px;"><div style="width:34px;height:34px;line-height:34px;'
            f'border-radius:10px;background:{tint};color:{tone};text-align:center;font-size:16px;font-family:{_FONT};">{icon}</div></td>'
            f'<td style="padding:14px 16px 14px 12px;"><div style="font-family:{_FONT};font-size:12px;font-weight:800;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:{tone};margin-bottom:4px;">{escape(section["title"])}</div>'
            f'<div style="font-family:{_FONT};font-size:15px;line-height:1.6;color:{_TEXT};">{escape(section["text"])}</div>'
            '</td></tr></table></td></tr>')
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{"".join(rows)}</table>'


def _feedback_email(*, band, subject, preheader, full_name, opening, sections, sections_title, score, facts,
                    meta_line, button, footer_reason):
    """The assessment feedback e-mail: tinted hero with the result, a short bold-highlighted opening, the takeaway
    cards, the report button, a closing line and the team sign-off. Returns (subject, text, html)."""
    _tone, _tint, headline, closing = FEEDBACK_LOOK[band]
    greeting = greeting_for(full_name)

    text = [headline, "", greeting, "", plain_text(opening), "", "YOUR RESULT"]
    if score is not None:
        text.append(f"Score: {score:.1f} / 10 ({BAND_STYLE[band][0]})")
    text += [f"{k}: {v}" for k, v in facts] + ["", sections_title.upper()]
    text += [f"{s['title']}: {s['text']}" for s in sections]
    text += ["", f"{button[0]}: {button[1]}", "", closing, SIGN_OFF,
             "--", footer_reason, f"{APP_NAME} - automated message, please do not reply."]

    body = (
        f'<p style="margin:0 0 14px 0;font-family:{_FONT};font-size:16px;color:{_MUTED};">{escape(greeting)}</p>'
        + _rich_paragraph(opening)
        + _section_heading(sections_title)
        + _takeaway_cards(band, sections)
        + _button(button[1], button[0] + " →")
        + f'<p style="margin:6px 0 4px 0;font-family:{_FONT};font-size:15px;line-height:1.6;color:{_TEXT};">{escape(closing)}</p>'
        + f'<p style="margin:0 0 10px 0;font-family:{_FONT};font-size:14px;color:{_SOFT};">{SIGN_OFF}</p>')
    session = dict(facts).get("Session ID", "")
    footer = (f"Session {session} · " if session else "") + footer_reason
    html = _layout(headline, preheader, body, footer, hero=_feedback_hero(band, headline, meta_line, score))
    return subject, "\n".join(text), html


def _meta_line(domain_line, level_label, date_text):
    return " · ".join(part for part in (domain_line, level_label, date_text) if part)


def assessment_email(full_name, opening, sections, band, domain, score, session_code, date_text, result_id, base_url,
                     level_label=None):
    """sections: the takeaway lines [{"title", "text"}]. opening: the short first paragraph, with **key phrases**."""
    domain_line = one_line(domain) or "General"
    facts = [("Session ID", session_code), ("Domain", domain_line)]
    if level_label:
        facts.append(("Level", level_label))
    facts.append(("Date", date_text))
    return _feedback_email(
        band=band, subject=FEEDBACK_SUBJECTS.get(band, NEUTRAL_SUBJECT).format(code=session_code),
        preheader=f"Your report {session_code} is ready.", full_name=full_name, opening=opening, sections=sections,
        sections_title="Your next step" if band == "brief" else "Your three takeaways", score=score, facts=facts,
        meta_line=_meta_line(domain_line, level_label, date_text),
        button=("View your full report", f"{base_url}/my-history/{result_id}"),
        footer_reason="You received this email because you completed an assessment on our platform.")


def exited_email(full_name, opening, sections, domain, score, session_code, date_text, result_id, base_url, reviewed,
                 level_label=None):
    """The candidate exited a scored assessment early. With an analysis: the score ring and the takeaways. Without one
    (no answers, or the AI analysis failed): no score at all, just the status and one next step."""
    domain_line = one_line(domain) or "General"
    facts = [("Session ID", session_code), ("Domain", domain_line)]
    if level_label:
        facts.append(("Level", level_label))
    facts.append(("Date", date_text))
    if not reviewed:
        facts.append(("Status", "Exited before completion"))
    return _feedback_email(
        band="exited", subject=FEEDBACK_SUBJECTS["exited"].format(code=session_code),
        preheader=f"Your report {session_code} is ready.", full_name=full_name, opening=opening, sections=sections,
        sections_title="Your three takeaways" if reviewed else "Your next step", score=score if reviewed else None,
        facts=facts, meta_line=_meta_line(domain_line, level_label, date_text),
        button=("View your report", f"{base_url}/my-history/{result_id}"),
        footer_reason="You received this email because you took an assessment on our platform.")


def terminated_email(full_name, opening, domain, session_code, date_text, result_id, base_url):
    domain_line = one_line(domain) or "General"
    return _build(
        subject=f"Update on your assessment session · {session_code}",
        preheader=f"Details of session {session_code}.",
        badge="Session Update",
        title="Your assessment session has ended",
        greeting=greeting_for(full_name),
        paragraphs=[opening],
        rows=[("Session ID", session_code), ("Domain", domain_line), ("Date", date_text),
              ("Status", "Session ended early")],
        button=("View session details", f"{base_url}/my-history/{result_id}"),
        footer_reason="You received this email because a session was recorded on your account.")


def otp_email(otp, base_url):
    return _build(
        subject=f"Your {APP_NAME} login code",
        preheader=f"Your code is {otp}. It expires in 10 minutes.",
        badge="Platform Access Code",
        title="Your Temporary Login Code",
        greeting="Hello,",
        paragraphs=["You recently requested to access the AI Interview Platform. Please use the secure code below to "
                    "complete your login securely."],
        code=otp,
        callout=("Important Security Note", "This code will expire in 10 minutes. If you did not request this code, "
                                            "you can safely ignore this email."),
        footer_reason="You received this email because a sign-in or verification was requested for this address.")


def slot_unlocked_email(full_name, base_url):
    return _build(
        subject=f"Your assessment slot has been unlocked - {APP_NAME}",
        preheader="A new assessment slot is available on your account.",
        badge="Assessment Status Update",
        title="New Interview Slot Authorized!",
        greeting=greeting_for(full_name),
        paragraphs=["Great news! An additional standard evaluation slot has been unlocked for your account on "
                    "AI Interview Platform."],
        callout=("What is Next?", "Log in to your workspace dashboard to launch your new assessment session. Make sure "
                                  "you have a quiet environment and uninterrupted time."),
        button=(f"Open {APP_NAME}", f"{base_url}/dashboard"),
        footer_reason="You received this email because an administrator updated your assessment access.")


def feedback_received_email(user_name, user_email, rating, category_label, message, page_label, session_code,
                            when_text, contact_ok, user_id=None, account_type="", course_or_role="", member_since="",
                            sign_in_method=""):
    stars = ("\u2605" * rating + "\u2606" * (5 - rating) + f"   {rating} / 5") if rating else "Not rated"
    sender = [("Name", one_line(user_name, 60) or "-"), ("Email", one_line(user_email, 80) or "-")]
    for label, value in (("Account", account_type), ("Course / Role", course_or_role), ("Member since", member_since),
                         ("Signed in with", sign_in_method)):
        if value:
            sender.append((label, one_line(value, 60)))
    if user_id:
        sender.append(("User ID", str(user_id)))
    details = [("Topic", category_label), ("Rating", stars), ("Sent from", page_label)]
    if session_code:
        details.append(("Session ID", session_code))
    details += [("Submitted", when_text),
                ("Reply allowed", "Yes - just reply to this email" if contact_ok else "No - the user asked not to be contacted")]
    return _build(
        subject=f"New feedback \u00b7 {category_label}" + (f" \u00b7 {rating}/5" if rating else "")
                + f" \u00b7 {one_line(user_name, 40) or 'User'}",
        preheader=f"{one_line(user_name, 40) or 'A user'} ({one_line(user_email, 60)}) sent feedback: {category_label}",
        badge="New Feedback",
        title="New feedback received",
        greeting="Hello,",
        paragraphs=["A user shared feedback through the platform. Their details and message are below."],
        groups=[("Sender details", sender), ("Feedback details", details)],
        quote=("Message", message),
        footer_reason=f"You received this email because feedback was submitted on {APP_NAME}.")
