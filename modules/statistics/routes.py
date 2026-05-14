from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from modules.statistics.services.metric_service import (
    get_detection_metrics,
    get_dispatch_metrics,
    get_gang_metrics,
    get_overview_metrics,
    get_person_metrics,
    normalize_period,
)
from modules.statistics.services.report_service import generate_report, list_reports


statistics_bp = Blueprint("statistics", __name__, url_prefix="/statistics")


@statistics_bp.get("/")
def statistics_page():
    return render_template("statistics/index.html")


@statistics_bp.get("/api/overview")
def statistics_overview():
    return jsonify({"ok": True, **get_overview_metrics(dict(request.args))})


@statistics_bp.get("/api/detection")
def statistics_detection():
    period = normalize_period(dict(request.args))
    return jsonify({"ok": True, "period": period, **get_detection_metrics(period)})


@statistics_bp.get("/api/person")
def statistics_person():
    period = normalize_period(dict(request.args))
    return jsonify({"ok": True, "period": period, **get_person_metrics(period)})


@statistics_bp.get("/api/gang")
def statistics_gang():
    period = normalize_period(dict(request.args))
    return jsonify({"ok": True, "period": period, **get_gang_metrics(period)})


@statistics_bp.get("/api/dispatch")
def statistics_dispatch():
    period = normalize_period(dict(request.args))
    return jsonify({"ok": True, "period": period, **get_dispatch_metrics(period)})


@statistics_bp.get("/api/reports")
def statistics_reports():
    limit = request.args.get("limit", 20)
    return jsonify({"ok": True, "items": list_reports(limit=int(limit or 20))})


@statistics_bp.post("/api/reports/generate")
def statistics_generate_report():
    payload = request.get_json(silent=True) or {}
    result = generate_report(payload)
    return jsonify({"ok": True, **result})

