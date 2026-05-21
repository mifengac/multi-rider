import json
import time
from urllib.parse import quote

from flask import request, jsonify, Response
from . import dashboard_bp
from shared.config.config import logger
from shared.db.kingbase import query_one
from .services.summary_service import get_summary
from .services.trend_service import get_case_trend, get_person_trend, get_score_trend
from .services.distribution_service import (
    get_case_type_distribution, get_risk_level_distribution,
    get_area_distribution, get_age_distribution,
    get_gender_distribution, get_source_distribution, get_school_ranking,
)
from .services.alert_service import get_recent_alerts, mark_alert_read, handle_alert
from .services.alert_rule_engine import run_all_rules
from .services.heatmap_service import get_heatmap
from shared.validators import parse_int_arg, validate_allowed, validate_int_range, validate_zjhm


@dashboard_bp.route("/summary", methods=["GET"])
def summary():
    return jsonify(get_summary())


@dashboard_bp.route("/trend", methods=["GET"])
def trend():
    months = parse_int_arg(request.args.get("months"), 12)
    metric = request.args.get("metric", "cases").strip()

    if not validate_int_range(months, 1, 60):
        return jsonify({"error": "invalid_months", "message": "months 必须为 1-60"}), 400
    if not validate_allowed(metric, {"cases", "persons", "score"}):
        return jsonify({"error": "invalid_metric", "valid": ["cases", "persons", "score"]}), 400

    if metric == "persons":
        data = get_person_trend(months)
        points = data
        degraded = False
    elif metric == "score":
        data = get_score_trend(months)
        points = data
        degraded = False
    else:
        data = get_case_trend(months)
        if isinstance(data, dict):
            points = data.get("points", [])
            degraded = bool(data.get("degraded", False))
        else:
            points = data
            degraded = False

    return jsonify({"metric": metric, "months": months, "points": points, "degraded": degraded})


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

    result = handler()
    if isinstance(result, dict):
        items = result.get("items", [])
        degraded = bool(result.get("degraded", False))
    else:
        items = result
        degraded = False
    return jsonify({"dimension": dim, "items": items, "degraded": degraded})


@dashboard_bp.route("/alerts", methods=["GET"])
def alerts():
    limit = parse_int_arg(request.args.get("limit"), 20)
    if not validate_int_range(limit, 1, 100):
        return jsonify({"error": "invalid_limit"}), 400
    return jsonify({"items": get_recent_alerts(limit)})


def _alert_stream_events():
    pushed_ids = set()
    last_heartbeat = time.monotonic()
    while True:
        try:
            alerts = get_recent_alerts(5) or []
            new_alerts = []
            for alert in alerts:
                alert_id = alert.get("id")
                if alert_id in pushed_ids:
                    continue
                pushed_ids.add(alert_id)
                new_alerts.append(alert)

            for alert in reversed(new_alerts):
                payload = json.dumps(alert, ensure_ascii=False, default=str)
                yield f"data: {payload}\n\n"
                last_heartbeat = time.monotonic()

            if time.monotonic() - last_heartbeat >= 30:
                yield ":\n\n"
                last_heartbeat = time.monotonic()

            time.sleep(3)
        except GeneratorExit:
            return
        except Exception as exc:
            logger.warning("Dashboard alert stream failed: %s", exc)
            time.sleep(3)


@dashboard_bp.route("/alerts/stream", methods=["GET"])
def alert_stream():
    response = Response(_alert_stream_events(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@dashboard_bp.route("/alerts/scan", methods=["POST"])
def alert_scan():
    return jsonify({"result": run_all_rules()})


@dashboard_bp.route("/heatmap", methods=["GET"])
def heatmap():
    days = parse_int_arg(request.args.get("days"), 30)
    if not validate_int_range(days, 1, 365):
        return jsonify({"error": "invalid_days"}), 400
    return jsonify({"days": days, "items": get_heatmap(days)})


@dashboard_bp.route("/data-health", methods=["GET"])
def data_health():
    from .services.data_health_service import collect_health

    return jsonify(collect_health())


@dashboard_bp.route("/alerts/<int:alert_id>/read", methods=["POST"])
def alert_read(alert_id):
    ok = mark_alert_read(alert_id)
    return jsonify({"success": ok})


@dashboard_bp.route("/alerts/<int:alert_id>/handle", methods=["POST"])
def alert_handle(alert_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "handled") or "").strip()
    if not validate_allowed(status, {"pending", "handled", "ignored", "closed"}):
        return jsonify({"error": "invalid_status"}), 400
    ok = handle_alert(alert_id, status)
    return jsonify({"success": ok})


@dashboard_bp.route("/dispatch/from-person", methods=["POST"])
def dispatch_from_person():
    data = request.get_json(silent=True) or {}
    zjhm = str(data.get("zjhm") or "").strip()
    if not zjhm:
        return jsonify({"ok": False, "error": "missing_zjhm"}), 400
    if not validate_zjhm(zjhm):
        return jsonify({"ok": False, "error": "invalid_zjhm"}), 400

    sql = """
        SELECT zjhm
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        WHERE zjhm = %(zjhm)s
        LIMIT 1
    """
    try:
        row = query_one(sql, {"zjhm": zjhm})
    except Exception as exc:
        logger.warning("Dispatch from person validation failed for %s: %s", zjhm, exc)
        row = {}
    if not row:
        return jsonify({"ok": False, "error": "invalid_zjhm"}), 400

    # TODO: 后续接入 dispatch.services.store_service.create_queue_item_from_wcnr
    redirect_url = "/dispatch?zjhm=" + quote(zjhm)
    return jsonify({"ok": True, "zjhm": zjhm, "redirect": redirect_url})


@dashboard_bp.route("/ranking", methods=["GET"])
def ranking():
    by = request.args.get("by", "area").strip()
    metric = request.args.get("metric", "risk_count").strip()
    level = request.args.get("level", "ssfj").strip().lower()
    parent_code = str(request.args.get("parent_code") or "").strip() or None
    if metric not in {"case_count", "risk_count"}:
        return jsonify({"error": "invalid_metric", "valid": ["case_count", "risk_count"]}), 400
    if by == "school":
        data = get_school_ranking(metric)
    elif by == "area":
        if level not in {"ssfj", "sspcs"}:
            return jsonify({"error": "invalid_level", "valid": ["ssfj", "sspcs"]}), 400
        data = get_area_distribution(metric, level=level, parent_code=parent_code)
    else:
        return jsonify({"error": "invalid_by", "valid": ["area", "school"]}), 400

    payload = {"by": by, "metric": metric, "items": data[:10]}
    if by == "area":
        payload["level"] = level
        payload["parent_code"] = parent_code
    return jsonify(payload)
