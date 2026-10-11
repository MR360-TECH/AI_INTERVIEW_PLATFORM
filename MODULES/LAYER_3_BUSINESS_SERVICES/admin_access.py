"""Who may open the admin account, and from which devices.

  * Device approval: when ADMIN_APPROVAL_EMAIL is set, the admin password works only on devices the owner approved. The
    first sign-in on a new device sends an approval e-mail to that mailbox; the device waits until the owner presses
    Approve (or This wasn't me). The link works once and for one hour.
  * Password fingerprints: every signed-in session (admin and candidate) carries a fingerprint of the password it was
    opened with. When the password changes, the fingerprint no longer matches, so every device is signed out; approved
    admin devices must be approved again.
  * Safe "continue to" addresses after sign-in (only pages of this site).
"""
import hashlib
import re
import secrets
from datetime import datetime, timedelta

DEVICE_COOKIE = "aip_admin_device"
DEVICE_COOKIE_DAYS = 3650                 # the device stays known until it is removed; approval is what matters
APPROVAL_LINK_MINUTES = 60
APPROVAL_REQUESTS_PER_HOUR = 5            # someone who knows the password cannot flood the owner's mailbox


def fingerprint(secret, salt):
    """A short one-way code made from a password (or a password hash). It cannot be turned back into the password."""
    return hashlib.sha256(("%s|%s" % (salt or "", secret or "")).encode("utf-8")).hexdigest()[:24]


def token_hash(token):
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def new_token():
    return secrets.token_urlsafe(32)


def device_label(user_agent):
    """'Chrome on Windows', 'Safari on iPhone' ... from the browser's User-Agent text."""
    ua = user_agent or ""
    if "Edg/" in ua:
        browser = "Edge"
    elif "OPR/" in ua or "Opera" in ua:
        browser = "Opera"
    elif "SamsungBrowser" in ua:
        browser = "Samsung Internet"
    elif "Firefox/" in ua:
        browser = "Firefox"
    elif "Chrome/" in ua or "CriOS/" in ua:
        browser = "Chrome"
    elif "Safari/" in ua:
        browser = "Safari"
    else:
        browser = "A browser"
    if "iPhone" in ua:
        system = "iPhone"
    elif "iPad" in ua:
        system = "iPad"
    elif "Android" in ua:
        system = "Android"
    elif "Windows" in ua:
        system = "Windows"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        system = "Mac"
    elif "Linux" in ua:
        system = "Linux"
    else:
        system = "an unknown system"
    return "%s on %s" % (browser, system)


def safe_next(value, default="/admin"):
    """Only an address on this site ('/admin/users?q=...'), never another site, after signing in."""
    value = (value or "").strip()
    if (not value.startswith("/") or value.startswith("//") or "\\" in value or len(value) > 300
            or re.search(r"[\r\n]", value)):
        return default
    return value


def masked(address):
    """p****@gmail.com: enough for the owner to recognise their mailbox, not enough to learn it."""
    name, _, domain = (address or "").partition("@")
    return (name[:1] + "****@" + domain) if domain else "your mailbox"


def approval_expired(device, now=None):
    return not device.approve_expires or (now or datetime.utcnow()) > device.approve_expires


def open_approval(device, now=None):
    """Gives a waiting device a fresh one-hour approval link. Returns the link token (sent by e-mail, stored only hashed)."""
    now = now or datetime.utcnow()
    token = new_token()
    device.status = "pending"
    device.approve_hash = token_hash(token)
    device.approve_expires = now + timedelta(minutes=APPROVAL_LINK_MINUTES)
    device.requested_at = now
    return token
