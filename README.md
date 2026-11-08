# Intern Work Tracker System

A minimalist, full-stack web application where interns record daily work activities, view them on a large monthly calendar, and generate productivity reports. Built with **Python Flask**, **PostgreSQL**, **FullCalendar.js**, and **Bootstrap 5**.

## Features

- Secure login/logout with hashed passwords (Werkzeug)
- Individual intern accounts with private work records
- Admin role: create/manage interns, view all logs, reset passwords
- Large interactive monthly calendar (FullCalendar) showing task counts per day
- Click any date to view, add, edit, or delete that day's work logs
- Work log form: date, title, description, start/end time, category, status, attachment
- Search, filter (date/category/status), and paginated work log history
- Productivity reports (daily/weekly/monthly) with Chart.js visualizations
- Export reports to PDF and Excel
- User settings: update profile and change password
- Minimalist, responsive design (desktop, tablet, mobile)

## Tech Stack

- Backend: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF
- Database: PostgreSQL (psycopg2)
- Frontend: HTML5, CSS3, JavaScript, Bootstrap 5, FullCalendar.js, Chart.js
- Exports: fpdf2 (PDF), openpyxl (Excel)
- Deployment: Gunicorn, Render

## Project Structure

```
intern_work_tracker/
├── app/
│   ├── __init__.py          # Flask app factory & extensions
│   ├── models.py            # User, WorkLog, Attachment models
│   ├── routes/
│   │   ├── auth.py          # Login / logout
│   │   ├── dashboard.py     # Dashboard, calendar API, stats
│   │   ├── work_logs.py     # Work log CRUD
│   │   ├── reports.py       # Reports + PDF/Excel export
│   │   ├── admin.py         # Admin dashboard, intern management, all logs
│   │   └── settings.py      # User profile & password
│   ├── templates/           # Jinja2 HTML templates
│   └── static/
│       ├── css/style.css
│       └── js/*.js
├── migrations/              # Flask-Migrate database migrations
├── config.py                # Configuration
├── run.py                   # Application entry point
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Local Installation (Windows)

### Prerequisites
- Python 3.10+
- PostgreSQL running locally
- pip

### 1. Clone / open the project
```powershell
cd "C:\Users\Mike Angelo\OneDrive\Documents\Intern Tracker\intern_work_tracker"
```

### 2. Set up PostgreSQL
Create a database and user (example using the `postgres` superuser):

```powershell
psql -U postgres -h localhost -c "CREATE USER intern_app WITH PASSWORD 'intern_app_pass' LOGIN;"
psql -U postgres -h localhost -c "CREATE DATABASE intern_tracker OWNER intern_app;"
```

If you use different credentials, update `DATABASE_URL` in `.env` (see below).

### 3. Create virtual environment & install dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment
Copy `.env.example` to `.env` and adjust values:

```powershell
copy .env.example .env
```

Edit `.env` to set your `SECRET_KEY` and `DATABASE_URL`.

### 5. Initialize the database
```powershell
flask db init        # only the first time
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. Seed the admin account
```powershell
flask seed-db
```

This creates an admin account:
- Username: `admin`
- Password: `Admin123!`
- Role: admin

(Uses env vars `ADMIN_USERNAME` / `ADMIN_PASSWORD` if set; otherwise defaults above. **Change these in production.**)

### 7. Run the application
```powershell
flask run
# or
python run.py
```

Open http://127.0.0.1:5000 in your browser.

Login with the admin account, then create intern accounts via Admin Dashboard > Intern Management. Interns log in with their own credentials.

## Available CLI Commands

- `flask db init / migrate / upgrade` — manage database migrations
- `flask seed-db` — create the default admin account if none exists

## Deployment on Render

1. Push this repository to GitHub.
2. Create a **PostgreSQL** database on Render.
3. Create a **Web Service** on Render connected to your repo.
4. Set the following environment variables in Render:
   - `FLASK_CONFIG=production`
   - `SECRET_KEY` (long random string)
   - `DATABASE_URL` (Render provides this automatically for the PostgreSQL service)
5. Set the build command:
   ```
   pip install -r requirements.txt && flask db upgrade && flask seed-db
   ```
6. Set the start command:
   ```
   gunicorn run:app
   ```

Render will run migrations and seed the admin on each deploy.

## Security

- Passwords are hashed with Werkzeug (`generate_password_hash` / `check_password_hash`)
- Flask-Login with strong session protection
- CSRF protection via Flask-WTF on all state-changing requests
- Role-based authorization (admin vs intern)
- Interns can only access their own work logs; admin access is enforced server-side
- Session cookies are HttpOnly and SameSite=Lax (Secure in production)
- File uploads are validated by extension and size (max 16 MB)
- No passwords are stored or returned in plain text

## Notes

- PostgreSQL `pg_hba.conf` is set to `trust` for local connections in this development environment. For production, use scram-sha-256 with a strong password via `DATABASE_URL`.
- Admin accounts cannot be deactivated through the intern-facing interface; intern deactivation is a soft-delete (`is_active`) to preserve data-retention rules.
