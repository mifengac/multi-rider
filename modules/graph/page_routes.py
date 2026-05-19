from flask import Blueprint, render_template

graph_page_bp = Blueprint("graph_page", __name__)


@graph_page_bp.route("/graph")
def graph_page():
    return render_template("modules/graph/graph.html", active_tab="graph")
