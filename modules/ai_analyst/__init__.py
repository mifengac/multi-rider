from flask import Blueprint

ai_analyst_bp = Blueprint("ai_analyst", __name__, url_prefix="/api/ai")
ai_analyst_page_bp = Blueprint("ai_analyst_page", __name__)

from . import routes  # noqa: E402, F401
