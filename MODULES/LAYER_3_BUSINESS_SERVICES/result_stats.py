"""How a stored assessment result is classified, and the figures of the admin Analytics page.

Pure functions over result rows: nothing here touches the database or Flask, so they are easy to test.
Practice results are never passed in (the caller leaves them out), and a result without a score is simply not averaged.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta

OUTCOMES = ("passed", "failed", "exited", "terminated", "other")
FINISHED = ("passed", "failed")          # an assessment that was completed to the end
WINDOWS = (7, 30, 90, 0)                 # days shown by the Analytics page; 0 = everything
DAILY_DAYS = 30                          # length of the per-day chart when the window is "everything"


def outcome_of(result):
    """'terminated', 'exited', 'passed', 'failed' or 'other'. The same rules the admin dashboard uses for its counters."""
    status = result.status or ""
    if result.is_terminated or "Terminated" in status:
        return "terminated"
    if status == "Exited (Incomplete)":
        return "exited"
    if status in ("Selected", "PASS") or "WELL DONE" in status:
        return "passed"
    if status in ("Rejected", "FAIL"):
        return "failed"
    return "other"


def _score(result):
    try:
        return float(result.score) if result.score is not None else None
    except (TypeError, ValueError):
        return None


def _domain_key(result):
    text = " ".join((result.domain or "").split())
    return text.lower() or "not given", (text or "Not given")


def summarise(rows, days=30, now=None):
    """rows: list of (InterviewResult, User). Returns the numbers behind the Analytics page for the last `days` days (0 = all)."""
    now = now or datetime.utcnow()
    since = now - timedelta(days=days) if days else None
    picked = [(r, u) for r, u in rows if since is None or (r.interview_datetime and r.interview_datetime >= since)]

    counts = Counter(outcome_of(r) for r, _u in picked)
    total = len(picked)
    finished = counts["passed"] + counts["failed"]
    scores = [s for r, _u in picked if outcome_of(r) in FINISHED for s in [_score(r)] if s is not None]

    def pct(part, whole):
        return round(100.0 * part / whole, 1) if whole else None

    # one bar per day: the chosen window, or the last 30 days when everything is shown
    span = days or DAILY_DAYS
    first_day = (now - timedelta(days=span - 1)).date()
    per_day = Counter(r.interview_datetime.date() for r, _u in picked if r.interview_datetime)
    daily = []
    for i in range(span):
        d = first_day + timedelta(days=i)
        daily.append({"date": d, "count": per_day.get(d, 0)})
    busiest = max(daily, key=lambda x: x["count"]) if daily and any(x["count"] for x in daily) else None

    # scores 0-1, 1-2 ... 9-10 (a 10 belongs to the last bar)
    histogram = [0] * 10
    for s in scores:
        histogram[min(9, max(0, int(s)))] += 1

    groups = defaultdict(lambda: {"label": "", "count": 0, "scores": [], "passed": 0, "finished": 0})
    for r, _u in picked:
        key, label = _domain_key(r)
        g = groups[key]
        g["label"] = g["label"] or label
        g["count"] += 1
        out = outcome_of(r)
        if out in FINISHED:
            g["finished"] += 1
            g["passed"] += out == "passed"
            s = _score(r)
            if s is not None:
                g["scores"].append(s)
    domains = sorted(groups.values(), key=lambda g: (-g["count"], g["label"].lower()))[:10]
    domain_rows = [{"label": g["label"], "count": g["count"],
                    "avg_score": round(sum(g["scores"]) / len(g["scores"]), 1) if g["scores"] else None,
                    "pass_rate": pct(g["passed"], g["finished"])} for g in domains]

    return {
        "days": days, "total": total, "counts": {k: counts[k] for k in OUTCOMES},
        "candidates": len({u.id for _r, u in picked}),
        "pass_rate": pct(counts["passed"], finished),
        "completion_rate": pct(finished, total),
        "exit_rate": pct(counts["exited"], total),
        "termination_rate": pct(counts["terminated"], total),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "mix": {k: pct(counts[k], total) or 0 for k in OUTCOMES},
        "daily": daily, "daily_max": max([x["count"] for x in daily] + [1]), "busiest": busiest,
        "histogram": histogram, "histogram_max": max(histogram + [1]),
        "domains": domain_rows,
    }
