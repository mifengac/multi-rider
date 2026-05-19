from flask import render_template

from . import ai_analyst_page_bp


@ai_analyst_page_bp.route("/ai-analyst")
def analyst_page():
    return render_template("modules/ai_analyst/analyst.html", active_tab="ai-analyst")
