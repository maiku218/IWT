import os
from app import create_app, db
from app.models import User

app = create_app(os.environ.get("FLASK_CONFIG", "default"))

with app.app_context():
    # Auto-migrate database on startup
    from flask_migrate import upgrade
    upgrade()

    # Create admin account if not exists
    if not User.query.filter_by(username="admin").first():
        admin = User(
            full_name="System Administrator",
            username="admin",
            email="admin@example.com",
            role="admin",
            account_status="approved",
            is_active=True,
        )
        admin.set_password("Admin123!")
        db.session.add(admin)
        db.session.commit()
        print("Admin created: admin / Admin123!")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
