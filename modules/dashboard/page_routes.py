from flask import Blueprint, render_template

dashboard_page_bp = Blueprint("dashboard_page", __name__)


@dashboard_page_bp.route("/dashboard")
def dashboard_page():
    return render_template("modules/dashboard/dashboard.html", active_tab="dashboard")
