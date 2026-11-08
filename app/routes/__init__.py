from app.routes.auth import bp as auth
from app.routes.dashboard import bp as dashboard
from app.routes.work_logs import bp as work_logs
from app.routes.reports import bp as reports
from app.routes.admin import bp as admin
from app.routes.settings import bp as settings

__all__ = ["auth", "dashboard", "work_logs", "reports", "admin", "settings"]
