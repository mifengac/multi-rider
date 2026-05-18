import threading
from flask import request, jsonify
from . import score_bp
from .services.score_engine import calculate_score, batch_recalculate
from .services.score_store import get_score, get_score_list, get_score_trend


@score_bp.route("/<zjhm>", methods=["GET"])
def score_detail(zjhm):
    result = get_score(zjhm)
    if not result:
        return jsonify({"error": "not_found", "message": "未找到该人员评分"}), 404
    return jsonify(result)


@score_bp.route("/list", methods=["GET"])
def score_list():
    min_score = request.args.get("min_score", 0, type=int)
    max_score = request.args.get("max_score", 100, type=int)
    risk_level = request.args.get("risk_level", "").strip() or None
    area_code = request.args.get("area_code", "").strip() or None
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 20, type=int)
    sort = request.args.get("sort", "desc")

    total, items = get_score_list(min_score, max_score, risk_level, area_code, page, size, sort)
    return jsonify({"total": total, "page": page, "size": size, "items": items})


@score_bp.route("/trend/<zjhm>", methods=["GET"])
def score_trend(zjhm):
    months = request.args.get("months", 6, type=int)
    points = get_score_trend(zjhm, months)
    return jsonify({"zjhm": zjhm, "months": months, "points": points})


@score_bp.route("/recalculate", methods=["POST"])
def recalculate():
    data = request.get_json(silent=True) or {}
    zjhm = data.get("zjhm", "all")

    if zjhm and zjhm != "all":
        result = calculate_score(zjhm)
        return jsonify({"status": "done", "result": result})

    thread = threading.Thread(target=batch_recalculate, daemon=True)
    thread.start()
    return jsonify({"status": "started", "message": "全量重算已启动，后台执行中"})
