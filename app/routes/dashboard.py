from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    current_app,
)
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from datetime import date, datetime

from app import db
from app.models import User, WorkLog

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("/")
@login_required
def index():
    today = date.today().isoformat()
    return render_template("dashboard/index.html", today=today)


@bp.route("/api/stats")
@login_required
def stats():
    user_id = current_user.id
    base = WorkLog.query.filter_by(user_id=user_id)

    total_tasks = base.count()
    completed_tasks = base.filter_by(status="Completed").count()

    now = date.today()
    tasks_this_month = base.filter(
        extract("year", WorkLog.work_date) == now.year,
        extract("month", WorkLog.work_date) == now.month,
    ).count()

    return jsonify(
        {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "tasks_this_month": tasks_this_month,
        }
    )


@bp.route("/api/calendar-events")
@login_required
def calendar_events():
    start = request.args.get("start")
    end = request.args.get("end")

    query = WorkLog.query.filter_by(user_id=current_user.id)
    if start:
        query = query.filter(WorkLog.work_date >= datetime.strptime(start, "%Y-%m-%d").date())
    if end:
        query = query.filter(WorkLog.work_date <= datetime.strptime(end, "%Y-%m-%d").date())

    logs = query.all()
    events = []
    for log in logs:
        events.append(
            {
                "id": f"log-{log.id}",
                "title": log.task_title,
                "start": log.work_date.isoformat(),
                "allDay": True,
                "backgroundColor": category_color(log.category),
                "borderColor": category_color(log.category),
                "extendedProps": {
                    "category": log.category,
                    "status": log.status,
                    "workDate": log.work_date.isoformat(),
                },
            }
        )
    return jsonify(events)


@bp.route("/api/records")
@login_required
def records():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "date is required"}), 400

    try:
        work_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "invalid date format"}), 400

    logs = (
        WorkLog.query.filter_by(user_id=current_user.id, work_date=work_date)
        .order_by(WorkLog.created_at.desc())
        .all()
    )

    return jsonify(
        {
            "date": date_str,
            "count": len(logs),
            "records": [log.to_dict() for log in logs],
        }
    )


def category_color(category):
    colors = {
        "Technical Support": "#2563eb",
        "Troubleshooting": "#dc2626",
        "Documentation": "#059669",
        "Research": "#7c3aed",
        "Administrative Work": "#d97706",
        "Software Development": "#0891b2",
        "Other": "#6b7280",
    }
    return colors.get(category, "#6b7280")
