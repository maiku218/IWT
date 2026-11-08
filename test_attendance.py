import re
from datetime import datetime
import time
from app import create_app, db
from app.models import User, InternshipSetting, AttendanceRecord, AttendanceCorrectionRequest, AttendanceAuditLog

app = create_app("development")

# Clean up previous test data and seed admin
with app.app_context():
    john_before = User.query.filter_by(username="john").first()
    print("  john exists before cleanup:", john_before is not None)
    AttendanceAuditLog.query.delete()
    AttendanceCorrectionRequest.query.delete()
    AttendanceRecord.query.delete()
    deleted = User.query.filter_by(username="john").delete()
    print("  deleted john rows:", deleted)
    db.session.commit()
    john_after = User.query.filter_by(username="john").first()
    print("  john exists after cleanup:", john_after is not None)
    existing = User.query.filter_by(username="admin").first()
    if not existing:
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
    s = InternshipSetting.query.first()
    if not s:
        db.session.add(InternshipSetting(required_hours=487))
        db.session.commit()

client = app.test_client()


def page_token(path):
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'name="csrf-token" content="([^"]+)"', html)
    return m.group(1) if m else None


def post_with_csrf(path, data=None, headers=None, token_path=None):
    if headers is None:
        headers = {}
    tp = token_path or path
    t = page_token(tp)
    if t:
        headers["X-CSRFToken"] = t
    return client.post(path, data=data, headers=headers)


print("== ATTENDANCE WORKFLOW TESTS ==")

print("== 1. Register intern john ==")
r = post_with_csrf("/register", data={
    "full_name": "John Intern",
    "username": "john",
    "email": "john@example.com",
    "password": "Intern123!",
    "confirm_password": "Intern123!",
})
print("  registration status:", r.status_code)
data_text = r.get_data(as_text=True)
if "Username already exists" in data_text:
    print("  ERROR: Username already exists - cleanup may not have run")
elif "All fields are required" in data_text:
    print("  ERROR: All fields are required")
elif "csrf" in data_text.lower():
    print("  ERROR: CSRF token issue")
else:
    print("  No obvious error message found")
print("  response snippet:", data_text[:200].replace("\n", " "))
assert r.status_code in (200, 302), (r.status_code, r.data[:300])
print("  registration OK")

print("== 2. Admin approves john ==")
client.get("/logout")
t = page_token("/admin/login")
client.post("/admin/login", data={"username": "admin", "password": "Admin123!", "csrf_token": t}, follow_redirects=True)
r = client.get("/admin/approvals")
html = r.get_data(as_text=True)
m = re.search(r'data-id="(\d+)"', html)
assert m, "john not found in approvals"
john_id = m.group(1)
r = client.post(f"/admin/approvals/{john_id}/approve", headers={"X-CSRFToken": t})
assert r.status_code == 200, r.status_code
print("  approve OK (id:", john_id, ")")

print("== 3. Intern logs in after approval ==")
client.get("/logout")
t = page_token("/login")
r = client.post("/login", data={"username": "john", "password": "Intern123!", "csrf_token": t}, follow_redirects=True)
assert r.status_code == 200, r.status_code
print("  login OK")

print("== 4. Time IN ==")
r = post_with_csrf("/attendance/time-in", token_path="/attendance/")
assert r.status_code == 200, (r.status_code, r.data)
data = r.get_json()
assert data["record"]["attendance_status"] == "on_duty"
print("  time-in OK")

print("== 5. Duplicate TIME IN prevented ==")
r = post_with_csrf("/attendance/time-in", token_path="/attendance/")
assert r.status_code == 400, r.status_code
assert b"already have an active" in r.data
print("  duplicate time-in blocked (400) OK")

print("== 6. Get status ==")
r = client.get("/attendance/api/status")
assert r.status_code == 200
data = r.get_json()
assert data["is_on_duty"] == True
print("  status API OK")

print("== 7. Active session API ==")
r = client.get("/attendance/api/active-session")
assert r.status_code == 200
data = r.get_json()
assert data["active"] == True
print("  active session API OK")

print("== 8. Time OUT ==")
time.sleep(1)
# Debug: check the active session before time-out
with app.app_context():
    from app.models import User as U, AttendanceRecord as AR
    u = U.query.filter_by(username="john").first()
    ar = AR.query.filter_by(user_id=u.id, attendance_status="on_duty").filter(AR.time_out.is_(None)).first()
    if ar:
        print(f"  DB time_in: {ar.time_in} (tzinfo={ar.time_in.tzinfo})")
    now = datetime.utcnow()
    print(f"  now_utc: {now} (type={type(now)})")
    if ar:
        delta = now - ar.time_in
        print(f"  delta seconds: {delta.total_seconds()}")

r = post_with_csrf("/attendance/time-out", token_path="/attendance/")
print("  time-out status:", r.status_code, r.data[:200])
assert r.status_code == 200, (r.status_code, r.data)
data = r.get_json()
assert data["record"]["attendance_status"] == "off_duty"
assert data["duration_hours"] >= 0
print("  time-out OK (duration:", data["duration_hours"], "hours)")

print("== 9. TIME OUT without session prevented ==")
r = post_with_csrf("/attendance/time-out", token_path="/attendance/")
assert r.status_code == 400, r.status_code
print("  invalid time-out blocked (400) OK")

print("== 10. Attendance history ==")
r = client.get("/attendance/history")
assert r.status_code == 200
print("  history page OK")

print("== 11. History API ==")
r = client.get("/attendance/api/history")
assert r.status_code == 200
data = r.get_json()
assert len(data["records"]) >= 1
print("  history API OK (records:", len(data["records"]), ")")

print("== 12. Correction request ==")
r = client.get("/attendance/api/history")
rec_id = r.get_json()["records"][0]["id"]
r = post_with_csrf("/attendance/api/corrections", data={
    "attendance_id": rec_id,
    "reason": "Forgot to time out properly",
}, token_path="/attendance/corrections")
assert r.status_code == 201, (r.status_code, r.data)
print("  correction request submitted OK")

print("== 13. Admin approves correction ==")
client.get("/logout")
t = page_token("/admin/login")
client.post("/admin/login", data={"username": "admin", "password": "Admin123!", "csrf_token": t}, follow_redirects=True)
r = client.get("/admin/attendance-corrections")
html = r.get_data(as_text=True)
m = re.search(r'data-id="(\d+)"', html)
assert m, "correction not found"
corr_id = m.group(1)
r = client.post(f"/admin/attendance-corrections/{corr_id}/approve", headers={"X-CSRFToken": t})
assert r.status_code == 200, (r.status_code, r.data)
print("  correction approval OK")

print("== 14. Admin duty hours ==")
r = client.get("/admin/intern-duty-hours")
assert r.status_code == 200
assert b"John Intern" in r.data
print("  intern duty hours page OK")

print("== 15. Admin attendance monitoring ==")
r = client.get("/admin/attendance-monitoring")
assert r.status_code == 200
print("  attendance monitoring page OK")

print("== 16. Admin rejects correction ==")
# Submit a new correction as john
client.get("/logout")
t = page_token("/login")
client.post("/login", data={"username": "john", "password": "Intern123!", "csrf_token": t}, follow_redirects=True)
r = client.get("/attendance/api/history")
rec_id = r.get_json()["records"][0]["id"]
r = post_with_csrf("/attendance/api/corrections", data={
    "attendance_id": rec_id,
    "reason": "Second correction request",
}, token_path="/attendance/corrections")
assert r.status_code == 201, (r.status_code, r.data)
# Log out, log in as admin, reject
client.get("/logout")
t = page_token("/admin/login")
client.post("/admin/login", data={"username": "admin", "password": "Admin123!", "csrf_token": t}, follow_redirects=True)
r = client.get("/admin/attendance-corrections")
html = r.get_data(as_text=True)
m = re.search(r'data-id="(\d+)"', html)
assert m, "correction not found"
corr_id = m.group(1)
r = client.post(f"/admin/attendance-corrections/{corr_id}/reject", data={"reason": "Invalid request"}, headers={"X-CSRFToken": t})
assert r.status_code == 200, (r.status_code, r.data)
print("  correction rejection OK")

print("== 17. Intern cannot access admin routes ==")
client.get("/logout")
t = page_token("/login")
client.post("/login", data={"username": "john", "password": "Intern123!", "csrf_token": t}, follow_redirects=True)
r = client.get("/admin/attendance-monitoring", follow_redirects=False)
assert r.status_code == 403, r.status_code
print("  intern blocked from admin (403) OK")

print("\nALL ATTENDANCE TESTS PASSED")
