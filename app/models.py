from datetime import datetime, time, timezone
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
    skills_acquired = db.Column(db.Text, nullable=True)
    work_date = db.Column(db.Date, nullable=False, index=True)
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

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_title": self.task_title,
            "description": self.description,
            "skills_acquired": self.skills_acquired,
            "work_date": self.work_date.isoformat() if self.work_date else None,
            "category": self.category,
            "status": self.status,
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


class InternshipSetting(db.Model):
    __tablename__ = "internship_settings"

    id = db.Column(db.Integer, primary_key=True, default=1)
    required_hours = db.Column(db.Integer, nullable=False, default=487)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_required_hours(cls):
        setting = cls.query.first()
        if not setting:
            setting = cls(required_hours=487)
            db.session.add(setting)
            db.session.commit()
        return setting.required_hours

    def __repr__(self):
        return f"<InternshipSetting required_hours={self.required_hours}>"


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    time_in = db.Column(db.DateTime, nullable=False, index=True)
    time_out = db.Column(db.DateTime, nullable=True)
    total_seconds = db.Column(db.Integer, nullable=True)
    attendance_status = db.Column(db.String(20), nullable=False, default="on_duty")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = db.relationship("User", backref="attendance_records")

    @property
    def duration_hours(self):
        if self.total_seconds:
            return round(self.total_seconds / 3600, 2)
        if self.time_in and self.time_out:
            delta = self.time_out - self.time_in
            return round(delta.total_seconds() / 3600, 2)
        return 0.0

    def to_dict(self):
        from zoneinfo import ZoneInfo
        manila = ZoneInfo("Asia/Manila")
        return {
            "id": self.id,
            "user_id": self.user_id,
            "time_in": self.time_in.isoformat() if self.time_in else None,
            "time_out": self.time_out.isoformat() if self.time_out else None,
            "time_in_manila": self.time_in.replace(tzinfo=timezone.utc).astimezone(manila).strftime("%Y-%m-%d %H:%M:%S") if self.time_in else None,
            "time_out_manila": self.time_out.replace(tzinfo=timezone.utc).astimezone(manila).strftime("%Y-%m-%d %H:%M:%S") if self.time_out else None,
            "total_seconds": self.total_seconds,
            "duration_hours": self.duration_hours,
            "attendance_status": self.attendance_status,
            "date": self.time_in.strftime("%Y-%m-%d") if self.time_in else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AttendanceRecord {self.id}: user={self.user_id} status={self.attendance_status}>"


class AttendanceCorrectionRequest(db.Model):
    __tablename__ = "attendance_correction_requests"

    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(
        db.Integer,
        db.ForeignKey("attendance_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_time_in = db.Column(db.DateTime, nullable=True)
    requested_time_out = db.Column(db.DateTime, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    request_status = db.Column(db.String(20), nullable=False, default="pending")
    reviewed_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    attendance = db.relationship("AttendanceRecord", backref="correction_requests")
    user = db.relationship("User", foreign_keys=[user_id], backref="correction_requests")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        from zoneinfo import ZoneInfo
        manila = ZoneInfo("Asia/Manila")
        return {
            "id": self.id,
            "attendance_id": self.attendance_id,
            "user_id": self.user_id,
            "requested_time_in": self.requested_time_in.isoformat() if self.requested_time_in else None,
            "requested_time_out": self.requested_time_out.isoformat() if self.requested_time_out else None,
            "requested_time_in_manila": self.requested_time_in.astimezone(manila).strftime("%Y-%m-%d %H:%M:%S") if self.requested_time_in else None,
            "requested_time_out_manila": self.requested_time_out.astimezone(manila).strftime("%Y-%m-%d %H:%M:%S") if self.requested_time_out else None,
            "reason": self.reason,
            "request_status": self.request_status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<AttendanceCorrectionRequest {self.id}: status={self.request_status}>"


class AttendanceAuditLog(db.Model):
    __tablename__ = "attendance_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(
        db.Integer,
        db.ForeignKey("attendance_records.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    admin_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = db.Column(db.String(50), nullable=False)
    old_values = db.Column(db.Text, nullable=True)
    new_values = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    attendance = db.relationship("AttendanceRecord", backref="audit_logs")
    admin = db.relationship("User", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AttendanceAuditLog {self.action}>"


# Add helper properties to User for attendance hours
_User_completed_hours = None


def _user_completed_hours(self):
    from app.models import AttendanceRecord
    total = (
        db.session.query(db.func.sum(AttendanceRecord.total_seconds))
        .filter_by(user_id=self.id, attendance_status="off_duty")
        .filter(AttendanceRecord.total_seconds.isnot(None))
        .scalar()
    )
    return round((total or 0) / 3600, 2)


def _user_attendance_progress(self, required_hours=None):
    from app.models import InternshipSetting
    if required_hours is None:
        required_hours = InternshipSetting.get_required_hours()
    if required_hours <= 0:
        return 0.0
    completed = self.completed_hours
    return round((completed / required_hours) * 100, 2)


User.completed_hours = property(_user_completed_hours)
User.attendance_progress = property(lambda self: _user_attendance_progress(self))
