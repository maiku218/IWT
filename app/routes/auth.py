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

from app import db
from app.models import User, AuditLog

bp = Blueprint("auth", __name__, url_prefix="")


def _audit(action, target_type=None, target_id=None, details=None):
    entry = AuditLog(
        actor_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.session.add(entry)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        if current_user.is_pending():
            return redirect(url_for("auth.account_pending"))
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username_or_email = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username_or_email or not password:
            flash("Please enter both username/email and password.", "error")
            return render_template("auth/login.html"), 400

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid username/email or password.", "error")
            _audit("login_failed", target_type="user", details=username_or_email)
            db.session.commit()
            return render_template("auth/login.html"), 401

        if user.role == "admin":
            flash("Administrators must use the admin login page.", "error")
            return render_template("auth/login.html"), 403

        if not user.is_active:
            flash("Your account has been deactivated. Contact an administrator.", "error")
            return render_template("auth/login.html"), 403

        if user.is_pending():
            flash("Your account is waiting for administrator approval.", "info")
            return render_template("auth/login.html"), 403

        if user.is_rejected():
            msg = user.rejection_reason or "Your account has been rejected."
            flash(f"Login blocked: {msg}", "error")
            return render_template("auth/login.html"), 403

        if user.is_suspended():
            flash("Your account has been suspended. Contact an administrator.", "error")
            return render_template("auth/login.html"), 403

        if not user.is_approved():
            flash("Your account is not approved for access.", "error")
            return render_template("auth/login.html"), 403

        login_user(user, remember=True)
        _audit("login", target_type="user", target_id=user.id, details=f"{user.full_name} logged in")
        db.session.commit()
        flash(f"Welcome back, {user.full_name}.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    name = current_user.full_name
    role = current_user.role
    _audit("logout", target_type="user", target_id=current_user.id, details=f"{name} logged out")
    db.session.commit()
    logout_user()
    flash(f"Goodbye, {name}. You have been logged out.", "info")
    if role == "admin":
        return redirect(url_for("admin.login"))
    return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not full_name or not username or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template("auth/register.html"), 400

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html"), 400

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("auth/register.html"), 400

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return render_template("auth/register.html"), 400

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "error")
            return render_template("auth/register.html"), 400

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
            "register",
            target_type="user",
            target_id=user.id,
            details=f"New intern registration: {full_name} ({username})",
        )
        db.session.commit()

        # Log the new (pending) user in so the pending page can show their info.
        login_user(user)
        flash("Registration submitted. Awaiting administrator approval.", "success")
        return redirect(url_for("auth.account_pending"))

    return render_template("auth/register.html")


@bp.route("/account/pending")
def account_pending():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    return render_template("auth/pending.html")


@bp.route("/account/status")
@login_required
def account_status():
    if current_user.role == "admin":
        return jsonify({"role": "admin", "status": current_user.account_status})
    return jsonify(
        {
            "role": current_user.role,
            "status": current_user.account_status,
            "full_name": current_user.full_name,
            "username": current_user.username,
            "email": current_user.email,
            "registered_at": current_user.registered_at.isoformat()
            if current_user.registered_at
            else None,
            "rejection_reason": current_user.rejection_reason,
        }
    )
