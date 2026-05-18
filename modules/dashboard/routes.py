from flask import request, jsonify
from . import dashboard_bp
from .services.summary_service import get_summary
from .services.trend_service import get_case_trend, get_person_trend, get_score_trend
from .services.distribution_service import (
    get_case_type_distribution, get_risk_level_distribution,
    get_area_distribution, get_age_distribution,
    get_gender_distribution, get_source_distribution,
)
from .services.alert_service import get_recent_alerts, mark_alert_read, handle_alert


@dashboard_bp.route("/summary", methods=["GET"])
def summary():
    return jsonify(get_summary())


@dashboard_bp.route("/trend", methods=["GET"])
def trend():
    months = request.args.get("months", 12, type=int)
    metric = request.args.get("metric", "cases")

    if metric == "persons":
        data = get_person_trend(months)
    elif metric == "score":
        data = get_score_trend(months)
    else:
        data = get_case_trend(months)

    return jsonify({"metric": metric, "months": months, "points": data})


@dashboard_bp.route("/distribution", methods=["GET"])
def distribution():
    dim = request.args.get("dim", "case_type")

    handlers = {
        "case_type": get_case_type_distribution,
        "risk_level": get_risk_level_distribution,
        "area": get_area_distribution,
        "age": get_age_distribution,
        "gender": get_gender_distribution,
        "source": get_source_distribution,
    }

    handler = handlers.get(dim)
    if not handler:
        return jsonify({"error": "invalid_dim", "valid": list(handlers.keys())}), 400

    return jsonify({"dimension": dim, "items": handler()})


@dashboard_bp.route("/alerts", methods=["GET"])
def alerts():
    limit = request.args.get("limit", 20, type=int)
    return jsonify({"items": get_recent_alerts(limit)})


@dashboard_bp.route("/alerts/<int:alert_id>/read", methods=["POST"])
def alert_read(alert_id):
    ok = mark_alert_read(alert_id)
    return jsonify({"success": ok})


@dashboard_bp.route("/alerts/<int:alert_id>/handle", methods=["POST"])
def alert_handle(alert_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status", "handled")
    ok = handle_alert(alert_id, status)
    return jsonify({"success": ok})


@dashboard_bp.route("/ranking", methods=["GET"])
def ranking():
    metric = request.args.get("metric", "risk_count")
    data = get_area_distribution()
    return jsonify({"metric": metric, "items": data[:10]})
