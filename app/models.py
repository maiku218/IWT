from datetime import datetime, time
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="intern")
    account_status = db.Column(
        db.String(20), nullable=False, default="pending"
    )
    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    approver = db.relationship(
        "User", remote_side=[id], foreign_keys=[approved_by], backref="approved_accounts"
    )
    work_logs = db.relationship(
        "WorkLog",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan",
    )
    audit_logs = db.relationship(
        "AuditLog",
        backref="actor",
        lazy=True,
        foreign_keys="AuditLog.actor_id",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"

    def is_intern(self):
        return self.role == "intern"

    def is_pending(self):
        return self.account_status == "pending"

    def is_approved(self):
        return self.account_status == "approved"

    def is_rejected(self):
        return self.account_status == "rejected"

    def is_suspended(self):
        return self.account_status == "suspended"

    def can_intern_login(self):
        return (
            self.is_active
            and self.is_intern()
            and self.is_approved()
        )

    def __repr__(self):
        return f"<User {self.username}>"


class WorkLog(db.Model):
    __tablename__ = "work_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    work_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    attachments = db.relationship(
        "Attachment",
        backref="work_log",
        lazy=True,
        cascade="all, delete-orphan",
    )

    @property
    def time_spent(self):
        if self.start_time and self.end_time:
            start = datetime.combine(datetime.today(), self.start_time)
            end = datetime.combine(datetime.today(), self.end_time)
            delta = end - start
            total_minutes = int(delta.total_seconds() / 60)
            if total_minutes <= 0:
                return "0 min"
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m" if minutes else f"{hours}h"
            return f"{minutes}m"
        return "Not specified"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_title": self.task_title,
            "description": self.description,
            "work_date": self.work_date.isoformat() if self.work_date else None,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "category": self.category,
            "status": self.status,
            "time_spent": self.time_spent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<WorkLog {self.id}: {self.task_title}>"


class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    work_log_id = db.Column(
        db.Integer,
        db.ForeignKey("work_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Attachment {self.file_name}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog {self.action}>"
