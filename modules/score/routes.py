import threading
from flask import request, jsonify
from . import score_bp
from .services.score_engine import calculate_score, batch_recalculate
from .services.score_store import get_score, get_score_list, get_score_trend
from shared.validators import (
    VALID_RISK_LEVELS,
    parse_int_arg,
    validate_allowed,
    validate_area_code,
    validate_int_range,
    validate_page,
    validate_page_size,
    validate_score_range,
    validate_zjhm,
)


@score_bp.route("/<zjhm>", methods=["GET"])
def score_detail(zjhm):
    if not validate_zjhm(zjhm):
        return jsonify({"error": "invalid_zjhm", "message": "证件号格式不正确"}), 400

    result = get_score(zjhm)
    if not result:
        return jsonify({"error": "not_found", "message": "未找到该人员评分"}), 404
    return jsonify(result)


@score_bp.route("/list", methods=["GET"])
def score_list():
    min_score = parse_int_arg(request.args.get("min_score"), 0)
    max_score = parse_int_arg(request.args.get("max_score"), 100)
    risk_level = request.args.get("risk_level", "").strip() or None
    area_code = request.args.get("area_code", "").strip() or None
    page = parse_int_arg(request.args.get("page"), 1)
    size = parse_int_arg(request.args.get("size"), 20)
    sort = request.args.get("sort", "desc")

    if not validate_score_range(min_score, max_score):
        return jsonify({"error": "invalid_score_range", "message": "分数范围必须为 0-100 且 min_score <= max_score"}), 400
    if risk_level and not validate_allowed(risk_level, VALID_RISK_LEVELS):
        return jsonify({"error": "invalid_risk_level"}), 400
    if not validate_area_code(area_code):
        return jsonify({"error": "invalid_area_code"}), 400
    if not validate_page(page):
        return jsonify({"error": "invalid_page"}), 400
    if not validate_page_size(size):
        return jsonify({"error": "invalid_size"}), 400
    if not validate_allowed(sort, {"asc", "desc"}):
        return jsonify({"error": "invalid_sort"}), 400

    total, items = get_score_list(min_score, max_score, risk_level, area_code, page, size, sort)
    return jsonify({"total": total, "page": page, "size": size, "items": items})


@score_bp.route("/trend/<zjhm>", methods=["GET"])
def score_trend(zjhm):
    if not validate_zjhm(zjhm):
        return jsonify({"error": "invalid_zjhm", "message": "证件号格式不正确"}), 400

    months = parse_int_arg(request.args.get("months"), 6)
    if not validate_int_range(months, 1, 60):
        return jsonify({"error": "invalid_months"}), 400

    points = get_score_trend(zjhm, months)
    return jsonify({"zjhm": zjhm, "months": months, "points": points})


@score_bp.route("/recalculate", methods=["POST"])
@score_bp.route("/batch-recalculate", methods=["POST"])
def recalculate():
    data = request.get_json(silent=True) or {}
    zjhm = data.get("zjhm", "all")

    if zjhm and zjhm != "all":
        if not validate_zjhm(zjhm):
            return jsonify({"error": "invalid_zjhm", "message": "证件号格式不正确"}), 400
        result = calculate_score(zjhm)
        return jsonify({"status": "done", "result": result})

    thread = threading.Thread(target=batch_recalculate, daemon=True)
    thread.start()
    return jsonify({"status": "started", "message": "全量重算已启动，后台执行中"})
