from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from modules.graph.services.algo_service import detect_gangs, get_gang_detail, list_gangs, predict_links
from modules.graph.services.etl_service import (
    get_graph_backend_status,
    get_latest_sync_summary,
    get_person_subgraph,
    get_person_trajectory,
)
from shared.ownership.ownership import get_request_owner
from shared.task_queue import get_task, submit_task


graph_bp = Blueprint("graph", __name__)


def _parse_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _parse_int(value, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@graph_bp.get("/graph")
def graph_page():
    return render_template("modules/graph/index.html")


@graph_bp.get("/api/graph/status")
def graph_status():
    return jsonify(get_graph_backend_status())


@graph_bp.post("/api/graph/sync")
def graph_sync_submit():
    owner_key, owner_ip = get_request_owner(request)
    payload = request.get_json(silent=True) or request.form or {}
    limit = _parse_int(payload.get("limit"))
    theft_only = _parse_bool(payload.get("theft_only"), True)
    incremental = _parse_bool(payload.get("incremental"), False)
    task_id = submit_task(
        "graph_sync",
        payload={"limit": limit, "theft_only": theft_only, "incremental": incremental},
        owner_key=owner_key,
        owner_ip=owner_ip,
    )
    return jsonify({"ok": True, "task_id": task_id, "task_type": "graph_sync", "limit": limit, "theft_only": theft_only, "incremental": incremental})


@graph_bp.get("/api/graph/sync/status")
def graph_sync_status():
    task_id = str(request.args.get("task_id", "") or "").strip()
    try:
        sync_summary = get_latest_sync_summary()
    except Exception as exc:
        sync_summary = {"table_ready": False, "error": str(exc)}
    if task_id:
        task = get_task(task_id)
        if task is None:
            return jsonify({"ok": False, "error": "task not found"}), 404
        return jsonify({"ok": True, "task": task, "latest_sync": sync_summary})
    return jsonify({"ok": True, "latest_sync": sync_summary})


@graph_bp.post("/api/graph/detect-gangs")
def graph_detect_submit():
    owner_key, owner_ip = get_request_owner(request)
    payload = request.get_json(silent=True) or request.form or {}
    min_size = max(2, _parse_int(payload.get("min_size"), 2) or 2)
    task_id = submit_task(
        "graph_detect",
        payload={"min_size": min_size},
        owner_key=owner_key,
        owner_ip=owner_ip,
    )
    return jsonify({"ok": True, "task_id": task_id, "task_type": "graph_detect", "min_size": min_size})


@graph_bp.get("/api/graph/gangs")
def graph_gangs():
    limit = max(1, min(_parse_int(request.args.get("limit"), 20) or 20, 200))
    run_id = str(request.args.get("run_id", "") or "").strip()
    return jsonify(list_gangs(limit=limit, run_id=run_id))


@graph_bp.get("/api/graph/gangs/<gang_id>")
def graph_gang_detail(gang_id: str):
    run_id = str(request.args.get("run_id", "") or "").strip()
    detail = get_gang_detail(gang_id, run_id=run_id)
    if detail is None:
        return jsonify({"ok": False, "error": "gang not found"}), 404
    return jsonify(detail)


@graph_bp.get("/api/graph/person/<sfzh>")
def graph_person(sfzh: str):
    result = get_person_subgraph(sfzh)
    status_code = 200 if result.get("ok") else 404
    return jsonify(result), status_code


@graph_bp.get("/api/graph/person/<sfzh>/trajectory")
def graph_person_trajectory(sfzh: str):
    limit = max(1, min(_parse_int(request.args.get("limit"), 200) or 200, 1000))
    return jsonify(get_person_trajectory(sfzh, limit=limit))


@graph_bp.post("/api/graph/detect-gangs/run-now")
def graph_detect_run_now():
    payload = request.get_json(silent=True) or request.form or {}
    min_size = max(2, _parse_int(payload.get("min_size"), 2) or 2)
    return jsonify(detect_gangs(min_size=min_size))


@graph_bp.get("/api/graph/predict-links")
def graph_predict_links():
    limit = max(1, min(_parse_int(request.args.get("limit"), 50) or 50, 500))
    min_common = max(1, _parse_int(request.args.get("min_common"), 2) or 2)
    return jsonify(predict_links(limit=limit, min_common=min_common))