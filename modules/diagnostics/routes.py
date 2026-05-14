from __future__ import annotations

import json
import os

from flask import Blueprint, jsonify, request

from shared.config.config import logger
from shared.config.config import BASE_DIR
from shared.health import get_health_report
from shared.task_queue_diagnostics import get_task_queue_snapshot


diagnostics_bp = Blueprint("diagnostics", __name__, url_prefix="/diagnostics")


@diagnostics_bp.get("/task-queue")
def task_queue_diagnostics():
    task_type = (request.args.get("task_type") or "").strip() or None
    status = (request.args.get("status") or "").strip() or None
    limit = request.args.get("limit")
    try:
        snapshot = get_task_queue_snapshot(task_type=task_type, status=status, limit=limit)
        health = get_health_report()
    except Exception as exc:
        logger.exception("failed to load task queue diagnostics: %s", exc)
        return jsonify({"ok": False, "error": "failed to load task queue diagnostics"}), 500

    snapshot["health"] = {
        "ok": bool(health.get("ok")),
        "task_queue": (health.get("checks") or {}).get("task_queue") or {},
    }
    return jsonify({"ok": True, **snapshot})


@diagnostics_bp.get("/benchmarks")
def benchmark_results():
    limit_raw = request.args.get("limit", "20")
    try:
        limit = max(1, min(int(limit_raw or 20), 100))
    except Exception:
        limit = 20
    bench_dir = os.path.join(BASE_DIR, "runtime", "benchmarks")
    if not os.path.isdir(bench_dir):
        return jsonify({"ok": True, "items": [], "directory": bench_dir})
    files = [
        os.path.join(bench_dir, name)
        for name in os.listdir(bench_dir)
        if name.lower().endswith(".json")
    ]
    files.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    items = []
    for path in files[:limit]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            items.append(
                {
                    "file": os.path.basename(path),
                    "path": path,
                    "benchmark_id": payload.get("benchmark_id"),
                    "scenario": payload.get("scenario"),
                    "created_at": payload.get("created_at"),
                    "metrics": payload.get("metrics") or {},
                }
            )
        except Exception as exc:
            logger.warning("failed to read benchmark result %s: %s", path, exc)
    return jsonify({"ok": True, "items": items, "directory": bench_dir})
