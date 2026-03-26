import os
import threading
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from config import (
    BATCH_SIZE,
    CONF_THRESH,
    IMGSZ,
    MODEL_DEFAULT,
    MODEL_REGISTRY,
    get_train_base_model_options,
    get_upload_model_default,
    get_upload_model_options,
)
from db.oracle import fetch_image_urls
from db.sqlite import get_job as get_saved_job
from db.sqlite import list_jobs as list_saved_jobs
from service.face_library_service import get_face_library_status
from service.result_store_service import (
    attach_identity_to_manifest_items,
    load_identity_report,
    load_result_manifest,
)
from service.job_service import (
    JOBS,
    JOBS_LOCK,
    _new_job_record,
    _run_job,
    get_job_snapshot,
    list_running_jobs,
    request_cancel,
)
from utils.helpers import (
    default_time_range,
    ensure_hours_list,
    format_timestamp,
    parse_and_normalize_dt,
    to_datetime_local_str,
)
from utils.ownership import get_request_owner, job_matches_owner


job_bp = Blueprint("job", __name__)


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


def _is_visible_job(record: dict | None, owner_key: str, owner_ip: str) -> bool:
    return job_matches_owner(record, owner_key, owner_ip)


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
    with JOBS_LOCK:
        job = _new_job_record(total=len(url_and_times))
        job["owner_key"] = owner_key
        job["owner_ip"] = owner_ip
        job["model_key"] = model_key
        for running_job in JOBS.values():
            if running_job.get("status") == "running" and job_matches_owner(running_job, owner_key, owner_ip):
                running_job["cancel"].set()
        JOBS[job["id"]] = job
        job_id = job["id"]

    thread = threading.Thread(
        target=_run_job,
        args=(job_id, url_and_times, conf_val, batch_val, imgsz_val, classes_raw, model_key),
        daemon=True,
    )
    thread.start()
    return jsonify({"ok": True, "job_id": job_id, "total": len(url_and_times)})


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


@job_bp.get("/history")
def history():
    owner_key, owner_ip = get_request_owner(request)
    limit_raw = request.args.get("limit", "50")
    try:
        limit = int(limit_raw)
    except Exception:
        limit = 50

    records = list_saved_jobs(owner_key, owner_ip, limit=limit)
    items = [_history_summary_payload(record) for record in records]
    return jsonify({"ok": True, "jobs": items})


@job_bp.get("/history-page")
def history_page():
    return render_template("history.html")


@job_bp.get("/history-page/<job_id>")
def history_detail_page(job_id: str):
    return render_template("history_detail.html", job_id=job_id)


@job_bp.get("/history/<job_id>")
def history_detail(job_id: str):
    owner_key, owner_ip = get_request_owner(request)
    record = get_saved_job(job_id)
    if not job_matches_owner(record, owner_key, owner_ip):
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
            items.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "origin_name": item.get("origin_name") or item.get("name"),
                    "size_bytes": item.get("size_bytes", 0),
                    "asset_url": url_for("face.result_asset", job_id=job_id, asset_id=item.get("id")),
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
        "library": get_face_library_status(),
    }
    return jsonify(payload)
