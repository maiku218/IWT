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
from werkzeug.security import generate_password_hash
from sqlalchemy import func, extract
from datetime import date, datetime

from app import db
from app.models import User, WorkLog
from app.routes.helpers import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

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


@bp.route("/")
@login_required
@admin_required
def dashboard():
    total_interns = User.query.filter_by(role="intern").count()
    total_logs = WorkLog.query.count()
    completed_tasks = WorkLog.query.filter_by(status="Completed").count()
    total_users = User.query.count()

    recent = (
        WorkLog.query.join(User, WorkLog.user_id == User.id)
        .order_by(WorkLog.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/index.html",
        total_interns=total_interns,
        total_logs=total_logs,
        completed_tasks=completed_tasks,
        total_users=total_users,
        recent=recent,
    )


@bp.route("/interns")
@login_required
@admin_required
def interns():
    interns = User.query.filter_by(role="intern").order_by(User.created_at.desc()).all()
    return render_template("admin/interns.html", interns=interns)


@bp.route("/interns", methods=["POST"])
@login_required
@admin_required
def create_intern():
    full_name = (request.form.get("full_name") or "").strip()
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    if not full_name or not username or not email or not password:
        flash("All fields are required.", "error")
        return redirect(url_for("admin.interns"))

    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "error")
        return redirect(url_for("admin.interns"))
    if User.query.filter_by(email=email).first():
        flash("Email already exists.", "error")
        return redirect(url_for("admin.interns"))

    user = User(
        full_name=full_name,
        username=username,
        email=email,
        role="intern",
        is_active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(f"Intern account '{username}' created successfully.", "success")
    return redirect(url_for("admin.interns"))


@bp.route("/interns/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_intern(user_id):
    user = User.query.filter_by(id=user_id, role="intern").first_or_404()

    if request.method == "GET":
        return jsonify(
            {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
            }
        )

    full_name = (request.form.get("full_name") or "").strip()
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()

    if not full_name or not username or not email:
        return jsonify({"error": "All fields are required."}), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != user.id:
        return jsonify({"error": "Username already exists."}), 400
    existing_email = User.query.filter_by(email=email).first()
    if existing_email and existing_email.id != user.id:
        return jsonify({"error": "Email already exists."}), 400

    user.full_name = full_name
    user.username = username
    user.email = email
    db.session.commit()
    return jsonify({"message": "Intern updated."})


@bp.route("/interns/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_intern(user_id):
    user = User.query.filter_by(id=user_id, role="intern").first_or_404()
    user.is_active = not user.is_active
    db.session.commit()
    status = "activated" if user.is_active else "deactivated"
    return jsonify({"message": f"Intern {status}.", "is_active": user.is_active})


@bp.route("/interns/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.filter_by(id=user_id, role="intern").first_or_404()
    new_password = request.form.get("new_password") or "Intern123!"
    user.set_password(new_password)
    db.session.commit()
    return jsonify({"message": f"Password reset for {user.username}."})


@bp.route("/logs")
@login_required
@admin_required
def logs():
    page = request.args.get("page", 1, type=int)
    intern_id = request.args.get("intern", type=int)
    category = (request.args.get("category") or "").strip()
    status = (request.args.get("status") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()

    query = WorkLog.query.join(User, WorkLog.user_id == User.id).filter(User.role == "intern")

    if intern_id:
        query = query.filter(WorkLog.user_id == intern_id)
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
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    interns = User.query.filter_by(role="intern").order_by(User.full_name.asc()).all()

    return render_template(
        "admin/logs.html",
        logs=pagination.items,
        pagination=pagination,
        interns=interns,
        intern_id=intern_id,
        category=category,
        status=status,
        date_from=date_from,
        date_to=date_to,
        categories=CATEGORIES,
        statuses=STATUSES,
    )


@bp.route("/interns/<int:user_id>/records")
@login_required
@admin_required
def intern_records(user_id):
    user = User.query.filter_by(id=user_id, role="intern").first_or_404()
    page = request.args.get("page", 1, type=int)
    logs = (
        WorkLog.query.filter_by(user_id=user_id)
        .order_by(WorkLog.work_date.desc(), WorkLog.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("admin/intern_records.html", intern=user, logs=logs)
