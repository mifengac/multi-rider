import threading
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from config import (
    BATCH_SIZE,
    CONF_THRESH,
    IMGSZ,
    MODEL_DEFAULT,
    MODEL_REGISTRY,
    get_upload_model_default,
    get_upload_model_options,
)
from db.oracle import fetch_image_urls
from db.sqlite import get_job as get_saved_job
from db.sqlite import list_jobs as list_saved_jobs
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


job_bp = Blueprint("job", __name__)


def _request_owner_ip() -> str:
    return request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or ""


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

    owner_ip = _request_owner_ip()
    with JOBS_LOCK:
        job = _new_job_record(total=len(url_and_times))
        job["owner_ip"] = owner_ip
        job["model_key"] = model_key
        for running_job in JOBS.values():
            if running_job.get("status") == "running" and running_job.get("owner_ip") == owner_ip:
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
    job = get_job_snapshot(job_id)
    if job is not None:
        return jsonify({"ok": True, "job": _progress_payload(job)})

    saved_job = get_saved_job(job_id)
    if saved_job is None:
        return jsonify({"ok": False, "error": "job not found"}), 404
    return jsonify({"ok": True, "job": _progress_payload(saved_job)})


@job_bp.post("/cancel/<job_id>")
def cancel_job(job_id: str):
    if not request_cancel(job_id):
        return jsonify({"ok": False, "error": "job not found"}), 404
    return jsonify({"ok": True})


@job_bp.get("/jobs")
def list_jobs():
    running = list_running_jobs()
    return jsonify({"ok": True, "running_count": len(running), "running": running})


@job_bp.get("/history")
def history():
    owner_ip = _request_owner_ip()
    limit_raw = request.args.get("limit", "50")
    try:
        limit = int(limit_raw)
    except Exception:
        limit = 50

    records = list_saved_jobs(owner_ip, limit=limit)
    items = []
    for record in records:
        items.append(
            {
                "id": record.get("id"),
                "start_ts": format_timestamp(record.get("start_ts")),
                "status": record.get("status"),
                "kept": record.get("kept", 0),
                "total": record.get("total", 0),
                "zip_parts_count": len(record.get("zip_parts") or []),
                "model_key": record.get("model_key", MODEL_DEFAULT),
            }
        )
    return jsonify({"ok": True, "jobs": items})


@job_bp.get("/history-page")
def history_page():
    return render_template("history.html")
