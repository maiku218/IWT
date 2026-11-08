from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import current_user

from app import db
from app.models import User
from app.routes.helpers import approved_intern_required

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/")
@approved_intern_required
def index():
    return render_template("settings/index.html")


@bp.route("/", methods=["POST"])
@approved_intern_required
def update_profile():
    full_name = (request.form.get("full_name") or "").strip()
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()

    if not full_name or not username or not email:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "All fields are required."}), 400
        flash("All fields are required.", "error")
        return redirect(url_for("settings.index"))

    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != current_user.id:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "Username already exists."}), 400
        flash("Username already exists.", "error")
        return redirect(url_for("settings.index"))

    existing_email = User.query.filter_by(email=email).first()
    if existing_email and existing_email.id != current_user.id:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "Email already exists."}), 400
        flash("Email already exists.", "error")
        return redirect(url_for("settings.index"))

    current_user.full_name = full_name
    current_user.username = username
    current_user.email = email
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"message": "Profile updated."})

    flash("Profile updated successfully.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/change-password", methods=["POST"])
@approved_intern_required
def change_password():
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not current_user.check_password(current_password):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "Current password is incorrect."}), 400
        flash("Current password is incorrect.", "error")
        return redirect(url_for("settings.index"))

    if len(new_password) < 6:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "New password must be at least 6 characters."}), 400
        flash("New password must be at least 6 characters.", "error")
        return redirect(url_for("settings.index"))

    if new_password != confirm_password:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "New passwords do not match."}), 400
        flash("New passwords do not match.", "error")
        return redirect(url_for("settings.index"))

    current_user.set_password(new_password)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"message": "Password changed."})

    flash("Password changed successfully.", "success")
    return redirect(url_for("settings.index"))
