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

from config import (
    BATCH_SIZE,
    CONF_THRESH,
    IMGSZ,
    OUTPUT_DIR,
    get_upload_model_default,
    UPLOAD_TEMP_DIR,
    VIDEO_FRAME_INTERVAL,
    logger,
    model_supports_text_prompt,
)
from service.infer_service import _predict_batch, get_model


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

UPLOAD_JOBS: dict[str, dict] = {}
UPLOAD_JOBS_LOCK = threading.Lock()


def get_upload_job_snapshot(job_id: str) -> dict | None:
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if job is None:
            return None
        return {k: v for k, v in job.items() if k != "cancel"}


def request_upload_cancel(job_id: str) -> bool:
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if job is None:
            return False
        job["cancel"].set()
        return True


def _new_upload_job(total: int, source_name: str, source_type: str) -> dict:
    return {
        "id": uuid4().hex,
        "job_type": "upload",
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
        "conf_thresh": CONF_THRESH,
        "batch_size": BATCH_SIZE,
        "imgsz": IMGSZ,
        "classes_raw": "",
        "model_key": get_upload_model_default(),
        "owner_ip": "",
        "cancel": threading.Event(),
    }


def _finish_upload_job(job_id: str, status: str, message: str = "") -> None:
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if job is None:
            return
        job["status"] = status
        job["message"] = message
        job["end_ts"] = int(time.time())


def _run_upload_job(
    job_id: str,
    images: list[tuple[str, Image.Image]],
    conf_thresh: float,
    batch_size: int,
    imgsz: int,
    classes_raw: str,
    model_key: str,
    temp_dir: str | None,
) -> None:
    """Background thread: run detection on pre-loaded images, write kept ones to result ZIP."""
    try:
        model = get_model(model_key)
        allowed_classes: Optional[Set[int]] = None
        prompt_classes: list[str] | None = None

        if model_supports_text_prompt(model_key):
            prompt_classes = [t.strip() for t in classes_raw.split(",") if t.strip()] or None
        else:
            names = getattr(model, "names", None)
            if classes_raw and names:
                indexes: Set[int] = set()
                if isinstance(names, dict):
                    name_map = {str(v).lower(): int(k) for k, v in names.items()}
                else:
                    name_map = {str(v).lower(): i for i, v in enumerate(names)}
                for token in [t.strip() for t in classes_raw.split(",") if t.strip()]:
                    if token.isdigit():
                        indexes.add(int(token))
                    else:
                        mapped = name_map.get(token.lower())
                        if mapped is not None:
                            indexes.add(mapped)
                if indexes:
                    allowed_classes = indexes

        kept_names: list[str] = []
        kept_imgs: list[Image.Image] = []

        for i in range(0, len(images), batch_size):
            with UPLOAD_JOBS_LOCK:
                job = UPLOAD_JOBS.get(job_id)
                if job is None or job["cancel"].is_set():
                    break

            batch = images[i : i + batch_size]
            batch_names = [n for n, _ in batch]
            batch_imgs = [img for _, img in batch]

            try:
                hits = _predict_batch(
                    batch_imgs, model, conf_thresh, allowed_classes, imgsz, model_key, prompt_classes
                )
                for name, img, hit in zip(batch_names, batch_imgs, hits):
                    if hit:
                        kept_names.append(name)
                        kept_imgs.append(img)
            except Exception:
                pass

            with UPLOAD_JOBS_LOCK:
                job = UPLOAD_JOBS.get(job_id)
                if job is not None:
                    job["processed"] = min(i + batch_size, len(images))
                    job["kept"] = len(kept_imgs)

        # Check cancel state after loop
        with UPLOAD_JOBS_LOCK:
            job = UPLOAD_JOBS.get(job_id)
            canceled = job is not None and job["cancel"].is_set()

        if canceled:
            _finish_upload_job(job_id, "canceled")
            return

        # Pack detected images into result ZIP
        zip_path = os.path.join(OUTPUT_DIR, f"upload_{job_id}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, img in zip(kept_names, kept_imgs):
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                zf.writestr(name, buf.getvalue())

        with UPLOAD_JOBS_LOCK:
            job = UPLOAD_JOBS.get(job_id)
            if job is not None:
                job["zip_path"] = zip_path
                job["kept"] = len(kept_imgs)
                job["processed"] = len(images)

        _finish_upload_job(job_id, "done")

    except Exception as exc:
        logger.exception("upload job %s failed: %s", job_id, exc)
        _finish_upload_job(job_id, "error", str(exc))
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


def start_zip_job(
    zip_bytes: bytes,
    original_filename: str,
    conf_thresh: float,
    batch_size: int,
    imgsz: int,
    classes_raw: str,
    model_key: str,
    owner_ip: str,
) -> tuple[str | None, str]:
    """Parse ZIP, load images into memory, launch background detection thread."""
    images: list[tuple[str, Image.Image]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for entry in zf.namelist():
                ext = os.path.splitext(entry.lower())[1]
                if ext not in IMAGE_EXTS:
                    continue
                # Prevent path traversal
                safe_name = os.path.basename(entry)
                if not safe_name:
                    continue
                try:
                    data = zf.read(entry)
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    images.append((safe_name, img))
                except Exception:
                    continue
    except Exception as exc:
        return None, f"ZIP 解析失败：{exc}"

    if not images:
        return None, "ZIP 中未找到有效图片（支持 jpg/png/bmp/tiff/webp）"

    job = _new_upload_job(len(images), original_filename, "zip")
    job.update(
        conf_thresh=conf_thresh,
        batch_size=batch_size,
        imgsz=imgsz,
        classes_raw=classes_raw,
        model_key=model_key,
        owner_ip=owner_ip,
    )
    job_id = job["id"]
    with UPLOAD_JOBS_LOCK:
        UPLOAD_JOBS[job_id] = job

    threading.Thread(
        target=_run_upload_job,
        args=(job_id, images, conf_thresh, batch_size, imgsz, classes_raw, model_key, None),
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
    owner_ip: str,
    temp_dir: str,
) -> tuple[str | None, str]:
    """Extract frames from video, load into memory, launch background detection thread."""
    images: list[tuple[str, Image.Image]] = []
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None, "无法打开视频文件，请确认格式为 MP4/AVI/MOV"

        frame_idx = 0
        kept_num = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_interval == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                images.append((f"frame_{kept_num:06d}.jpg", img))
                kept_num += 1
            frame_idx += 1
        cap.release()
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"视频帧提取失败：{exc}"

    if not images:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, "视频未提取到任何帧，文件可能已损坏"

    job = _new_upload_job(len(images), original_filename, "video")
    job.update(
        conf_thresh=conf_thresh,
        batch_size=batch_size,
        imgsz=imgsz,
        classes_raw=classes_raw,
        model_key=model_key,
        owner_ip=owner_ip,
        frame_interval=frame_interval,
    )
    job_id = job["id"]
    with UPLOAD_JOBS_LOCK:
        UPLOAD_JOBS[job_id] = job

    threading.Thread(
        target=_run_upload_job,
        args=(job_id, images, conf_thresh, batch_size, imgsz, classes_raw, model_key, temp_dir),
        daemon=True,
    ).start()
    return job_id, ""
