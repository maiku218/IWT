from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from app.models import User
from app.routes.helpers import admin_required

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
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
            return render_template("auth/login.html"), 401

        if not user.is_active:
            flash("This account has been deactivated. Contact an administrator.", "error")
            return render_template("auth/login.html"), 403

        login_user(user, remember=True)
        flash(f"Welcome back, {user.full_name}.", "success")

        next_page = request.args.get("next")
        if user.role == "admin":
            return redirect(next_page or url_for("admin.dashboard"))
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    name = current_user.full_name
    logout_user()
    flash(f"Goodbye, {name}. You have been logged out.", "info")
    return redirect(url_for("auth.login"))
