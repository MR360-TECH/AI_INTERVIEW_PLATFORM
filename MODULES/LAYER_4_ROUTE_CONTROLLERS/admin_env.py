import os
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, session, jsonify, send_from_directory, current_app
from sqlalchemy import func
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import db
from MODULES.LAYER_2_DATA_PERSISTENCE.models import (
    User,
    InterviewResult,
    InterviewProgress,
    AdminSettings,
    get_settings,
    invalidate_settings_cache,
    resume_file_exists,
    INTEGRITY_SWITCHES,
    InterviewViolation,
    ResourceBookmark,
    Feedback
)
from MODULES.LAYER_3_BUSINESS_SERVICES.mailer import send_slot_unlocked_email

admin_bp = Blueprint('admin_bp', __name__)


@admin_bp.route("/admin/db-check")
def db_check():
    if not session.get("is_admin"):
        return redirect("/login")
    try:
        engine = db.engine
        dialect_name = engine.dialect.name
        user_count = User.query.count()
        result_count = InterviewResult.query.count()
        return jsonify({
            "status": "connected",
            "database_engine": dialect_name,
            "is_postgres": bool("postgres" in dialect_name),
            "users_in_db": user_count,
            "interview_results_in_db": result_count
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_bp.route("/admin")
def admin():
    if "user_id" in session:
        return redirect("/dashboard")
    if not session.get("is_admin"):
        return redirect("/login")

    today = date.today()
    current_month = today.month
    current_year = today.year

    filter_type = request.args.get("filter", "all")

    all_results = db.session.query(InterviewResult, User).join(User, InterviewResult.user_id == User.id)\
        .filter(~InterviewResult.status.like('%Practice%'))\
        .order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).all()

    today_count = sum(1 for r, u in all_results if r.interview_datetime and r.interview_datetime.date() == today)
    month_count = sum(1 for r, u in all_results if r.interview_datetime and r.interview_datetime.year == current_year and r.interview_datetime.month == current_month)
    total_count = len(all_results)
    selected_count = sum(1 for r, u in all_results if (r.status in ["Selected", "PASS"] or (r.status and "WELL DONE" in r.status)) and not r.is_terminated)
    rejected_count = sum(1 for r, u in all_results if (r.status in ["Rejected", "FAIL"] or r.is_terminated or "Terminated" in (r.status or "")))

    if filter_type == "today":
        results = [(r, u) for r, u in all_results if r.interview_datetime and r.interview_datetime.date() == today]
    elif filter_type == "month":
        results = [(r, u) for r, u in all_results if r.interview_datetime and r.interview_datetime.year == current_year and r.interview_datetime.month == current_month]
    elif filter_type == "selected":
        results = [(r, u) for r, u in all_results if (r.status in ["Selected", "PASS"] or (r.status and "WELL DONE" in r.status)) and not r.is_terminated]
    elif filter_type == "rejected":
        results = [(r, u) for r, u in all_results if (r.status in ["Rejected", "FAIL"] or r.is_terminated or "Terminated" in (r.status or ""))]
    else:
        results = all_results

    settings = get_settings()

    all_users = User.query.all()
    user_attempt_counts = {u.id: u.get_attempts_used() for u in all_users}

    return render_template(
        "admin.html",
        results=results,
        today_count=today_count,
        month_count=month_count,
        total_count=total_count,
        selected_count=selected_count,
        rejected_count=rejected_count,
        filter_type=filter_type,
        settings=settings,
        user_attempt_counts=user_attempt_counts
    )


@admin_bp.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if not session.get("is_admin"):
        return redirect("/login")

    if request.method == "POST":
        # Always work directly with the DB row — never modify the cached snapshot
        db_settings = AdminSettings.query.first()
        if not db_settings:
            # Row doesn't exist yet — create it with defaults
            db_settings = AdminSettings(
                min_questions=3,
                max_questions=8,
                pass_score=3,
                default_difficulty='student',
                question_timer_seconds=90,
                enable_attempt_limits=True,
                default_allowed_interviews=2,
                enable_warning_strikes=True,
                enable_feedback_emails=True
            )
            db.session.add(db_settings)

        try:
            db_settings.min_questions = int(float(request.form.get("min_questions", 3)))
        except (ValueError, TypeError):
            pass
        try:
            db_settings.max_questions = int(float(request.form.get("max_questions", 8)))
        except (ValueError, TypeError):
            pass
        try:
            db_settings.pass_score = int(float(request.form.get("pass_score", 3)))
        except (ValueError, TypeError):
            pass
        db_settings.default_difficulty = request.form.get("default_difficulty", "student")
        if "question_timer_seconds" in request.form:
            try:
                db_settings.question_timer_seconds = int(float(request.form["question_timer_seconds"]))
            except (ValueError, TypeError):
                pass

        # Checkboxes: present = True, absent = False
        db_settings.enable_attempt_limits = bool(request.form.get("enable_attempt_limits"))
        db_settings.enable_warning_strikes = bool(request.form.get("enable_warning_strikes"))
        db_settings.enable_feedback_emails = bool(request.form.get("enable_feedback_emails"))
        # Integrity switches (only when the grouped form was submitted, so older posts never switch them off by accident)
        if request.form.get("integrity_form"):
            for switch in INTEGRITY_SWITCHES:
                setattr(db_settings, switch, bool(request.form.get(switch)))
            db_settings.enable_rate_limits = bool(request.form.get("enable_rate_limits"))
            try:
                db_settings.max_strikes = max(1, min(5, int(float(request.form.get("max_strikes", 2)))))
            except (ValueError, TypeError):
                db_settings.max_strikes = 2
        if "default_allowed_interviews" in request.form:
            try:
                db_settings.default_allowed_interviews = int(float(request.form["default_allowed_interviews"]))
            except (ValueError, TypeError):
                pass

        # The form limits the numbers, but the server enforces the same limits (a crafted request cannot save nonsense).
        def clamp(value, low, high, default):
            return default if value is None else max(low, min(high, value))

        # Interview bounds stay consistent: 1 <= min <= max <= 20.
        db_settings.min_questions = clamp(db_settings.min_questions, 1, 20, 3)
        db_settings.max_questions = max(db_settings.min_questions, clamp(db_settings.max_questions, 1, 20, 8))
        db_settings.pass_score = clamp(db_settings.pass_score, 0, 10, 3)
        db_settings.question_timer_seconds = clamp(db_settings.question_timer_seconds, 20, 300, 90)
        db_settings.default_allowed_interviews = clamp(db_settings.default_allowed_interviews, 1, 10, 2)
        if db_settings.default_difficulty not in ("student", "mid", "senior"):
            db_settings.default_difficulty = "student"

        db.session.commit()

        # ✅ Force-clear the in-memory cache so the new settings apply immediately
        invalidate_settings_cache()

        return redirect("/admin/settings?saved=1")

    settings = get_settings()
    return render_template("admin_settings.html", settings=settings, saved=request.args.get("saved"))


@admin_bp.route("/admin/guide")
@admin_bp.route("/admin/info")
def admin_guide():
    if not session.get("is_admin"):
        return redirect("/login")
    settings = get_settings()
    return render_template("admin_guide.html", settings=settings)


@admin_bp.route("/admin/delete/<int:result_id>", methods=["POST"])
def delete_result(result_id):
    if not session.get("is_admin"):
        return redirect("/login")

    record = db.session.get(InterviewResult, result_id)
    if record:
        InterviewViolation.query.filter_by(result_id=result_id).delete()
        db.session.delete(record)
        db.session.commit()

    return redirect("/admin")


@admin_bp.route("/admin/user/<int:user_id>/unlock-attempt", methods=["POST"])
def admin_unlock_attempt(user_id):
    if not session.get("is_admin"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user_obj = db.session.get(User, user_id)
    if not user_obj:
        return jsonify({"status": "error", "message": "User not found"}), 404

    settings = get_settings()
    default_allowed = settings.default_allowed_interviews or 2

    # Count actual token-consuming attempts (excludes Practice, Abandoned)
    attempts_used = user_obj.get_attempts_used()

    current_extra = user_obj.extra_allowed_interviews or 0
    # Ensure extra grants at least +1 usable token beyond whatever attempts were consumed
    required_extra = max(current_extra + 1, attempts_used - default_allowed + 1)
    user_obj.extra_allowed_interviews = max(0, required_extra)
    db.session.commit()

    allowed_total = default_allowed + user_obj.extra_allowed_interviews
    remaining_tokens = max(0, allowed_total - attempts_used)

    if user_obj.email:
        try:
            send_slot_unlocked_email(user_obj.email, user_obj.full_name)
        except Exception as mail_err:
            print(f"[MAIL ERROR] {mail_err}")

    return jsonify({
        "status": "success",
        "message": f"Successfully granted 1 interview token for {user_obj.full_name or 'candidate'}.",
        "new_extra": user_obj.extra_allowed_interviews,
        "remaining_tokens": remaining_tokens,
        "allowed_total": allowed_total,
        "attempts_used": attempts_used
    })


@admin_bp.route("/admin/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if not session.get("is_admin"):
        return redirect("/login")

    user = db.session.get(User, user_id)
    resume_path = None
    if user and user.resume_filename:
        resume_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), user.resume_filename)

    InterviewViolation.query.filter_by(user_id=user_id).delete()
    ResourceBookmark.query.filter_by(user_id=user_id).delete()
    Feedback.query.filter_by(user_id=user_id).update({"user_id": None})      # keep the message, drop the link
    InterviewResult.query.filter_by(user_id=user_id).delete()
    InterviewProgress.query.filter_by(user_id=user_id).delete()
    if user:
        db.session.delete(user)
    db.session.commit()

    if resume_path and os.path.isfile(resume_path):
        try:
            os.remove(resume_path)
        except OSError as e:
            print(f"Error removing resume file of deleted user: {e}")

    # Only allow redirects to local admin pages (no open redirect)
    next_url = request.args.get("next") or request.form.get("next") or "/admin"
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/admin"
    return redirect(next_url)


USERS_PER_PAGE = 20
USER_FILTERS = ("all", "locked", "no_resume", "google", "never_assessed")
USER_SORTS = ("newest", "oldest", "name", "attempts")


def _is_recommended(result, settings):
    """Same rule the dashboard uses: at or above the passing score and not ended by proctoring."""
    try:
        return (not result.is_terminated and "Terminated" not in (result.status or "")
                and float(result.score) >= float(settings.pass_score or 0))
    except (TypeError, ValueError):
        return False


@admin_bp.route("/admin/users")
def admin_users():
    if not session.get("is_admin"):
        return redirect("/login")

    q = request.args.get("q", "").strip()
    filter_type = request.args.get("filter", "all")
    sort = request.args.get("sort", "newest")
    if filter_type not in USER_FILTERS:
        filter_type = "all"
    if sort not in USER_SORTS:
        sort = "newest"
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    settings = get_settings()
    query = User.query
    if q:
        query = query.filter(
            (User.full_name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")) |
            (User.course.ilike(f"%{q}%")) | (User.skills.ilike(f"%{q}%")))
    users = query.order_by(User.registered_at.desc()).all()

    # newest assessment (practice excluded) and the number of assessments per candidate
    latest, taken = {}, {}
    for r in (InterviewResult.query.filter(~InterviewResult.status.like('%Practice%'))
              .order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).all()):
        latest.setdefault(r.user_id, r)
        taken[r.user_id] = taken.get(r.user_id, 0) + 1

    default_allowed = settings.default_allowed_interviews or 2
    rows = []
    for u in users:
        used = u.get_attempts_used()
        allowed = default_allowed + (u.extra_allowed_interviews or 0)
        remaining = allowed - used
        last = latest.get(u.id)
        rows.append({
            "user": u, "used": used,
            "locked": bool(settings.enable_attempt_limits and remaining <= 0),
            "has_resume": bool(u.resume_filename or u.resume_text),
            "taken": taken.get(u.id, 0), "last": last,
            "last_ok": bool(last and _is_recommended(last, settings)),
        })

    week_ago = datetime.utcnow() - timedelta(days=7)
    stats = {
        "total": len(rows),
        "locked": sum(1 for r in rows if r["locked"]),
        "new_week": sum(1 for r in rows if r["user"].registered_at and r["user"].registered_at >= week_ago),
        "with_resume": sum(1 for r in rows if r["has_resume"]),
        "assessed": sum(1 for r in rows if r["taken"]),
    }

    if filter_type == "locked":
        rows = [r for r in rows if r["locked"]]
    elif filter_type == "no_resume":
        rows = [r for r in rows if not r["has_resume"]]
    elif filter_type == "google":
        rows = [r for r in rows if r["user"].auth_provider == "google"]
    elif filter_type == "never_assessed":
        rows = [r for r in rows if not r["taken"]]

    if sort == "oldest":
        rows.sort(key=lambda r: r["user"].registered_at or datetime.min)
    elif sort == "name":
        rows.sort(key=lambda r: (r["user"].full_name or "").lower())
    elif sort == "attempts":
        rows.sort(key=lambda r: r["used"], reverse=True)

    total_filtered = len(rows)
    pages = max(1, -(-total_filtered // USERS_PER_PAGE))
    page = min(page, pages)
    rows = rows[(page - 1) * USERS_PER_PAGE: page * USERS_PER_PAGE]

    return render_template("admin_users.html", rows=rows, users=[r["user"] for r in rows], q=q, settings=settings, stats=stats,
                           filter_type=filter_type, sort=sort, page=page, pages=pages, total_filtered=total_filtered,
                           now=datetime.utcnow())


@admin_bp.route("/admin/user/<int:user_id>")
def admin_user_detail(user_id):
    if not session.get("is_admin"):
        return redirect("/login")

    user = db.session.get(User, user_id)
    if not user:
        return redirect("/admin")

    interviews = InterviewResult.query.filter(
        InterviewResult.user_id == user_id,
        ~InterviewResult.status.like('%Practice%')
    ).order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).all()

    settings = get_settings()
    attempts_used = user.get_attempts_used()
    extra_granted = user.extra_allowed_interviews or 0
    allowed_total = (settings.default_allowed_interviews or 2) + extra_granted
    remaining_tokens = max(0, allowed_total - attempts_used)
    is_locked = bool(settings.enable_attempt_limits and remaining_tokens <= 0)

    return render_template(
        "admin_user_detail.html",
        user=user,
        interviews=interviews,
        settings=settings,
        attempts_used=attempts_used,
        extra_granted=extra_granted,
        allowed_total=allowed_total,
        remaining_tokens=remaining_tokens,
        is_locked=is_locked,
        resume_file_exists=resume_file_exists(user)
    )


@admin_bp.route("/admin/user/<int:user_id>/resume")
def admin_view_user_resume(user_id):
    if not session.get("is_admin"):
        return redirect("/login")
    user = db.session.get(User, user_id)
    if not user or not resume_file_exists(user):
        return redirect(f"/admin/user/{user_id}")
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, user.resume_filename)


@admin_bp.route("/admin/interview/<int:result_id>")
def admin_interview_detail(result_id):
    if not session.get("is_admin"):
        return redirect("/login")

    result = db.session.get(InterviewResult, result_id)
    if not result:
        return redirect("/admin")

    candidate = db.session.get(User, result.user_id)
    settings = get_settings()

    try:
        score_percent = min(int((float(result.score) / 10) * 100), 100)
    except (TypeError, ValueError):
        score_percent = 0

    others, attempts_used, allowed_total, is_locked = [], 0, 0, False
    if candidate:
        others = (InterviewResult.query
                  .filter(InterviewResult.user_id == candidate.id, InterviewResult.id != result.id,
                          ~InterviewResult.status.like('%Practice%'))
                  .order_by(InterviewResult.interview_datetime.desc(), InterviewResult.id.desc()).all())
        attempts_used = candidate.get_attempts_used()
        allowed_total = (settings.default_allowed_interviews or 2) + (candidate.extra_allowed_interviews or 0)
        is_locked = bool(settings.enable_attempt_limits and attempts_used >= allowed_total)

    terminated = bool(result.is_terminated or "Terminated" in (result.status or ""))
    paragraphs = [p.strip() for p in (result.summary or "").split("\n") if p.strip()]
    violations = []
    if settings.proctor_integrity_log:
        violations = (InterviewViolation.query.filter_by(result_id=result.id)
                      .order_by(InterviewViolation.created_at, InterviewViolation.id).all())

    return render_template("admin_interview_detail.html", result=result, candidate=candidate, score_percent=score_percent,
                           resume_file_exists=resume_file_exists(candidate), settings=settings, others=others,
                           recommended=_is_recommended(result, settings), terminated=terminated, paragraphs=paragraphs,
                           attempts_used=attempts_used, allowed_total=allowed_total, is_locked=is_locked,
                           violations=violations, strike_count=sum(1 for v in violations if v.strike_no),
                           flag_count=sum(1 for v in violations if not v.strike_no),
                           other_ok={o.id: _is_recommended(o, settings) for o in others})


# ══════════════════════════════════════════════════════════════════════════════
# LINK HEALTH (admin only): the only place the "last checked" dates are shown
# ══════════════════════════════════════════════════════════════════════════════

LINK_FILTERS = ("all", "broken", "blocked", "unchecked", "hidden")


@admin_bp.route("/admin/links")
def admin_links():
    if not session.get("is_admin"):
        return redirect("/login")
    from MODULES.LAYER_4_ROUTE_CONTROLLERS.resources import LIBRARY
    from MODULES.LAYER_2_DATA_PERSISTENCE.models import LinkCheck

    filter_type = request.args.get("filter", "all")
    if filter_type not in LINK_FILTERS:
        filter_type = "all"
    checks = {c.url: c for c in LinkCheck.query.all()}
    rows = [{"item": i, "check": checks.get(i["url"])} for i in LIBRARY]

    stats = {
        "total": len(rows),
        "ok": sum(1 for r in rows if r["check"] and r["check"].kind == "ok"),
        "blocked": sum(1 for r in rows if r["check"] and r["check"].kind == "blocked"),
        "broken": sum(1 for r in rows if r["check"] and r["check"].kind == "broken"),
        "unchecked": sum(1 for r in rows if not r["check"] or not r["check"].checked_at),
        "hidden": sum(1 for r in rows if r["check"] and r["check"].hidden),
    }
    times = [r["check"].checked_at for r in rows if r["check"] and r["check"].checked_at]
    last_run = max(times) if times else None

    if filter_type == "broken":
        rows = [r for r in rows if r["check"] and r["check"].kind == "broken"]
    elif filter_type == "blocked":
        rows = [r for r in rows if r["check"] and r["check"].kind == "blocked"]
    elif filter_type == "unchecked":
        rows = [r for r in rows if not r["check"] or not r["check"].checked_at]
    elif filter_type == "hidden":
        rows = [r for r in rows if r["check"] and r["check"].hidden]

    progress, running = 0, False
    started = request.args.get("started", "")
    if started.isdigit():
        since = datetime.utcfromtimestamp(int(started))
        progress = sum(1 for c in checks.values() if c.checked_at and c.checked_at >= since)
        running = progress < stats["total"] and (datetime.utcnow() - since).total_seconds() < 240

    return render_template("admin_links.html", rows=rows, stats=stats, last_run=last_run, filter_type=filter_type,
                           running=running, progress=progress, busy=request.args.get("busy") == "1")


@admin_bp.route("/admin/links/check", methods=["POST"])
def admin_links_check():
    if not session.get("is_admin"):
        return redirect("/login")
    import time
    from MODULES.LAYER_4_ROUTE_CONTROLLERS.resources import LIBRARY
    from MODULES.LAYER_3_BUSINESS_SERVICES.link_checker import start_check
    started = int(time.time())
    if not start_check(current_app._get_current_object(), [i["url"] for i in LIBRARY]):
        return redirect("/admin/links?busy=1")
    return redirect(f"/admin/links?started={started}")


@admin_bp.route("/admin/links/hide", methods=["POST"])
def admin_links_hide():
    """Hides (or shows again) one library link for candidates."""
    if not session.get("is_admin"):
        return redirect("/login")
    from MODULES.LAYER_4_ROUTE_CONTROLLERS.resources import LIBRARY_URLS
    from MODULES.LAYER_2_DATA_PERSISTENCE.models import LinkCheck
    url = request.form.get("url", "")
    if url in LIBRARY_URLS:
        row = LinkCheck.query.filter_by(url=url).first() or LinkCheck(url=url)
        row.hidden = not bool(row.hidden)
        db.session.add(row)
        db.session.commit()
    filter_type = request.form.get("filter", "all")
    return redirect(f"/admin/links?filter={filter_type if filter_type in LINK_FILTERS else 'all'}")
