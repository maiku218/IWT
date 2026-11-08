from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import login_required, current_user
from app import db
from app.models import WorkLog
from app.routes.helpers import admin_required, get_work_log
from datetime import datetime, time

bp = Blueprint("work_logs", __name__, url_prefix="/work-logs")

CATEGORIES = [
    "Technical Support",
    "Troubleshooting",
    "Documentation",
    "Research",
    "Administrative Work",
    "Software Development",
    "Other",
]

STATUSES = ["Completed", "Ongoing", "Pending"]

REQUIRED_FIELDS = ["work_date", "task_title", "description", "category", "status"]


def validate_work_log_data(data, is_update=False):
    errors = {}
    for field in REQUIRED_FIELDS:
        value = (data.get(field) or "").strip()
        if not value:
            errors[field] = f"{field.replace('_', ' ').title()} is required."

    work_date_str = (data.get("work_date") or "").strip()
    if work_date_str:
        try:
            datetime.strptime(work_date_str, "%Y-%m-%d").date()
        except ValueError:
            errors["work_date"] = "Please enter a valid date."

    category = (data.get("category") or "").strip()
    if category and category not in CATEGORIES:
        errors["category"] = "Invalid category selected."

    status = (data.get("status") or "").strip()
    if status and status not in STATUSES:
        errors["status"] = "Invalid status selected."

    start_time_str = (data.get("start_time") or "").strip()
    end_time_str = (data.get("end_time") or "").strip()
    start_time = None
    end_time = None
    if start_time_str:
        try:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
        except ValueError:
            errors["start_time"] = "Invalid start time."
    if end_time_str:
        try:
            end_time = datetime.strptime(end_time_str, "%H:%M").time()
        except ValueError:
            errors["end_time"] = "Invalid end time."
    if start_time and end_time and end_time <= start_time:
        errors["end_time"] = "End time must be after start time."

    return errors, {
        "task_title": (data.get("task_title") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "work_date": datetime.strptime(work_date_str, "%Y-%m-%d").date() if work_date_str else None,
        "start_time": start_time,
        "end_time": end_time,
        "category": category,
        "status": status,
    }


@bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    search = (request.args.get("search") or "").strip()
    category = (request.args.get("category") or "").strip()
    status = (request.args.get("status") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()

    query = WorkLog.query.filter_by(user_id=current_user.id)

    if search:
        like = f"%{search}%"
        query = query.filter(
            (WorkLog.task_title.ilike(like)) | (WorkLog.description.ilike(like))
        )
    if category:
        query = query.filter_by(category=category)
    if status:
        query = query.filter_by(status=status)
    if date_from:
        try:
            query = query.filter(WorkLog.work_date >= datetime.strptime(date_from, "%Y-%m-%d").date())
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(WorkLog.work_date <= datetime.strptime(date_to, "%Y-%m-%d").date())
        except ValueError:
            pass

    query = query.order_by(WorkLog.work_date.desc(), WorkLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=15, error_out=False)

    return render_template(
        "work_logs/index.html",
        logs=pagination.items,
        pagination=pagination,
        search=search,
        category=category,
        status=status,
        date_from=date_from,
        date_to=date_to,
        categories=CATEGORIES,
        statuses=STATUSES,
    )


@bp.route("/", methods=["POST"])
@login_required
def create():
    data = request.form.to_dict()
    errors, values = validate_work_log_data(data)

    if errors:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"errors": errors}), 400
        for field, msg in errors.items():
            flash(f"{msg}", "error")
        return redirect(url_for("work_logs.index"))

    log = WorkLog(
        user_id=current_user.id,
        task_title=values["task_title"],
        description=values["description"],
        work_date=values["work_date"],
        start_time=values["start_time"],
        end_time=values["end_time"],
        category=values["category"],
        status=values["status"],
    )
    db.session.add(log)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"message": "Work log created.", "log": log.to_dict()}), 201

    flash("Work log added successfully.", "success")
    return redirect(url_for("work_logs.index"))


@bp.route("/<int:log_id>")
@login_required
def view(log_id):
    log = get_work_log(log_id)
    return jsonify({"log": log.to_dict()})


@bp.route("/<int:log_id>/edit", methods=["GET", "POST"])
@login_required
def edit(log_id):
    log = get_work_log(log_id)

    if request.method == "GET":
        return jsonify({"log": log.to_dict()})

    data = request.form.to_dict()
    errors, values = validate_work_log_data(data)

    if errors:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"errors": errors}), 400
        for field, msg in errors.items():
            flash(f"{msg}", "error")
        return redirect(url_for("work_logs.index"))

    log.task_title = values["task_title"]
    log.description = values["description"]
    log.work_date = values["work_date"]
    log.start_time = values["start_time"]
    log.end_time = values["end_time"]
    log.category = values["category"]
    log.status = values["status"]
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"message": "Work log updated.", "log": log.to_dict()})

    flash("Work log updated successfully.", "success")
    return redirect(url_for("work_logs.index"))


@bp.route("/<int:log_id>/delete", methods=["POST"])
@login_required
def delete(log_id):
    log = get_work_log(log_id)
    title = log.task_title
    db.session.delete(log)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"message": f"Work log '{title}' deleted."})

    flash(f"Work log '{title}' deleted successfully.", "success")
    return redirect(url_for("work_logs.index"))


@bp.route("/<int:log_id>/status", methods=["POST"])
@login_required
def update_status(log_id):
    log = get_work_log(log_id)
    status = (request.form.get("status") or request.json.get("status") if request.is_json else None) or ""
    status = status.strip()

    if status not in STATUSES:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"error": "Invalid status."}), 400
        flash("Invalid status.", "error")
        return redirect(url_for("work_logs.index"))

    log.status = status
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"message": "Status updated.", "log": log.to_dict()})

    flash("Status updated successfully.", "success")
    return redirect(url_for("work_logs.index"))
