"""Friendly rate limits: generous for real people, strict for scripts.

Design rules
  * Limits are far above what a person can do (a person cannot answer 12 interview questions a minute), so nobody
    notices them. A script, or a stuck refresh loop, runs into them quickly.
  * Nothing is punished: a limit is a simple sliding window. Wait a few seconds and everything works again. A limited
    request never uses an interview attempt and never loses saved progress.
  * Signed-in people are limited per ACCOUNT, not per IP address, so a whole classroom behind one college network
    does not block each other. Visitors who are not signed in are limited per IP address.
  * The AI-calling steps (interview answers and results) and a few expensive actions have their own, tighter limits,
    because every call spends Gemini quota.
  * Hourly caps (resume uploads, practice sessions) are kept in the database, so they hold across server workers.
    Per-minute limits are kept in memory for speed.

Everything can be loosened with RATE_LIMIT_SCALE (for example 2 doubles every limit) or switched off with
RATE_LIMITS_ENABLED=false.
"""
import math
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone

from flask import jsonify, make_response, render_template, request, session

from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db
from MODULES.LAYER_2_DATA_PERSISTENCE.models import AuthThrottle

# name -> (requests, seconds)
# The numbers are deliberately loose: they only stop scripts and runaway loops, never a person using the app.
LIMITS = {
    "anon":     (400, 60),     # a visitor who is not signed in: per IP address (a campus shares one address)
    "user":     (600, 60),     # any signed-in candidate: all requests together
    "ai":       (30, 60),      # interview answers: every one calls the AI (a person answers a few per minute)
    "result":   (30, 600),     # opening the evaluation of a finished interview
    "violation": (90, 60),     # integrity reports from the browser
    "resume":   (30, 3600),    # resume uploads (each one is analysed by the AI)
    "practice": (120, 3600),   # practice sessions started
}
AI_PATHS = ("/interview", "/interview/submit")
EXEMPT_PREFIXES = ("/static/",)
EXEMPT_PATHS = ("/health", "/favicon.ico", "/interview/heartbeat", "/logout")     # never limited; the administrator is never limited either

_lock = threading.Lock()
_hits = {}
_calls = [0]


def _now():
    return time.time()


def _scaled(limit):
    try:
        scale = float(os.environ.get("RATE_LIMIT_SCALE", "1"))
    except ValueError:
        scale = 1.0
    return max(1, int(limit * max(scale, 0.1)))


def allow(key, limit, window, now=None):
    """Sliding window held in memory. Returns (allowed, seconds_until_allowed)."""
    now = _now() if now is None else now
    limit = _scaled(limit)
    with _lock:
        _calls[0] += 1
        if _calls[0] % 2000 == 0:                         # drop idle keys now and then so memory cannot grow without end
            for k in [k for k, q in _hits.items() if not q or q[-1] < now - 7200]:
                _hits.pop(k, None)
        q = _hits.setdefault(key, deque())
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= limit:
            return False, max(1, math.ceil(window - (now - q[0])))
        q.append(now)
        return True, 0


def consume(key, limit, window):
    """Fixed hourly window kept in the database (shared by every server worker). Returns (allowed, seconds_left)."""
    limit = _scaled(limit)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = AuthThrottle.query.filter_by(key=key[:160]).first()
    if not row:
        row = AuthThrottle(key=key[:160], failures=0, window_start=now)
        db.session.add(row)
    if row.window_start is None or (now - row.window_start).total_seconds() >= window:
        row.failures, row.window_start = 0, now
    if (row.failures or 0) >= limit:
        left = max(1, math.ceil(window - (now - row.window_start).total_seconds()))
        db.session.commit()
        return False, left
    row.failures = (row.failures or 0) + 1
    db.session.commit()
    return True, 0


def reset():
    """Forget every in-memory count (used by the tests)."""
    with _lock:
        _hits.clear()


def _wants_json():
    return request.is_json or "X-CSRF-Token" in request.headers or request.path == "/interview/submit" \
        or "application/json" in request.headers.get("Accept", "")


def _wait_text(seconds):
    if seconds < 60:
        return f"{seconds} second{'' if seconds == 1 else 's'}"
    minutes = math.ceil(seconds / 60)
    return f"{minutes} minute{'' if minutes == 1 else 's'}"


def _limited(seconds, what):
    """A calm, helpful 429 response: it says what happened, how long to wait, and that nothing was lost."""
    user = session.get("user_id") and not session.get("is_admin")
    in_interview = bool(user and request.path.startswith(("/interview", "/practice")))
    message = f"{what} Please wait {_wait_text(seconds)} and try again."
    if _wants_json():
        response = jsonify({"error": "rate_limited", "message": message, "retry_after": seconds,
                            "progress_saved": in_interview})
        response.status_code = 429
    else:
        back = "/interview" if in_interview else ("/admin" if session.get("is_admin") else ("/dashboard" if user else "/"))
        response = make_response(render_template(
            "error.html", code=429, title="You're going a little fast", eyebrow="Please slow down", icon="bi-hourglass-split",
            message=message, notice=("Your interview is safe and this did not use any of your attempts." if in_interview else None),
            in_interview=False, back_url=back, reference=None), 429)
    response.headers["Retry-After"] = str(seconds)
    return response


def init_rate_limits(app):
    @app.before_request
    def enforce_rate_limits():
        """A problem inside the limiter itself must never break the app: on any error the request simply goes through."""
        try:
            return _check()
        except Exception as err:
            try:
                db.session.rollback()
            except Exception:
                pass
            print(f"[RATE LIMIT] skipped because of an internal error: {err}")
            return None

    def _check():
        forced = app.config.get("RATE_LIMIT_ENABLED")                    # None = use the environment and the admin switch
        if forced is False or os.environ.get("RATE_LIMITS_ENABLED", "true").strip().lower() in ("0", "false", "no", "off"):
            return None
        from MODULES.LAYER_2_DATA_PERSISTENCE.models import get_settings
        if forced is not True and not get_settings().enable_rate_limits:
            return None                                                    # the administrator switched it off in Settings
        path = request.path
        if path in EXEMPT_PATHS or path.startswith(EXEMPT_PREFIXES):
            return None
        if session.get("is_admin"):
            return None                                   # the administrator is never limited
        user_id = session.get("user_id")
        me = f"u{user_id}" if user_id else f"ip{request.remote_addr or 'unknown'}"

        ok, wait = allow(f"all:{me}", *LIMITS["user" if user_id else "anon"])
        if not ok:
            return _limited(wait, "You are sending requests very quickly.")
        if not user_id:
            return None

        if request.method == "POST" and path in AI_PATHS:
            ok, wait = allow(f"ai:{me}", *LIMITS["ai"])
            if not ok:
                return _limited(wait, "Answers are being sent faster than the AI examiner can read them.")
        elif path == "/interview-result":
            ok, wait = allow(f"res:{me}", *LIMITS["result"])
            if not ok:
                return _limited(wait, "Your result is already being prepared.")
        elif path == "/interview/violation":
            ok, wait = allow(f"vio:{me}", *LIMITS["violation"])
            if not ok:
                return _limited(wait, "Too many reports were sent at once.")
        elif request.method == "POST" and path == "/dashboard/update-resume":
            ok, wait = consume(f"rl:resume:{user_id}", *LIMITS["resume"])
            if not ok:
                return _limited(wait, "You have uploaded several resumes in the last hour.")
        elif request.method == "POST" and path == "/practice-start":
            ok, wait = consume(f"rl:practice:{user_id}", *LIMITS["practice"])
            if not ok:
                return _limited(wait, "You have started many practice sessions in the last hour.")
        return None
