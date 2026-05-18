from flask import Blueprint

score_bp = Blueprint("score", __name__, url_prefix="/api/score")

from . import routes  # noqa: E402, F401
