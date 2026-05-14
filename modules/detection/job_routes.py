import json
import os
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from shared.config.config import (
    BATCH_SIZE,
    CONF_THRESH,
    IMGSZ,
    MODEL_DEFAULT,
    MODEL_REGISTRY,
    get_train_base_model_options,
    get_upload_model_default,
    get_upload_model_options,
)
from shared.db.oracle import fetch_image_urls
from shared.db.sqlite import get_job as get_saved_job
from shared.db.sqlite import list_all_jobs as list_all_saved_jobs
from modules.detection.repositories import ai_result_repository as structured_repo
from modules.detection.services.job_service import (
    get_job_snapshot,
    list_running_jobs,
    request_cancel,
    start_detection_job,
)
from modules.detection.services.result_store_service import (
    attach_identity_to_manifest_items,
    load_identity_report,
    load_result_manifest,
)
from shared.utils.helpers import (
    default_time_range,
    ensure_hours_list,
    format_timestamp,
    parse_and_normalize_dt,
    to_datetime_local_str,
)
from shared.ownership.ownership import get_request_owner, job_matches_owner


job_bp = Blueprint("job", __name__)
list_saved_jobs = list_all_saved_jobs


def _get_face_library_status() -> dict:
    """Lazy import to avoid circular dependency on face module at import time."""
    from modules.face.services.library_service import get_face_library_status
    return get_face_library_status()


def _progress_payload(job: dict) -> dict:
    data = {
        key: job.get(key)
        for key in (
            "id",
            "status",
            "message",
            "total",
            "processed",
            "kept",
            "notfound",
            "failed",
            "downloaded",
            "start_ts",
            "end_ts",
            "owner_ip",
            "model_key",
        )
    }
    data["zip_parts_count"] = len(job.get("zip_parts") or [])
    return data


def _history_summary_payload(record: dict) -> dict:
    identity_summary = record.get("identity_summary") or {}
    return {
        "id": record.get("id"),
        "job_type": record.get("job_type", "oracle"),
        "source_name": record.get("source_name", ""),
        "source_type": record.get("source_type", ""),
        "start_ts": format_timestamp(record.get("start_ts")),
        "end_ts": format_timestamp(record.get("end_ts")),
        "status": record.get("status"),
        "kept": record.get("kept", 0),
        "total": record.get("total", 0),
        "zip_parts_count": len(record.get("zip_parts") or []),
        "model_key": record.get("model_key", MODEL_DEFAULT),
        "identity_summary": identity_summary,
        "detail_url": url_for("job.history_detail_page", job_id=record.get("id")),
        "download_url": url_for("file.download_zip", job_id=record.get("id")),
    }


def _parse_limit_arg(value: str, default: int, *, minimum: int = 1, maximum: int = 500) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(minimum, min(maximum, parsed))


def _serialize_structured_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except Exception:
                return value
    return value


def _serialize_structured_run(record: dict) -> dict:
    return {key: _serialize_structured_value(value) for key, value in dict(record).items()}


def _serialize_structured_detection(record: dict) -> dict:
    return {key: _serialize_structured_value(value) for key, value in dict(record).items()}


def _serialize_structured_media_asset(record: dict) -> dict:
    return {key: _serialize_structured_value(value) for key, value in dict(record).items()}


@job_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        return redirect(url_for("job.index"))

    kssj, jssj = default_time_range()
    try:
        kssj_dt = datetime.strptime(kssj, "%Y-%m-%d %H:%M:%S")
        jssj_dt = datetime.strptime(jssj, "%Y-%m-%d %H:%M:%S")
    except Exception:
        now = datetime.now()
        kssj_dt = now
        jssj_dt = now

    return render_template(
        "index.html",
        kssj=kssj,
        jssj=jssj,
        kssj_local=to_datetime_local_str(kssj_dt),
        jssj_local=to_datetime_local_str(jssj_dt),
        conf_default=CONF_THRESH,
        batch_default=BATCH_SIZE,
        imgsz_default=IMGSZ,
        model_default=MODEL_DEFAULT,
        upload_model_default=get_upload_model_default(),
        upload_models=get_upload_model_options(),
        train_base_models=get_train_base_model_options(),
    )


@job_bp.route("/start", methods=["GET", "POST", "OPTIONS"])
def start_job():
    if request.method == "OPTIONS":
        return ("", 204)

    form = request.form if request.method == "POST" else request.args
    kssj_in = (form.get("kssj", "") or "").strip()
    jssj_in = (form.get("jssj", "") or "").strip()
    hours_raw = request.form.getlist("hours") if request.method == "POST" else request.args.getlist("hours")
    hours = ensure_hours_list(hours_raw)

    conf_in = (form.get("conf", "") or "").strip()
    batch_in = (form.get("batch_size", "") or "").strip()
    imgsz_in = (form.get("imgsz", "") or "").strip()
    classes_raw = (form.get("classes", "") or "").strip()
    model_key = (form.get("model_key", MODEL_DEFAULT) or MODEL_DEFAULT).strip()

    if model_key not in MODEL_REGISTRY:
        return jsonify({"ok": False, "error": f"非法 model_key: {model_key}"}), 400

    try:
        kssj = parse_and_normalize_dt(kssj_in)
        jssj = parse_and_normalize_dt(jssj_in)
    except Exception:
        kssj = kssj_in
        jssj = jssj_in

    try:
        url_and_times = fetch_image_urls(kssj, jssj, hours, model_key)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"数据库查询失败: {exc}"}), 500

    if not url_and_times:
        return jsonify({"ok": False, "error": "未查询到图片 URL"}), 400

    conf_val = CONF_THRESH
    try:
        if conf_in:
            conf_val = max(0.0, min(1.0, float(conf_in)))
    except Exception:
        pass

    batch_val = BATCH_SIZE
    try:
        if batch_in:
            batch_val = max(1, int(batch_in))
    except Exception:
        pass

    imgsz_val = IMGSZ
    try:
        if imgsz_in:
            imgsz_val = max(64, int(imgsz_in))
    except Exception:
        pass

    owner_key, owner_ip = get_request_owner(request)
    job = start_detection_job(
        url_and_times,
        conf_val,
        batch_val,
        imgsz_val,
        classes_raw,
        model_key,
        owner_key,
        owner_ip,
    )
    return jsonify({"ok": True, "job_id": job["id"], "total": len(url_and_times)})


@job_bp.get("/progress/<job_id>")
def get_progress(job_id: str):
    owner_key, owner_ip = get_request_owner(request)
    job = get_job_snapshot(job_id)
    if job is not None:
        if not job_matches_owner(job, owner_key, owner_ip):
            return jsonify({"ok": False, "error": "job not found"}), 404
        return jsonify({"ok": True, "job": _progress_payload(job)})

    saved_job = get_saved_job(job_id)
    if saved_job is None or not job_matches_owner(saved_job, owner_key, owner_ip):
        return jsonify({"ok": False, "error": "job not found"}), 404
    return jsonify({"ok": True, "job": _progress_payload(saved_job)})


@job_bp.post("/cancel/<job_id>")
def cancel_job(job_id: str):
    owner_key, owner_ip = get_request_owner(request)
    if not request_cancel(job_id, owner_key, owner_ip):
        return jsonify({"ok": False, "error": "job not found"}), 404
    return jsonify({"ok": True})


@job_bp.get("/jobs")
def list_jobs():
    owner_key, owner_ip = get_request_owner(request)
    running = list_running_jobs(owner_key, owner_ip)
    return jsonify({"ok": True, "running_count": len(running), "running": running})


@job_bp.get("/detection/api/structured/runs")
def structured_run_list():
    limit = _parse_limit_arg(request.args.get("limit", "50"), 50)
    status = (request.args.get("status", "") or "").strip().lower() or None

    try:
        items = structured_repo.list_yolo_runs(limit=limit, status=status)
    except Exception as exc:
        logger.exception("failed to query structured yolo runs: %s", exc)
        return jsonify({"ok": False, "error": "structured run query failed"}), 500

    return jsonify(
        {
            "ok": True,
            "count": len(items),
            "items": [_serialize_structured_run(item) for item in items],
        }
    )


@job_bp.get("/detection/api/structured/runs/<run_id>")
def structured_run_detail(run_id: str):
    detection_limit = _parse_limit_arg(request.args.get("detection_limit", "100"), 100)

    try:
        run_record = structured_repo.get_yolo_run(run_id)
        if run_record is None:
            return jsonify({"ok": False, "error": "structured run not found"}), 404
        detections = structured_repo.list_yolo_detections(limit=detection_limit, run_id=run_id)
    except Exception as exc:
        logger.exception("failed to query structured yolo run %s: %s", run_id, exc)
        return jsonify({"ok": False, "error": "structured run query failed"}), 500

    return jsonify(
        {
            "ok": True,
            "run": _serialize_structured_run(run_record),
            "detections": [_serialize_structured_detection(item) for item in detections],
        }
    )


@job_bp.get("/detection/api/structured/detections")
def structured_detection_list():
    limit = _parse_limit_arg(request.args.get("limit", "100"), 100)
    filters = {
        "run_id": (request.args.get("run_id", "") or "").strip() or None,
        "label_code": (request.args.get("label_code", "") or "").strip() or None,
        "sfzh": (request.args.get("sfzh", "") or "").strip() or None,
        "start_time": (request.args.get("start_time", "") or "").strip() or None,
        "end_time": (request.args.get("end_time", "") or "").strip() or None,
        "source_system": (request.args.get("source_system", "") or "").strip() or None,
        "source_table": (request.args.get("source_table", "") or "").strip() or None,
        "review_status": (request.args.get("review_status", "") or "").strip().lower() or None,
    }

    try:
        items = structured_repo.list_yolo_detections(limit=limit, **filters)
    except Exception as exc:
        logger.exception("failed to query structured yolo detections: %s", exc)
        return jsonify({"ok": False, "error": "structured detection query failed"}), 500

    return jsonify(
        {
            "ok": True,
            "count": len(items),
            "filters": filters,
            "items": [_serialize_structured_detection(item) for item in items],
        }
    )


@job_bp.get("/detection/api/structured/assets")
def structured_media_asset_list():
    limit = _parse_limit_arg(request.args.get("limit", "100"), 100)
    filters = {
        "asset_id": (request.args.get("asset_id", "") or "").strip() or None,
        "parent_asset_id": (request.args.get("parent_asset_id", "") or "").strip() or None,
        "source_system": (request.args.get("source_system", "") or "").strip() or None,
        "source_table": (request.args.get("source_table", "") or "").strip() or None,
        "media_type": (request.args.get("media_type", "") or "").strip().lower() or None,
        "detect_status": (request.args.get("detect_status", "") or "").strip().lower() or None,
    }

    try:
        items = structured_repo.list_media_assets(limit=limit, **filters)
    except Exception as exc:
        logger.exception("failed to query structured media assets: %s", exc)
        return jsonify({"ok": False, "error": "structured media asset query failed"}), 500

    return jsonify(
        {
            "ok": True,
            "count": len(items),
            "filters": filters,
            "items": [_serialize_structured_media_asset(item) for item in items],
        }
    )


@job_bp.get("/detection/api/structured/assets/<asset_id>/lineage")
def structured_media_asset_lineage(asset_id: str):
    child_limit = _parse_limit_arg(request.args.get("child_limit", "200"), 200)

    try:
        asset = structured_repo.get_media_asset(asset_id)
        if asset is None:
            return jsonify({"ok": False, "error": "structured media asset not found"}), 404
        parent = None
        parent_asset_id = str(asset.get("parent_asset_id") or "").strip()
        if parent_asset_id:
            parent = structured_repo.get_media_asset(parent_asset_id)
        children = structured_repo.list_media_assets(limit=child_limit, parent_asset_id=asset_id)
    except Exception as exc:
        logger.exception("failed to query structured media asset lineage %s: %s", asset_id, exc)
        return jsonify({"ok": False, "error": "structured media asset lineage query failed"}), 500

    return jsonify(
        {
            "ok": True,
            "asset": _serialize_structured_media_asset(asset),
            "parent": _serialize_structured_media_asset(parent) if parent else None,
            "children": [_serialize_structured_media_asset(item) for item in children],
        }
    )


@job_bp.post("/detection/api/structured/detections/<detection_id>/review")
def structured_detection_review_update(detection_id: str):
    payload = request.get_json(silent=True) or request.form or {}
    review_status = (payload.get("review_status", "") or "").strip().lower()
    review_result = (payload.get("review_result", "") or "").strip().lower() or None

    if review_status not in structured_repo.VALID_REVIEW_STATUSES:
        allowed = ", ".join(sorted(structured_repo.VALID_REVIEW_STATUSES))
        return jsonify({"ok": False, "error": f"invalid review_status, allowed: {allowed}"}), 400
    if review_result and review_result not in structured_repo.VALID_REVIEW_RESULTS:
        allowed = ", ".join(sorted(structured_repo.VALID_REVIEW_RESULTS))
        return jsonify({"ok": False, "error": f"invalid review_result, allowed: {allowed}"}), 400

    try:
        item = structured_repo.update_yolo_detection_review(
            detection_id,
            review_status=review_status,
            review_result=review_result,
            reviewer_id=(payload.get("reviewer_id", "") or "").strip() or None,
            reviewer_name=(payload.get("reviewer_name", "") or "").strip() or None,
            review_comment=(payload.get("review_comment", "") or "").strip() or None,
        )
        if item is None:
            return jsonify({"ok": False, "error": "structured detection not found"}), 404
        training_sample = None
        if review_result in {"true_positive", "false_positive", "false_negative"}:
            training_sample = structured_repo.sync_training_sample_from_detection_review(detection_id)
    except Exception as exc:
        logger.exception("failed to update structured yolo detection review %s: %s", detection_id, exc)
        return jsonify({"ok": False, "error": "structured detection review update failed"}), 500

    return jsonify(
        {
            "ok": True,
            "message": "复核结果已更新",
            "item": _serialize_structured_detection(item),
            "training_sample": training_sample,
        }
    )


@job_bp.get("/history")
def history():
    limit_raw = request.args.get("limit", "50")
    try:
        limit = int(limit_raw)
    except Exception:
        limit = 50

    owner_key, owner_ip = get_request_owner(request)
    records = list_saved_jobs(owner_key, owner_ip, limit=limit)
    items = [_history_summary_payload(record) for record in records]
    return jsonify({"ok": True, "jobs": items})


@job_bp.get("/history-page")
def history_page():
    return render_template("modules/detection/history/history.html")


@job_bp.get("/history-page/<job_id>")
def history_detail_page(job_id: str):
    return render_template("modules/detection/history/history_detail.html", job_id=job_id)


@job_bp.get("/history/<job_id>")
def history_detail(job_id: str):
    record = get_saved_job(job_id)
    if record is None:
        return jsonify({"ok": False, "error": "job not found"}), 404

    manifest = None
    manifest_path = record.get("result_manifest_path")
    if manifest_path and os.path.isfile(manifest_path):
        try:
            manifest = load_result_manifest(manifest_path)
        except Exception:
            manifest = None

    identity_report = {"summary": {}, "items": []}
    identity_path = record.get("identity_result_path")
    if identity_path and os.path.isfile(identity_path):
        try:
            identity_report = load_identity_report(identity_path)
        except Exception:
            identity_report = {"summary": {}, "items": []}

    items = []
    if manifest is not None:
        for item in attach_identity_to_manifest_items(manifest, identity_report):
            structured_asset_id = str(item.get("structured_asset_id") or "").strip()
            items.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "origin_name": item.get("origin_name") or item.get("name"),
                    "size_bytes": item.get("size_bytes", 0),
                    "asset_url": url_for("face.result_asset", job_id=job_id, asset_id=item.get("id")),
                    "structured_asset_id": structured_asset_id,
                    "structured_lineage_url": url_for("job.structured_media_asset_lineage", asset_id=structured_asset_id) if structured_asset_id else "",
                    "identity": item.get("identity"),
                }
            )

    payload = {
        "ok": True,
        "job": {
            **_history_summary_payload(record),
            "message": record.get("message", ""),
            "downloaded": record.get("downloaded", 0),
            "notfound": record.get("notfound", 0),
            "failed": record.get("failed", 0),
            "summary_text": record.get("summary_text", ""),
            "result_count": len(items),
            "summary_url": url_for("file.download_summary", job_id=job_id),
            "download_parts": [
                {
                    "name": part.get("name"),
                    "url": url_for("file.download_zip_part", job_id=job_id, part=part.get("name")),
                }
                for part in (record.get("zip_parts") or [])
                if part.get("name")
            ] if len(record.get("zip_parts") or []) > 1 else [],
        },
        "items": items,
        "identity_summary": identity_report.get("summary") or (record.get("identity_summary") or {}),
        "library": _get_face_library_status(),
    }
    return jsonify(payload)


@job_bp.get("/api/dashboard/stats")
def dashboard_stats():
    """Return real-time header stats: today's identity matches and pending dispatch count."""
    import sqlite3 as _sqlite3
    import time as _time
    from shared.config.config import SQLITE_DB_PATH as _DB_PATH

    owner_key, owner_ip = get_request_owner(request)

    today_start = int(_time.time()) - (_time.time() % 86400)  # midnight UTC approx
    # More accurate: midnight local calendar day
    import datetime as _dt
    now_local = _dt.datetime.now()
    today_midnight = _dt.datetime(now_local.year, now_local.month, now_local.day).timestamp()

    today_matched = 0
    pending_dispatch = 0

    try:
        conn = _sqlite3.connect(_DB_PATH, timeout=5)
        conn.row_factory = _sqlite3.Row

        # "今日命中" = dispatch_queue entries created today for this user
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM dispatch_queue WHERE created_ts >= ? AND (owner_key=? OR owner_ip=?)",
            (int(today_midnight), owner_key, owner_ip),
        ).fetchone()
        today_matched = row["cnt"] if row else 0

        # "待下发" = dispatch_queue entries pending for this user
        row2 = conn.execute(
            "SELECT COUNT(*) AS cnt FROM dispatch_queue WHERE dispatch_status='pending' AND (owner_key=? OR owner_ip=?)",
            (owner_key, owner_ip),
        ).fetchone()
        pending_dispatch = row2["cnt"] if row2 else 0

        conn.close()
    except Exception:
        pass

    return jsonify({"ok": True, "today_matched": today_matched, "pending_dispatch": pending_dispatch})
