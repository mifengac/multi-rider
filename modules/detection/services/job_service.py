import io
import os
import threading
import time
import zipfile
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime
from typing import Optional, Set
from uuid import uuid4

from PIL import Image

from shared.config.config import (
    BATCH_SIZE,
    CONF_THRESH,
    IMGSZ,
    MAX_WORKERS,
    MODEL_DEFAULT,
    OUTPUT_DIR,
    logger,
)
from shared.db.sqlite import save_job
from modules.detection.services.result_store_service import add_result_bytes, create_result_store, finalize_result_store
from shared.inference.infer_service import _predict_batch, download_image_with_status, get_model
from shared.ownership.ownership import job_matches_owner
from shared.utils.helpers import filename_from_url, format_timestamp, infer_ext_from_bytes


JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _job_snapshot(job: dict) -> dict:
    snapshot = {key: value for key, value in job.items() if key != "cancel"}
    if "zip_parts" in snapshot:
        snapshot["zip_parts"] = [dict(part) for part in snapshot["zip_parts"]]
    return snapshot


def get_job_snapshot(job_id: str) -> dict | None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return None
        return _job_snapshot(job)


def list_running_jobs(owner_key: str = "", owner_ip: str = "") -> list[dict]:
    with JOBS_LOCK:
        return [
            {
                "id": job.get("id"),
                "start_ts": job.get("start_ts"),
                "total": job.get("total"),
                "processed": job.get("processed"),
                "status": job.get("status"),
                "model_key": job.get("model_key", MODEL_DEFAULT),
            }
            for job in JOBS.values()
            if job.get("status") == "running"
            and job_matches_owner(job, owner_key, owner_ip)
        ]


def request_cancel(job_id: str, owner_key: str = "", owner_ip: str = "") -> bool:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None or not job_matches_owner(job, owner_key, owner_ip):
            return False
        job["cancel"].set()
        return True


def _save_terminal_job(snapshot: dict) -> None:
    try:
        save_job(snapshot)
    except Exception as exc:
        logger.exception("failed to persist job %s: %s", snapshot.get("id"), exc)


def _new_job_record(total: int) -> dict:
    return {
        "job_type": "oracle",
        "id": uuid4().hex,
        "source_name": "oracle",
        "source_type": "oracle",
        "status": "running",
        "message": "",
        "total": total,
        "processed": 0,
        "downloaded": 0,
        "kept": 0,
        "notfound": 0,
        "failed": 0,
        "start_ts": int(time.time()),
        "end_ts": None,
        "owner_key": "",
        "zip_bytes": None,
        "zip_path": None,
        "zip_parts": [],
        "summary_text": "",
        "result_dir": "",
        "result_manifest_path": "",
        "conf_thresh": CONF_THRESH,
        "batch_size": BATCH_SIZE,
        "imgsz": IMGSZ,
        "classes": None,
        "classes_raw": "",
        "model_key": MODEL_DEFAULT,
        "owner_ip": "",
        "cancel": threading.Event(),
    }


def _summarize(job: dict) -> str:
    downloaded = (
        job.get("downloaded")
        if job.get("downloaded") is not None
        else max(0, job["processed"] - job["notfound"] - job["failed"])
    )
    discarded = max(0, downloaded - job["kept"])
    threshold = job.get("conf_thresh", CONF_THRESH)
    lines = [
        f"模型: {job.get('model_key', MODEL_DEFAULT)}",
        f"总 URL 数: {job['total']}",
        f"已处理: {job['processed']}",
        f"下载成功: {downloaded}",
        f"置信度 >= {threshold}（保留）: {job['kept']}",
        f"置信度 < {threshold}（丢弃）: {discarded}",
        f"404 Not Found: {job['notfound']}",
        f"其他失败: {job['failed']}",
        f"开始时间: {format_timestamp(job.get('start_ts'))}",
        f"结束时间: {format_timestamp(job.get('end_ts'))}",
    ]
    return "\n".join(lines) + "\n"


def _run_job(
    job_id: str,
    url_and_times: list[tuple[str, str]],
    conf_thresh: float,
    batch_size: int,
    imgsz: int,
    classes_raw: str,
    model_key: str,
) -> None:
    try:
        model = get_model(model_key)
        result_store = create_result_store(job_id, "oracle", "oracle", "oracle")
        allowed_classes: Optional[Set[int]] = None
        prompt_classes: list[str] | None = None

        if model_key == "general":
            prompt_classes = [item.strip() for item in classes_raw.split(",") if item.strip()] or None
        else:
            names = getattr(model, "names", None)
            if classes_raw and names:
                indexes: Set[int] = set()
                if isinstance(names, dict):
                    name_map = {str(value).lower(): int(key) for key, value in names.items()}
                else:
                    name_map = {str(value).lower(): index for index, value in enumerate(names)}

                for token in [item.strip() for item in classes_raw.split(",") if item.strip()]:
                    if token.isdigit():
                        indexes.add(int(token))
                    else:
                        mapped = name_map.get(token.lower())
                        if mapped is not None:
                            indexes.add(int(mapped))
                if indexes:
                    allowed_classes = indexes

        with JOBS_LOCK:
            job = JOBS[job_id]
            job["conf_thresh"] = conf_thresh
            job["batch_size"] = batch_size
            job["imgsz"] = imgsz
            job["classes_raw"] = classes_raw
            job["model_key"] = model_key
            job["classes"] = allowed_classes if model_key == "bczj" else prompt_classes

        def time_bin_key(time_str: str) -> str:
            try:
                if time_str:
                    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    return dt.strftime("%Y%m%d")
            except Exception:
                pass
            return "unknown"

        def gen_downloads():
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                iterator = iter(url_and_times)
                in_flight = {}
                max_in_flight = max(1, MAX_WORKERS * 2)

                def submit_one(item: tuple[str, str]) -> None:
                    url, ts = item
                    future = executor.submit(download_image_with_status, url)
                    in_flight[future] = (url, ts)

                for _ in range(max_in_flight):
                    item = next(iterator, None)
                    if item is None:
                        break
                    submit_one(item)

                while in_flight:
                    with JOBS_LOCK:
                        if JOBS[job_id]["cancel"].is_set():
                            return

                    done, _ = wait(set(in_flight.keys()), return_when=FIRST_COMPLETED)
                    for future in done:
                        url, ts = in_flight.pop(future)
                        try:
                            data, code, _content_type = future.result()
                        except Exception:
                            data, code = None, None

                        if data is None:
                            with JOBS_LOCK:
                                current = JOBS[job_id]
                                if code == 404:
                                    current["notfound"] += 1
                                else:
                                    current["failed"] += 1
                        else:
                            with JOBS_LOCK:
                                JOBS[job_id]["downloaded"] += 1
                            name = filename_from_url(url)
                            root, ext = os.path.splitext(name)
                            if not ext:
                                ext = infer_ext_from_bytes(data)
                                name = root + ext
                            yield name, data, ts

                        item = next(iterator, None)
                        if item is not None:
                            submit_one(item)

        zip_files: dict[str, zipfile.ZipFile] = {}

        def get_zip_for_key(key: str) -> zipfile.ZipFile:
            zip_handle = zip_files.get(key)
            if zip_handle is None:
                path = os.path.join(OUTPUT_DIR, f"{job_id}_{key}.zip")
                zip_handle = zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED)
                zip_files[key] = zip_handle
            return zip_handle

        sequence = 0
        images: list[Image.Image] = []
        payloads: list[tuple[str, bytes]] = []
        bins: list[str] = []

        for name, image_bytes, time_str in gen_downloads():
            with JOBS_LOCK:
                if JOBS[job_id]["cancel"].is_set():
                    break

            try:
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            except Exception:
                with JOBS_LOCK:
                    JOBS[job_id]["failed"] += 1
                continue

            images.append(image)
            payloads.append((name, image_bytes))
            bins.append(time_bin_key(time_str))

            if len(images) >= batch_size:
                keeps = _predict_batch(
                    images,
                    model,
                    conf_thresh,
                    allowed_classes,
                    imgsz,
                    model_key,
                    prompt_classes,
                )
                for index, ((filename, payload), keep) in enumerate(zip(payloads, keeps)):
                    with JOBS_LOCK:
                        JOBS[job_id]["processed"] += 1
                    if keep:
                        sequence += 1
                        output_name = f"{sequence:07d}_{filename}"
                        zip_file = get_zip_for_key(bins[index])
                        zip_file.writestr(output_name, payload)
                        add_result_bytes(
                            result_store,
                            output_name,
                            payload,
                            extra={"origin_name": filename, "group_key": bins[index]},
                        )
                        with JOBS_LOCK:
                            JOBS[job_id]["kept"] += 1

                for image in images:
                    try:
                        image.close()
                    except Exception:
                        pass
                images.clear()
                payloads.clear()
                bins.clear()

                with JOBS_LOCK:
                    if JOBS[job_id]["cancel"].is_set():
                        break

        if images:
            keeps = _predict_batch(
                images,
                model,
                conf_thresh,
                allowed_classes,
                imgsz,
                model_key,
                prompt_classes,
            )
            for index, ((filename, payload), keep) in enumerate(zip(payloads, keeps)):
                with JOBS_LOCK:
                    JOBS[job_id]["processed"] += 1
                if keep:
                    sequence += 1
                    output_name = f"{sequence:07d}_{filename}"
                    zip_file = get_zip_for_key(bins[index])
                    zip_file.writestr(output_name, payload)
                    add_result_bytes(
                        result_store,
                        output_name,
                        payload,
                        extra={"origin_name": filename, "group_key": bins[index]},
                    )
                    with JOBS_LOCK:
                        JOBS[job_id]["kept"] += 1

            for image in images:
                try:
                    image.close()
                except Exception:
                    pass

        with JOBS_LOCK:
            current = JOBS[job_id]
            current["end_ts"] = int(time.time())
            if current["cancel"].is_set() and current["status"] == "running":
                current["status"] = "canceled"
                current["message"] = "任务已取消"
            current["summary_text"] = _summarize(current)
            summary_text = current["summary_text"]

        zip_parts = []
        for zip_handle in list(zip_files.values()):
            try:
                zip_handle.writestr("summary.txt", summary_text)
            except Exception:
                pass
            path = zip_handle.filename
            try:
                zip_handle.close()
            except Exception:
                pass
            zip_parts.append(path)

        manifest_path = finalize_result_store(result_store)

        with JOBS_LOCK:
            current = JOBS[job_id]
            current["zip_parts"] = [{"path": path, "name": os.path.basename(path)} for path in zip_parts]
            current["zip_path"] = zip_parts[0] if len(zip_parts) == 1 else None
            current["result_dir"] = result_store["result_dir"]
            current["result_manifest_path"] = manifest_path
            if current["status"] == "running":
                current["status"] = "done"
            snapshot = _job_snapshot(current)

        _save_terminal_job(snapshot)
    except Exception as exc:
        logger.exception("job failed: %s", exc)
        with JOBS_LOCK:
            current = JOBS.get(job_id)
            if current is not None:
                current["status"] = "error"
                current["message"] = str(exc)
                current["end_ts"] = int(time.time())
                current["summary_text"] = _summarize(current)
                snapshot = _job_snapshot(current)
            else:
                snapshot = None
        if snapshot is not None:
            _save_terminal_job(snapshot)
