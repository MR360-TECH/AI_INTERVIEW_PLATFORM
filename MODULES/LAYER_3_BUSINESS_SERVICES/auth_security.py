"""Server-side security for the login system: one-time codes and brute-force lockouts.

Why this exists: one-time codes used to live in the Flask session cookie. That cookie is only SIGNED, not encrypted, so
anyone could read their own cookie, see the code and log in as any email without owning the mailbox. Now:
  * the code is never stored in readable form - only a keyed hash (HMAC with SECRET_KEY) in the database
  * every code expires (10 minutes), works once, and allows 5 wrong guesses (counted in the DATABASE, so replaying an old
    cookie cannot reset the counter)
  * requesting codes is rate limited per email
  * failed logins are throttled per email+IP and per IP
"""
import hmac
import hashlib
import math
import secrets
from datetime import datetime, timedelta, timezone

from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db, SECRET_KEY
from MODULES.LAYER_2_DATA_PERSISTENCE.models import OtpChallenge, AuthThrottle

OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_SECONDS = 30
OTP_MAX_PER_HOUR = 5

THROTTLE_WINDOW_MINUTES = 15
THROTTLE_LOCK_MINUTES = 15
LOGIN_MAX_FAILURES = 5          # per email + IP
IP_MAX_FAILURES = 30            # per IP, across all emails
OTP_SEND_MAX_PER_IP = 10        # code requests per IP per window


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)      # naive UTC, same everywhere (SQLite / Postgres)


def _digest(purpose, email, code):
    return hmac.new(SECRET_KEY.encode(), f"{purpose}|{email}|{code}".encode(), hashlib.sha256).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# One-time codes
# ──────────────────────────────────────────────────────────────────────────────

def issue_otp(purpose, email):
    """Creates a fresh code. Returns (code, None) or (None, reason) where reason is 'cooldown' or 'limit'."""
    now = _now()
    recent = (OtpChallenge.query
              .filter(OtpChallenge.purpose == purpose, OtpChallenge.email == email,
                      OtpChallenge.created_at >= now - timedelta(hours=1))
              .order_by(OtpChallenge.id.desc()).all())
    if recent and (now - recent[0].created_at).total_seconds() < OTP_RESEND_SECONDS:
        return None, "cooldown"
    if len(recent) >= OTP_MAX_PER_HOUR:
        return None, "limit"
    OtpChallenge.query.filter_by(purpose=purpose, email=email, used=False).update({"used": True})
    code = f"{secrets.randbelow(10 ** 6):06d}"
    db.session.add(OtpChallenge(purpose=purpose, email=email, code_hash=_digest(purpose, email, code),
                                expires_at=now + timedelta(minutes=OTP_TTL_MINUTES), created_at=now))
    db.session.commit()
    return code, None


def verify_otp(purpose, email, entered):
    """Returns 'ok', 'invalid', 'expired' or 'locked'. A correct code works exactly once."""
    entered = (entered or "").strip()
    challenge = (OtpChallenge.query.filter_by(purpose=purpose, email=email, used=False)
                 .order_by(OtpChallenge.id.desc()).first())
    if not challenge:
        return "expired"
    if challenge.expires_at < _now():
        challenge.used = True
        db.session.commit()
        return "expired"
    if challenge.attempts >= OTP_MAX_ATTEMPTS:
        challenge.used = True
        db.session.commit()
        return "locked"
    challenge.attempts += 1
    if hmac.compare_digest(challenge.code_hash, _digest(purpose, email, entered)):
        challenge.used = True
        db.session.commit()
        return "ok"
    status = "invalid"
    if challenge.attempts >= OTP_MAX_ATTEMPTS:
        challenge.used = True
        status = "locked"
    db.session.commit()
    return status


# ──────────────────────────────────────────────────────────────────────────────
# Lockouts
# ──────────────────────────────────────────────────────────────────────────────

def throttle_seconds_left(key):
    """Seconds the caller must still wait (0 = allowed)."""
    row = AuthThrottle.query.filter_by(key=key).first()
    if row and row.locked_until and row.locked_until > _now():
        return max(1, math.ceil((row.locked_until - _now()).total_seconds()))
    return 0


def throttle_fail(key, max_failures):
    """Records one failure; locks the key for THROTTLE_LOCK_MINUTES once max_failures is reached inside the window."""
    now = _now()
    row = AuthThrottle.query.filter_by(key=key).first()
    if not row:
        row = AuthThrottle(key=key, failures=0, window_start=now)
        db.session.add(row)
    if row.window_start is None or row.window_start < now - timedelta(minutes=THROTTLE_WINDOW_MINUTES):
        row.failures, row.window_start, row.locked_until = 0, now, None
    row.failures += 1
    if row.failures >= max_failures:
        row.locked_until = now + timedelta(minutes=THROTTLE_LOCK_MINUTES)
    db.session.commit()


def throttle_reset(key):
    AuthThrottle.query.filter_by(key=key).delete()
    db.session.commit()


def minutes_text(seconds):
    minutes = max(1, math.ceil(seconds / 60))
    return f"{minutes} minute" + ("" if minutes == 1 else "s")
