from flask import Blueprint

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

from . import routes  # noqa: E402, F401
