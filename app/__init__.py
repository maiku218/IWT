import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"
login_manager.session_protection = "strong"


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "default")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes import auth, dashboard, work_logs, reports, admin, settings, attendance

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(work_logs)
    app.register_blueprint(reports)
    app.register_blueprint(admin)
    app.register_blueprint(settings)
    app.register_blueprint(attendance)

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("errors/404.html"), 404

    @app.cli.command("seed-db")
    def seed_db():
        """Seed the default admin account if none exists."""
        from app.models import User
        admin_username = os.environ.get("ADMIN_USERNAME", "admin")
        admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")

        existing = User.query.filter_by(username=admin_username).first()
        if existing:
            print(f"Admin user '{admin_username}' already exists.")
            return

        admin = User(
            full_name="System Administrator",
            username=admin_username,
            email="admin@example.com",
            role="admin",
            account_status="approved",
            is_active=True,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin account created: username='{admin_username}', password='{admin_password}'")

    @app.route("/")
    def root():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    return app
