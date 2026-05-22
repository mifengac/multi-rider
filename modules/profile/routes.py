from flask import request, jsonify
from . import profile_bp
from .services.profile_assembler import assemble_profile, get_photo, get_featured_people
from .services.trajectory_service import (
    get_recent_trajectory, get_hotspots, get_time_pattern, get_last_seen,
)
from .services.timeline_service import build_timeline
from .services.suggestion_engine import generate_suggestions
from shared.validators import parse_int_arg, validate_int_range, validate_zjhm


@profile_bp.route("/featured", methods=["GET"])
def profile_featured():
    """Demo helper: list monitored people ordered by risk, no zjhm needed."""
    limit = parse_int_arg(request.args.get("limit"), 12)
    if not validate_int_range(limit, 1, 60):
        limit = 12
    return jsonify({"items": get_featured_people(limit)})


@profile_bp.route("/<zjhm>", methods=["GET"])
def profile_detail(zjhm):
    if not validate_zjhm(zjhm):
        return jsonify({"error": "invalid_zjhm", "message": "证件号格式不正确"}), 400

    profile = assemble_profile(zjhm)
    if not profile:
        return jsonify({"error": "not_found", "message": "未找到该人员信息"}), 404

    profile["trajectory"] = {
        "recent": get_recent_trajectory(zjhm, days=30),
        "hotspots": get_hotspots(zjhm),
        "time_pattern": get_time_pattern(zjhm),
        "last_seen": get_last_seen(zjhm),
    }
    profile["suggestions"] = generate_suggestions(profile)
    return jsonify(profile)


@profile_bp.route("/<zjhm>/trajectory", methods=["GET"])
def profile_trajectory(zjhm):
    if not validate_zjhm(zjhm):
        return jsonify({"error": "invalid_zjhm", "message": "证件号格式不正确"}), 400

    days = parse_int_arg(request.args.get("days"), 30)
    if not validate_int_range(days, 1, 365):
        return jsonify({"error": "invalid_days"}), 400

    return jsonify({
        "recent": get_recent_trajectory(zjhm, days),
        "hotspots": get_hotspots(zjhm, days),
        "time_pattern": get_time_pattern(zjhm, days),
        "last_seen": get_last_seen(zjhm),
    })


@profile_bp.route("/<zjhm>/timeline", methods=["GET"])
def profile_timeline(zjhm):
    if not validate_zjhm(zjhm):
        return jsonify({"error": "invalid_zjhm", "message": "证件号格式不正确"}), 400

    return jsonify({"items": build_timeline(zjhm)})


@profile_bp.route("/<zjhm>/photo", methods=["GET"])
def profile_photo(zjhm):
    if not validate_zjhm(zjhm):
        return jsonify({"error": "invalid_zjhm", "message": "证件号格式不正确"}), 400

    photo = get_photo(zjhm)
    if not photo:
        return jsonify({"error": "not_found"}), 404
    return jsonify(photo)
