"""Admin-only link checker for the preparation library.

Only URLs that are already in the catalog are ever fetched (never anything a user typed), and the result is stored in
the LinkCheck table so that only the admin sees when a link was last checked.
"""
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db
from MODULES.LAYER_2_DATA_PERSISTENCE.models import LinkCheck

USER_AGENT = "Mozilla/5.0 (compatible; LinkCheck/1.0)"
BLOCKED_CODES = {401, 403, 429, 999}      # the site refuses automated visitors: a person can usually still open it
_running = threading.Lock()


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def check_url(url, timeout=10):
    """Returns (status_code or None, kind) where kind is 'ok', 'blocked' or 'broken'."""
    last = (None, "broken", "no answer")
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, "ok", ""
        except urllib.error.HTTPError as e:
            kind = "blocked" if e.code in BLOCKED_CODES else "broken"
            last = (e.code, kind, f"HTTP {e.code}")
            if method == "HEAD" and e.code in (400, 403, 405, 501):
                continue                          # some servers refuse HEAD but accept GET
            return last
        except Exception as e:                    # DNS failure, timeout, TLS problem ...
            last = (None, "broken", type(e).__name__)
            if method == "HEAD":
                continue
    return last


def _store(app, url):
    status, kind, note = check_url(url)
    with app.app_context():
        row = LinkCheck.query.filter_by(url=url).first() or LinkCheck(url=url)
        row.status_code, row.kind, row.note, row.checked_at = status, kind, note[:120], _now()
        db.session.add(row)
        db.session.commit()


def start_check(app, urls):
    """Checks every URL in a background thread. Returns False when a run is already in progress."""
    if not _running.acquire(blocking=False):
        return False

    def work():
        try:
            with ThreadPoolExecutor(max_workers=10) as pool:
                list(pool.map(lambda u: _store(app, u), urls))
        finally:
            _running.release()

    threading.Thread(target=work, daemon=True).start()
    return True
