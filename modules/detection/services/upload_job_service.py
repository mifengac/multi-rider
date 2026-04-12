import io
import os
import shutil
import threading
import time
import zipfile
from typing import Optional, Set
from uuid import uuid4

import cv2
from PIL import Image

from shared.config.config import (
    BATCH_SIZE,
    CONF_THRESH,
    IMGSZ,
    OUTPUT_DIR,
    get_upload_model_default,
    logger,
    model_supports_text_prompt,
)
from shared.db.sqlite import save_job
from modules.detection.services.result_store_service import add_result_bytes, create_result_store, finalize_result_store
from shared.inference.infer_service import _predict_batch, get_model
from shared.ownership.ownership import job_matches_owner


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

UPLOAD_JOBS: dict[str, dict] = {}
UPLOAD_JOBS_LOCK = threading.Lock()


def get_upload_job_snapshot(job_id: str) -> dict | None:
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if job is None:
            return None
        return {k: v for k, v in job.items() if k != "cancel"}


def request_upload_cancel(job_id: str, owner_key: str = "", owner_ip: str = "") -> bool:
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if job is None or not job_matches_owner(job, owner_key, owner_ip):
            return False
        job["cancel"].set()
        return True


def _new_upload_job(total: int, source_name: str, source_type: str) -> dict:
    return {
        "job_type": "upload",
        "id": uuid4().hex,
        "source_name": source_name,
        "source_type": source_type,
        "status": "running",
        "message": "",
        "total": total,
        "processed": 0,
        "kept": 0,
        "failed": 0,
        "start_ts": int(time.time()),
        "end_ts": None,
        "zip_path": None,
        "zip_parts": [],
        "result_dir": "",
        "result_manifest_path": "",
        "conf_thresh": CONF_THRESH,
        "batch_size": BATCH_SIZE,
        "imgsz": IMGSZ,
        "classes_raw": "",
        "model_key": get_upload_model_default(),
        "owner_key": "",
        "owner_ip": "",
        "cancel": threading.Event(),
    }


def _finish_upload_job(job_id: str, status: str, message: str = "") -> None:
    snapshot = None
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if job is None:
            return
        job["status"] = status
        job["message"] = message
        job["end_ts"] = int(time.time())
        if status in {"done", "error", "canceled"}:
            snapshot = {k: v for k, v in job.items() if k != "cancel"}
    if snapshot is not None:
        try:
            save_job(snapshot)
        except Exception as exc:
            logger.exception("failed to persist upload job %s: %s", job_id, exc)


def _close_batch_images(batch: list[tuple[str, Image.Image]]) -> None:
    for _name, img in batch:
        try:
            img.close()
        except Exception:
            pass


def _resolve_model_filters(model_key: str, model, classes_raw: str) -> tuple[Optional[Set[int]], list[str] | None]:
    allowed_classes: Optional[Set[int]] = None
    prompt_classes: list[str] | None = None

    if model_supports_text_prompt(model_key):
        prompt_classes = [token.strip() for token in classes_raw.split(",") if token.strip()] or None
        return allowed_classes, prompt_classes

    names = getattr(model, "names", None)
    if classes_raw and names:
        indexes: Set[int] = set()
        if isinstance(names, dict):
            name_map = {str(value).lower(): int(key) for key, value in names.items()}
        else:
            name_map = {str(value).lower(): index for index, value in enumerate(names)}
        for token in [value.strip() for value in classes_raw.split(",") if value.strip()]:
            if token.isdigit():
                indexes.add(int(token))
            else:
                mapped = name_map.get(token.lower())
                if mapped is not None:
                    indexes.add(mapped)
        if indexes:
            allowed_classes = indexes

    return allowed_classes, prompt_classes


def _is_upload_canceled(job_id: str) -> bool:
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        return bool(job and job["cancel"].is_set())


def _mark_upload_failed_item(job_id: str) -> None:
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if job is None:
            return
        job["processed"] += 1
        job["failed"] += 1
        if job["processed"] > (job.get("total") or 0):
            job["total"] = job["processed"]


def _process_batch(
    job_id: str,
    batch: list[tuple[str, Image.Image]],
    model,
    conf_thresh: float,
    allowed_classes: Optional[Set[int]],
    imgsz: int,
    model_key: str,
    prompt_classes: list[str] | None,
    result_zip: zipfile.ZipFile,
    result_store: dict,
    kept_sequence: int,
) -> int:
    batch_names = [name for name, _ in batch]
    batch_imgs = [img for _, img in batch]

    try:
        hits = _predict_batch(batch_imgs, model, conf_thresh, allowed_classes, imgsz, model_key, prompt_classes)
    except Exception as exc:
        with UPLOAD_JOBS_LOCK:
            job = UPLOAD_JOBS.get(job_id)
            if job is not None:
                job["processed"] += len(batch)
                job["failed"] += len(batch)
                job["message"] = str(exc)
                if job["processed"] > (job.get("total") or 0):
                    job["total"] = job["processed"]
        logger.exception("upload inference failed for job %s: %s", job_id, exc)
        raise RuntimeError(f"inference failed: {exc}") from exc
    finally:
        # PIL images are no longer needed after predict returns.
        pass

    kept_delta = 0
    try:
        for name, img, hit in zip(batch_names, batch_imgs, hits):
            if not hit:
                continue
            kept_sequence += 1
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            payload = buf.getvalue()
            output_name = f"{kept_sequence:07d}_{os.path.splitext(name)[0]}.jpg"
            result_zip.writestr(output_name, payload)
            add_result_bytes(result_store, output_name, payload, extra={"origin_name": name})
            kept_delta += 1
    finally:
        _close_batch_images(batch)

    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if job is not None:
            job["processed"] += len(batch)
            job["kept"] += kept_delta
            if job["processed"] > (job.get("total") or 0):
                job["total"] = job["processed"]

    return kept_sequence


def _run_zip_source(
    job_id: str,
    zip_path: str,
    batch_size: int,
    model,
    conf_thresh: float,
    allowed_classes: Optional[Set[int]],
    imgsz: int,
    model_key: str,
    prompt_classes: list[str] | None,
    result_zip: zipfile.ZipFile,
    result_store: dict,
) -> int:
    batch: list[tuple[str, Image.Image]] = []
    kept_sequence = 0

    with zipfile.ZipFile(zip_path) as source_zip:
        for entry in source_zip.infolist():
            if _is_upload_canceled(job_id):
                break
            if entry.is_dir():
                continue

            ext = os.path.splitext(entry.filename.lower())[1]
            safe_name = os.path.basename(entry.filename)
            if ext not in IMAGE_EXTS or not safe_name:
                continue

            try:
                payload = source_zip.read(entry)
                img = Image.open(io.BytesIO(payload)).convert("RGB")
            except Exception:
                _mark_upload_failed_item(job_id)
                continue

            batch.append((safe_name, img))
            if len(batch) >= batch_size:
                kept_sequence = _process_batch(
                    job_id,
                    batch,
                    model,
                    conf_thresh,
                    allowed_classes,
                    imgsz,
                    model_key,
                    prompt_classes,
                    result_zip,
                    result_store,
                    kept_sequence,
                )
                batch = []

        if batch and not _is_upload_canceled(job_id):
            kept_sequence = _process_batch(
                job_id,
                batch,
                model,
                conf_thresh,
                allowed_classes,
                imgsz,
                model_key,
                prompt_classes,
                result_zip,
                result_store,
                kept_sequence,
            )
        else:
            _close_batch_images(batch)

    return kept_sequence


def _run_video_source(
    job_id: str,
    video_path: str,
    frame_interval: int,
    batch_size: int,
    model,
    conf_thresh: float,
    allowed_classes: Optional[Set[int]],
    imgsz: int,
    model_key: str,
    prompt_classes: list[str] | None,
    result_zip: zipfile.ZipFile,
    result_store: dict,
) -> int:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("cannot open video file")

    batch: list[tuple[str, Image.Image]] = []
    kept_sequence = 0
    frame_idx = 0
    sample_idx = 0

    try:
        while True:
            if _is_upload_canceled(job_id):
                break

            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval != 0:
                frame_idx += 1
                continue

            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
            except Exception:
                _mark_upload_failed_item(job_id)
                frame_idx += 1
                continue

            batch.append((f"frame_{sample_idx:06d}.jpg", img))
            sample_idx += 1
            frame_idx += 1

            if len(batch) >= batch_size:
                kept_sequence = _process_batch(
                    job_id,
                    batch,
                    model,
                    conf_thresh,
                    allowed_classes,
                    imgsz,
                    model_key,
                    prompt_classes,
                    result_zip,
                    result_store,
                    kept_sequence,
                )
                batch = []

        if batch and not _is_upload_canceled(job_id):
            kept_sequence = _process_batch(
                job_id,
                batch,
                model,
                conf_thresh,
                allowed_classes,
                imgsz,
                model_key,
                prompt_classes,
                result_zip,
                result_store,
                kept_sequence,
            )
        else:
            _close_batch_images(batch)
    finally:
        cap.release()

    return kept_sequence


def _run_upload_job(
    job_id: str,
    source_path: str,
    source_type: str,
    conf_thresh: float,
    batch_size: int,
    imgsz: int,
    classes_raw: str,
    model_key: str,
    temp_dir: str | None,
    frame_interval: int | None = None,
) -> None:
    # Persist the job immediately so it survives a process restart.
    with UPLOAD_JOBS_LOCK:
        snapshot = {k: v for k, v in (UPLOAD_JOBS.get(job_id) or {}).items() if k != "cancel"}
    if snapshot:
        try:
            save_job(snapshot)
        except Exception as exc:
            logger.warning("early persist upload job %s failed: %s", job_id, exc)

    result_store = None
    zip_path = os.path.join(OUTPUT_DIR, f"upload_{job_id}.zip")

    try:
        model = get_model(model_key)
        with UPLOAD_JOBS_LOCK:
            job_meta = UPLOAD_JOBS.get(job_id) or {}
            source_name = job_meta.get("source_name", "")
        result_store = create_result_store(job_id, "upload", source_type, source_name)
        allowed_classes, prompt_classes = _resolve_model_filters(model_key, model, classes_raw)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as result_zip:
            if source_type == "zip":
                _run_zip_source(
                    job_id,
                    source_path,
                    batch_size,
                    model,
                    conf_thresh,
                    allowed_classes,
                    imgsz,
                    model_key,
                    prompt_classes,
                    result_zip,
                    result_store,
                )
            else:
                _run_video_source(
                    job_id,
                    source_path,
                    max(1, int(frame_interval or 1)),
                    batch_size,
                    model,
                    conf_thresh,
                    allowed_classes,
                    imgsz,
                    model_key,
                    prompt_classes,
                    result_zip,
                    result_store,
                )

        if _is_upload_canceled(job_id):
            if os.path.isfile(zip_path):
                try:
                    os.remove(zip_path)
                except Exception:
                    pass
            if result_store and os.path.isdir(result_store["result_dir"]):
                shutil.rmtree(result_store["result_dir"], ignore_errors=True)
            _finish_upload_job(job_id, "canceled")
            return

        manifest_path = finalize_result_store(result_store)

        with UPLOAD_JOBS_LOCK:
            job = UPLOAD_JOBS.get(job_id)
            if job is not None:
                job["zip_path"] = zip_path
                job["zip_parts"] = [{"path": zip_path, "name": os.path.basename(zip_path)}]
                job["result_dir"] = result_store["result_dir"]
                job["result_manifest_path"] = manifest_path

        _finish_upload_job(job_id, "done")

    except Exception as exc:
        logger.exception("upload job %s failed: %s", job_id, exc)
        if os.path.isfile(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass
        if result_store and os.path.isdir(result_store["result_dir"]):
            shutil.rmtree(result_store["result_dir"], ignore_errors=True)
        _finish_upload_job(job_id, "error", str(exc))
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


def start_zip_job(
    zip_path: str,
    original_filename: str,
    conf_thresh: float,
    batch_size: int,
    imgsz: int,
    classes_raw: str,
    model_key: str,
    owner_key: str,
    owner_ip: str,
    temp_dir: str,
) -> tuple[str | None, str]:
    try:
        with zipfile.ZipFile(zip_path) as source_zip:
            total = sum(
                1
                for entry in source_zip.infolist()
                if not entry.is_dir()
                and os.path.splitext(entry.filename.lower())[1] in IMAGE_EXTS
                and os.path.basename(entry.filename)
            )
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"ZIP 解析失败：{exc}"

    if total <= 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, "ZIP 中未找到有效图片（支持 jpg/png/bmp/tiff/webp）"

    job = _new_upload_job(total, original_filename, "zip")
    job.update(
        conf_thresh=conf_thresh,
        batch_size=batch_size,
        imgsz=imgsz,
        classes_raw=classes_raw,
        model_key=model_key,
        owner_key=owner_key,
        owner_ip=owner_ip,
    )
    job_id = job["id"]
    with UPLOAD_JOBS_LOCK:
        UPLOAD_JOBS[job_id] = job

    threading.Thread(
        target=_run_upload_job,
        args=(job_id, zip_path, "zip", conf_thresh, batch_size, imgsz, classes_raw, model_key, temp_dir, None),
        daemon=True,
    ).start()
    return job_id, ""


def start_video_job(
    video_path: str,
    original_filename: str,
    frame_interval: int,
    conf_thresh: float,
    batch_size: int,
    imgsz: int,
    classes_raw: str,
    model_key: str,
    owner_key: str,
    owner_ip: str,
    temp_dir: str,
) -> tuple[str | None, str]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap.release()
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, "无法打开视频文件，请确认格式为 MP4/AVI/MOV"

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    total = max(1, (frame_count + max(1, frame_interval) - 1) // max(1, frame_interval)) if frame_count > 0 else 1

    job = _new_upload_job(total, original_filename, "video")
    job.update(
        conf_thresh=conf_thresh,
        batch_size=batch_size,
        imgsz=imgsz,
        classes_raw=classes_raw,
        model_key=model_key,
        owner_key=owner_key,
        owner_ip=owner_ip,
        frame_interval=frame_interval,
    )
    job_id = job["id"]
    with UPLOAD_JOBS_LOCK:
        UPLOAD_JOBS[job_id] = job

    threading.Thread(
        target=_run_upload_job,
        args=(job_id, video_path, "video", conf_thresh, batch_size, imgsz, classes_raw, model_key, temp_dir, frame_interval),
        daemon=True,
    ).start()
    return job_id, ""
