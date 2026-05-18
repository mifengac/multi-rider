from flask import Blueprint

graph_bp = Blueprint("graph", __name__, url_prefix="/api/graph")

from . import routes  # noqa: E402, F401
