from flask import request, jsonify
from . import profile_bp
from .services.profile_assembler import assemble_profile, get_photo
from .services.trajectory_service import (
    get_recent_trajectory, get_hotspots, get_time_pattern, get_last_seen,
)
from .services.timeline_service import build_timeline
from .services.suggestion_engine import generate_suggestions


@profile_bp.route("/<zjhm>", methods=["GET"])
def profile_detail(zjhm):
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
    days = request.args.get("days", 30, type=int)
    return jsonify({
        "recent": get_recent_trajectory(zjhm, days),
        "hotspots": get_hotspots(zjhm, days),
        "time_pattern": get_time_pattern(zjhm, days),
        "last_seen": get_last_seen(zjhm),
    })


@profile_bp.route("/<zjhm>/timeline", methods=["GET"])
def profile_timeline(zjhm):
    return jsonify({"items": build_timeline(zjhm)})


@profile_bp.route("/<zjhm>/photo", methods=["GET"])
def profile_photo(zjhm):
    photo = get_photo(zjhm)
    if not photo:
        return jsonify({"error": "not_found"}), 404
    return jsonify(photo)
