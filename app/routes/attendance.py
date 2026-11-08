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
from sqlalchemy import func, extract, and_
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app import db
from app.models import (
    User,
    AttendanceRecord,
    AttendanceCorrectionRequest,
    AttendanceAuditLog,
    InternshipSetting,
)
from app.routes.helpers import approved_intern_required

MANILA = ZoneInfo("Asia/Manila")

bp = Blueprint("attendance", __name__, url_prefix="/attendance")


def _now_utc():
    return datetime.utcnow()


def _audit(action, attendance_id=None, admin_id=None, details=None, old_values=None, new_values=None, reason=None):
    entry = AttendanceAuditLog(
        attendance_id=attendance_id,
        admin_id=admin_id or (current_user.id if current_user.is_authenticated else None),
        action=action,
        old_values=old_values,
        new_values=new_values,
        reason=reason,
    )
    db.session.add(entry)


@bp.route("/")
@approved_intern_required
def index():
    required_hours = InternshipSetting.get_required_hours()
    return render_template(
        "attendance/index.html",
        required_hours=required_hours,
        completed_hours=current_user.completed_hours,
        progress=current_user.attendance_progress,
    )


@bp.route("/api/status")
@approved_intern_required
def api_status():
    active = (
        AttendanceRecord.query.filter_by(
            user_id=current_user.id, attendance_status="on_duty"
        )
        .filter(AttendanceRecord.time_out.is_(None))
        .order_by(AttendanceRecord.created_at.desc())
        .first()
    )

    completed_hours = current_user.completed_hours
    required_hours = InternshipSetting.get_required_hours()
    progress = round((completed_hours / required_hours * 100), 2) if required_hours else 0.0

    now_manila = datetime.now(MANILA)

    return jsonify(
        {
            "active_session": active.to_dict() if active else None,
            "is_on_duty": active is not None,
            "completed_hours": completed_hours,
            "required_hours": required_hours,
            "remaining_hours": max(required_hours - completed_hours, 0),
            "progress_percentage": min(progress, 100.0),
            "current_time_manila": now_manila.strftime("%Y-%m-%d %H:%M:%S"),
            "current_date_manila": now_manila.strftime("%Y-%m-%d"),
            "current_time_utc": _now_utc().isoformat(),
        }
    )


@bp.route("/time-in", methods=["POST"])
@approved_intern_required
def time_in():
    # Check for existing active session
    active = (
        AttendanceRecord.query.filter_by(
            user_id=current_user.id, attendance_status="on_duty"
        )
        .filter(AttendanceRecord.time_out.is_(None))
        .order_by(AttendanceRecord.created_at.desc())
        .first()
    )

    if active:
        return jsonify(
            {"error": "You already have an active TIME IN session."}
        ), 400

    now_utc = _now_utc()
    record = AttendanceRecord(
        user_id=current_user.id,
        time_in=now_utc,
        time_out=None,
        total_seconds=None,
        attendance_status="on_duty",
    )
    db.session.add(record)
    db.session.commit()
    _audit("time_in", attendance_id=record.id, details=f"Time IN recorded at {now_utc.isoformat()}")
    db.session.commit()

    return jsonify(
        {
            "message": "Time IN recorded successfully.",
            "record": record.to_dict(),
        }
    )


@bp.route("/time-out", methods=["POST"])
@approved_intern_required
def time_out():
    active = (
        AttendanceRecord.query.filter_by(
            user_id=current_user.id, attendance_status="on_duty"
        )
        .filter(AttendanceRecord.time_out.is_(None))
        .order_by(AttendanceRecord.created_at.desc())
        .first()
    )

    if not active:
        return jsonify({"error": "No active TIME IN session found."}), 400

    now_utc = _now_utc()
    delta = now_utc - active.time_in
    total_seconds = int(delta.total_seconds())

    if total_seconds < 0:
        return jsonify({"error": "Invalid duration."}), 400

    active.time_out = now_utc
    active.total_seconds = total_seconds
    active.attendance_status = "off_duty"
    active.updated_at = now_utc
    db.session.commit()
    _audit(
        "time_out",
        attendance_id=active.id,
        old_values=f"time_in={active.time_in.isoformat()}, time_out=None",
        new_values=f"time_in={active.time_in.isoformat()}, time_out={now_utc.isoformat()}, total_seconds={total_seconds}",
        details=f"Time OUT recorded. Duration: {total_seconds}s",
    )
    db.session.commit()

    return jsonify(
        {
            "message": "Time OUT recorded successfully.",
            "record": active.to_dict(),
            "duration_hours": active.duration_hours,
        }
    )


@bp.route("/history")
@approved_intern_required
def history():
    return render_template("attendance/history.html")


@bp.route("/api/history")
@approved_intern_required
def api_history():
    page = request.args.get("page", 1, type=int)
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    month = request.args.get("month", "").strip()

    query = AttendanceRecord.query.filter_by(user_id=current_user.id).order_by(
        AttendanceRecord.time_in.desc()
    )

    if date_from:
        try:
            query = query.filter(AttendanceRecord.time_in >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(AttendanceRecord.time_in <= datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1))
        except ValueError:
            pass
    if month:
        try:
            year, m = month.split("-")
            query = query.filter(
                extract("year", AttendanceRecord.time_in) == int(year),
                extract("month", AttendanceRecord.time_in) == int(m),
            )
        except ValueError:
            pass

    pagination = query.paginate(page=page, per_page=20, error_out=False)

    return jsonify(
        {
            "records": [r.to_dict() for r in pagination.items],
            "pagination": {
                "page": pagination.page,
                "pages": pagination.pages,
                "total": pagination.total,
                "has_prev": pagination.has_prev,
                "has_next": pagination.has_next,
                "prev_num": pagination.prev_num,
                "next_num": pagination.next_num,
            },
        }
    )


@bp.route("/corrections")
@approved_intern_required
def corrections():
    return render_template("attendance/corrections.html")


@bp.route("/api/corrections", methods=["GET", "POST"])
@approved_intern_required
def api_corrections():
    if request.method == "GET":
        page = request.args.get("page", 1, type=int)
        query = (
            AttendanceCorrectionRequest.query.filter_by(user_id=current_user.id)
            .order_by(AttendanceCorrectionRequest.created_at.desc())
        )
        pagination = query.paginate(page=page, per_page=20, error_out=False)
        return jsonify(
            {
                "requests": [r.to_dict() for r in pagination.items],
                "pagination": {
                    "page": pagination.page,
                    "pages": pagination.pages,
                    "total": pagination.total,
                    "has_prev": pagination.has_prev,
                    "has_next": pagination.has_next,
                },
            }
        )

    # POST - submit correction request
    attendance_id = request.form.get("attendance_id", type=int)
    requested_time_in = request.form.get("requested_time_in", "").strip()
    requested_time_out = request.form.get("requested_time_out", "").strip()
    reason = (request.form.get("reason") or "").strip()

    if not reason:
        return jsonify({"error": "Reason is required."}), 400

    req_time_in = None
    req_time_out = None
    if requested_time_in:
        try:
            req_time_in = datetime.strptime(requested_time_in, "%Y-%m-%dT%H:%M")
        except ValueError:
            return jsonify({"error": "Invalid time in format."}), 400
    if requested_time_out:
        try:
            req_time_out = datetime.strptime(requested_time_out, "%Y-%m-%dT%H:%M")
        except ValueError:
            return jsonify({"error": "Invalid time out format."}), 400

    correction = AttendanceCorrectionRequest(
        attendance_id=attendance_id,
        user_id=current_user.id,
        requested_time_in=req_time_in,
        requested_time_out=req_time_out,
        reason=reason,
        request_status="pending",
    )
    db.session.add(correction)
    db.session.commit()
    _audit(
        "correction_requested",
        attendance_id=attendance_id,
        details=f"Correction requested: {reason}",
    )
    db.session.commit()

    return jsonify(
        {"message": "Correction request submitted.", "request": correction.to_dict()}
    ), 201


@bp.route("/api/active-session")
@approved_intern_required
def api_active_session():
    active = (
        AttendanceRecord.query.filter_by(
            user_id=current_user.id, attendance_status="on_duty"
        )
        .filter(AttendanceRecord.time_out.is_(None))
        .order_by(AttendanceRecord.created_at.desc())
        .first()
    )
    if not active:
        return jsonify({"active": False})
    now_utc = _now_utc()
    elapsed = int((now_utc - active.time_in).total_seconds())
    return jsonify(
        {
            "active": True,
            "record": active.to_dict(),
            "elapsed_seconds": elapsed,
            "elapsed_hours": round(elapsed / 3600, 2),
        }
    )
