from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    current_app,
)
from flask_login import current_user
from sqlalchemy import func, extract
from datetime import date, datetime, timedelta
import io

from app import db
from app.models import WorkLog
from app.routes.helpers import approved_intern_required

bp = Blueprint("reports", __name__, url_prefix="/reports")

STATUSES = ["Completed", "Ongoing", "Pending"]
CATEGORIES = [
    "Technical Support",
    "Troubleshooting",
    "Documentation",
    "Research",
    "Administrative Work",
    "Software Development",
    "Other",
]


def _parse_date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def _base_query(start_date, end_date):
    query = WorkLog.query.filter_by(user_id=current_user.id)
    if start_date:
        query = query.filter(WorkLog.work_date >= start_date)
    if end_date:
        query = query.filter(WorkLog.work_date <= end_date)
    return query.order_by(WorkLog.work_date.desc(), WorkLog.created_at.desc())


@bp.route("/")
@approved_intern_required
def index():
    today = date.today()
    default_start = today.replace(day=1)
    default_end = today

    start_date = _parse_date(request.args.get("start_date"), default_start)
    end_date = _parse_date(request.args.get("end_date"), default_end)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    logs = _base_query(start_date, end_date).all()

    total_tasks = len(logs)
    completed_tasks = sum(1 for l in logs if l.status == "Completed")
    ongoing_tasks = sum(1 for l in logs if l.status == "Ongoing")
    pending_tasks = sum(1 for l in logs if l.status == "Pending")

    # Daily breakdown for chart
    daily = {}
    for l in logs:
        key = l.work_date.isoformat()
        daily[key] = daily.get(key, 0) + 1
    daily_sorted = sorted(daily.items())

    # Category breakdown
    category_counts = {}
    for l in logs:
        category_counts[l.category] = category_counts.get(l.category, 0) + 1

    # Status breakdown
    status_counts = {s: 0 for s in STATUSES}
    for l in logs:
        status_counts[l.status] = status_counts.get(l.status, 0) + 1

    return render_template(
        "reports/index.html",
        logs=logs,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        ongoing_tasks=ongoing_tasks,
        pending_tasks=pending_tasks,
        daily_sorted=daily_sorted,
        category_counts=category_counts,
        status_counts=status_counts,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        categories=CATEGORIES,
        statuses=STATUSES,
    )


@bp.route("/export/pdf")
@approved_intern_required
def export_pdf():
    start_date = _parse_date(request.args.get("start_date"), date.today().replace(day=1))
    end_date = _parse_date(request.args.get("end_date"), date.today())
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    logs = _base_query(start_date, end_date).all()

    try:
        from fpdf import FPDF
    except ImportError:
        flash("PDF export library not available.", "error")
        return redirect(url_for("reports.index"))

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Work Log Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0,
        7,
        f"User: {current_user.full_name} ({current_user.username})",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.cell(
        0,
        7,
        f"Period: {start_date.isoformat()} to {end_date.isoformat()}",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(6)

    headers = ["Date", "Task Title", "Category", "Status", "Description"]
    widths = [22, 55, 32, 22, 0]

    pdf.set_font("Helvetica", "B", 9)
    for i, h in enumerate(headers):
        w = widths[i] if widths[i] else 100
        pdf.cell(w, 8, h, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for log in logs:
        row = [
            log.work_date.isoformat(),
            log.task_title,
            log.category,
            log.status,
            (log.description or "")[:60],
        ]
        for i, val in enumerate(row):
            w = widths[i] if widths[i] else 100
            pdf.cell(w, 7, str(val), border=1)
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, f"Total Tasks: {len(logs)}   Completed: {sum(1 for l in logs if l.status == 'Completed')}", new_x="LMARGIN", new_y="NEXT")

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)

    filename = f"work_report_{start_date.isoformat()}_to_{end_date.isoformat()}.pdf"
    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/export/excel")
@approved_intern_required
def export_excel():
    start_date = _parse_date(request.args.get("start_date"), date.today().replace(day=1))
    end_date = _parse_date(request.args.get("end_date"), date.today())
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    logs = _base_query(start_date, end_date).all()

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
    except ImportError:
        flash("Excel export library not available.", "error")
        return redirect(url_for("reports.index"))

    wb = Workbook()
    ws = wb.active
    ws.title = "Work Logs"

    headers = ["Date", "Task Title", "Category", "Status", "Skills Acquired", "Description", "Created At"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    for log in logs:
        ws.append([
            log.work_date.isoformat(),
            log.task_title,
            log.category,
            log.status,
            log.skills_acquired or "",
            log.description or "",
            log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else "",
        ])

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value or "")) > max_len:
                    max_len = len(str(cell.value))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 50)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"work_report_{start_date.isoformat()}_to_{end_date.isoformat()}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
