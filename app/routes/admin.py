from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func, extract
from datetime import date, datetime

from app import db
from app.models import User, WorkLog, AuditLog
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


def _audit(action, target_type=None, target_id=None, details=None):
    entry = AuditLog(
        actor_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.session.add(entry)


# ---------------------------------------------------------------- Admin Login
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username_or_email = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username_or_email or not password:
            flash("Please enter both username/email and password.", "error")
            return render_template("admin/login.html"), 400

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid administrator credentials.", "error")
            _audit("admin_login_failed", target_type="user", details=username_or_email)
            db.session.commit()
            return render_template("admin/login.html"), 401

        if user.role != "admin":
            flash("This account is not an administrator account.", "error")
            return render_template("admin/login.html"), 403

        if not user.is_active:
            flash("This administrator account has been deactivated.", "error")
            return render_template("admin/login.html"), 403

        login_user(user, remember=True)
        _audit(
            "admin_login",
            target_type="user",
            target_id=user.id,
            details=f"Admin {user.full_name} logged in",
        )
        db.session.commit()
        flash(f"Welcome back, {user.full_name}.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/login.html")


@bp.route("/logout")
@login_required
def logout():
    name = current_user.full_name
    _audit(
        "admin_logout",
        target_type="user",
        target_id=current_user.id,
        details=f"Admin {name} logged out",
    )
    db.session.commit()
    logout_user()
    flash(f"Goodbye, {name}. You have been logged out.", "info")
    return redirect(url_for("admin.login"))


# ------------------------------------------------------------- Admin Dashboard
@bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    total_interns = User.query.filter_by(role="intern").count()
    pending_approvals = User.query.filter_by(role="intern", account_status="pending").count()
    approved_interns = User.query.filter_by(role="intern", account_status="approved").count()
    rejected_applications = User.query.filter_by(role="intern", account_status="rejected").count()

    recent_registrations = (
        User.query.filter_by(role="intern")
        .order_by(User.registered_at.desc())
        .limit(10)
        .all()
    )

    total_logs = WorkLog.query.count()
    completed_tasks = WorkLog.query.filter_by(status="Completed").count()

    return render_template(
        "admin/dashboard.html",
        total_interns=total_interns,
        pending_approvals=pending_approvals,
        approved_interns=approved_interns,
        rejected_applications=rejected_applications,
        total_logs=total_logs,
        completed_tasks=completed_tasks,
        recent_registrations=recent_registrations,
    )


# ---------------------------------------------------------- Pending Approvals
@bp.route("/approvals")
@login_required
@admin_required
def approvals():
    pending = (
        User.query.filter_by(role="intern", account_status="pending")
        .order_by(User.registered_at.asc())
        .all()
    )
    rejected = (
        User.query.filter_by(role="intern", account_status="rejected")
        .order_by(User.rejected_at.desc())
        .all()
    )
    return render_template("admin/approvals.html", pending=pending, rejected=rejected)


@bp.route("/approvals/<int:user_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve(user_id):
    user = User.query.filter_by(id=user_id, role="intern").first_or_404()
    if user.account_status != "pending":
        return jsonify({"error": "Only pending accounts can be approved."}), 400

    user.account_status = "approved"
    user.approved_at = datetime.utcnow()
    user.approved_by = current_user.id
    user.rejected_at = None
    user.rejection_reason = None
    db.session.commit()
    _audit(
        "approve_intern",
        target_type="user",
        target_id=user.id,
        details=f"Approved {user.full_name} ({user.username})",
    )
    db.session.commit()
    return jsonify({"message": f"{user.full_name} has been approved."})


@bp.route("/approvals/<int:user_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject(user_id):
    user = User.query.filter_by(id=user_id, role="intern").first_or_404()
    if user.account_status not in ("pending", "rejected"):
        return jsonify({"error": "Cannot reject this account."}), 400

    reason = (request.form.get("reason") or request.json.get("reason") if request.is_json else None) or ""
    reason = reason.strip()

    user.account_status = "rejected"
    user.rejected_at = datetime.utcnow()
    user.rejection_reason = reason or "No reason provided."
    user.approved_at = None
    user.approved_by = None
    db.session.commit()
    _audit(
        "reject_intern",
        target_type="user",
        target_id=user.id,
        details=f"Rejected {user.full_name} ({user.username}): {reason}",
    )
    db.session.commit()
    return jsonify({"message": f"{user.full_name} has been rejected."})


# ------------------------------------------------------------ Intern Management
@bp.route("/interns")
@login_required
@admin_required
def interns():
    interns = User.query.filter_by(role="intern").order_by(User.registered_at.desc()).all()
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
        account_status="pending",
        is_active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    _audit(
        "create_intern",
        target_type="user",
        target_id=user.id,
        details=f"Admin created intern {full_name} ({username})",
    )
    db.session.commit()
    flash(f"Intern account '{username}' created (pending approval).", "success")
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
                "account_status": user.account_status,
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
    _audit(
        "edit_intern",
        target_type="user",
        target_id=user.id,
        details=f"Edited intern {user.full_name} ({user.username})",
    )
    db.session.commit()
    return jsonify({"message": "Intern updated."})


@bp.route("/interns/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_intern(user_id):
    user = User.query.filter_by(id=user_id, role="intern").first_or_404()
    user.is_active = not user.is_active
    db.session.commit()
    _audit(
        "toggle_intern",
        target_type="user",
        target_id=user.id,
        details=f"{'Activated' if user.is_active else 'Deactivated'} {user.full_name}",
    )
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
    _audit(
        "reset_password",
        target_type="user",
        target_id=user.id,
        details=f"Reset password for {user.full_name} ({user.username})",
    )
    db.session.commit()
    return jsonify({"message": f"Password reset for {user.username}."})


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


# ------------------------------------------------------------------ Admin Reports
@bp.route("/reports")
@login_required
@admin_required
def reports():
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
        "admin/reports.html",
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


# ------------------------------------------------------------------- Admin Settings
@bp.route("/settings")
@login_required
@admin_required
def settings():
    return render_template("admin/settings.html")
