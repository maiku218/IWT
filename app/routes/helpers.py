from flask import Blueprint, abort, redirect, url_for, flash
from flask_login import current_user
from functools import wraps

from app.models import User, WorkLog


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)

    return decorated


def approved_intern_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        if current_user.role != "intern" or not current_user.is_approved():
            abort(403)
        return f(*args, **kwargs)

    return decorated


def get_work_log(log_id):
    log = db_get(WorkLog, log_id)
    if not log:
        abort(404)
    if current_user.role != "admin" and log.user_id != current_user.id:
        abort(403)
    return log


def db_get(model, record_id):
    from app import db
    return db.session.get(model, int(record_id))


__all__ = ["admin_required", "approved_intern_required", "get_work_log", "db_get"]
