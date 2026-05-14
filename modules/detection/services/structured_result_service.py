from __future__ import annotations

import hashlib
import io
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

from PIL import Image

from shared.config.config import logger
from modules.detection.repositories import ai_result_repository as repo


def _safe_filename(name: str, fallback: str) -> str:
    base = os.path.basename((name or "").strip()) or fallback
    cleaned = "".join(char if char.isalnum() or char in {".", "_", "-"} else "_" for char in base).strip("._")
    return cleaned or fallback


def _serialize_source_key(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return value


def _content_bytes(item: dict[str, Any]) -> bytes | None:
    payload = item.get("payload_bytes")
    if isinstance(payload, bytes):
        return payload

    image = item.get("image")
    if isinstance(image, Image.Image):
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue()
    return None


def _content_hash(item: dict[str, Any]) -> str | None:
    payload = _content_bytes(item)
    if not payload:
        return None
    return hashlib.sha1(payload).hexdigest()


def preview_structured_asset_id(context: "StructuredYoloContext | None", item: dict[str, Any]) -> str:
    if context is None or not getattr(context, "enabled", False):
        return ""
    source_pk = str(item.get("source_pk") or item.get("name") or item.get("media_uri") or "").strip()
    content_hash = _content_hash(item)
    return repo.build_asset_id(context.source_system, source_pk, content_hash)


def _file_sha1(file_path: str) -> str | None:
    path = str(file_path or "").strip()
    if not path or not os.path.isfile(path):
        return None

    digest = hashlib.sha1()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _materialize_local_media(context: "StructuredYoloContext", item: dict[str, Any], asset_id: str) -> tuple[str, int | None, str | None]:
    if not context.materialize_local_inputs or not context.source_material_dir:
        return "", None, None

    os.makedirs(context.source_material_dir, exist_ok=True)
    filename = _safe_filename(str(item.get("name") or item.get("source_name") or "media.jpg"), "media.jpg")
    root, ext = os.path.splitext(filename)
    if not ext:
        ext = ".jpg"
    path = os.path.join(context.source_material_dir, f"{asset_id}_{root}{ext}")

    payload = _content_bytes(item)
    if isinstance(payload, bytes):
        with open(path, "wb") as fh:
            fh.write(payload)
        return path, len(payload), item.get("mime_type") or "image/jpeg"

    image = item.get("image")
    if isinstance(image, Image.Image):
        image.save(path, format="JPEG", quality=90)
        try:
            return path, os.path.getsize(path), item.get("mime_type") or "image/jpeg"
        except OSError:
            return path, None, item.get("mime_type") or "image/jpeg"

    return "", None, None


def _normalize_boxes(boxes: Sequence[dict[str, Any]], conf_thresh: float) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for box in boxes:
        confidence = float(box.get("confidence", 0.0) or 0.0)
        if confidence < conf_thresh:
            continue
        class_name = str(box.get("class_name") or "").strip()
        if not class_name:
            class_index = box.get("class_index")
            class_name = f"class_{class_index}" if class_index is not None else "unknown"
        normalized.append(
            {
                "class_index": box.get("class_index"),
                "class_name": class_name,
                "confidence": confidence,
                "x1": float(box.get("x1", 0.0) or 0.0),
                "y1": float(box.get("y1", 0.0) or 0.0),
                "x2": float(box.get("x2", 0.0) or 0.0),
                "y2": float(box.get("y2", 0.0) or 0.0),
            }
        )
    return normalized


def filter_prediction_boxes(
    boxes: Sequence[dict[str, Any]],
    conf_thresh: float,
    allowed_classes: set[int] | None = None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for box in _normalize_boxes(boxes, conf_thresh):
        class_index = box.get("class_index")
        if allowed_classes is not None:
            try:
                if int(class_index) not in allowed_classes:
                    continue
            except Exception:
                continue
        filtered.append(box)
    return filtered


def _default_scope(job: dict[str, Any], source_type: str) -> dict[str, Any]:
    scope = {
        "job_id": str(job.get("id") or ""),
        "job_type": str(job.get("job_type") or "yolo_detection"),
        "source_type": source_type,
        "model_key": str(job.get("model_key") or ""),
        "conf_thresh": job.get("conf_thresh"),
        "batch_size": job.get("batch_size"),
        "imgsz": job.get("imgsz"),
        "classes_raw": job.get("classes_raw") or job.get("classes"),
    }
    if job.get("source_name"):
        scope["source_name"] = job.get("source_name")
    if job.get("source_path"):
        scope["source_path"] = job.get("source_path")
    if job.get("frame_interval") is not None:
        scope["frame_interval"] = job.get("frame_interval")
    return scope


@dataclass
class StructuredYoloContext:
    enabled: bool
    run_id: str
    job_id: str
    job_type: str
    source_system: str
    source_table: str
    source_type: str
    source_scope: dict[str, Any]
    model_key: str
    model_name: str
    model_path: str
    model_version_id: str
    task_name: str
    result_dir: str = ""
    materialize_local_inputs: bool = False
    source_material_dir: str = ""
    scenario_code: str | None = None
    created_by: str = "hm_ai_worker"
    total_assets: int = 0
    processed_assets: int = 0
    detected_assets: int = 0
    detection_count: int = 0
    status: str = "running"
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    error_msg: str | None = None
    parent_asset_id: str = ""
    parent_media_asset: dict[str, Any] | None = None

    def as_run_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_name": self.task_name,
            "model_version_id": self.model_version_id,
            "model_code": self.model_key,
            "source_scope": self.source_scope,
            "scenario_code": self.scenario_code,
            "status": self.status,
            "total_assets": self.total_assets,
            "processed_assets": self.processed_assets,
            "detected_assets": self.detected_assets,
            "detection_count": self.detection_count,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error_msg": self.error_msg,
            "created_by": self.created_by,
        }


def build_structured_yolo_context(
    job: dict[str, Any],
    *,
    source_system: str,
    source_table: str,
    source_type: str,
    model_key: str,
    model_name: str,
    model_path: str,
    label_candidates: Sequence[str] | None = None,
    result_dir: str = "",
    materialize_local_inputs: bool = False,
    source_scope: dict[str, Any] | None = None,
    scenario_code: str | None = None,
    created_by: str = "hm_ai_worker",
) -> StructuredYoloContext:
    run_id = str(job.get("id") or "").strip()
    if not run_id:
        return StructuredYoloContext(
            enabled=False,
            run_id="",
            job_id="",
            job_type=str(job.get("job_type") or "yolo_detection"),
            source_system=source_system,
            source_table=source_table,
            source_type=source_type,
            source_scope=source_scope or {},
            model_key=model_key,
            model_name=model_name,
            model_path=model_path,
            model_version_id="",
            task_name=f"{job.get('job_type') or 'yolo_detection'}:{source_type}",
        )

    if not repo.tables_ready():
        return StructuredYoloContext(
            enabled=False,
            run_id=run_id,
            job_id=run_id,
            job_type=str(job.get("job_type") or "yolo_detection"),
            source_system=source_system,
            source_table=source_table,
            source_type=source_type,
            source_scope=source_scope or _default_scope(job, source_type),
            model_key=model_key,
            model_name=model_name,
            model_path=model_path,
            model_version_id="",
            task_name=f"{job.get('job_type') or 'yolo_detection'}:{source_type}",
        )

    try:
        model_version_id = repo.upsert_model_version(
            {
                "model_key": model_key,
                "model_name": model_name,
                "model_path": model_path,
                "model_file_uri": model_path,
                "model_task": "yolo_detection",
                "version_name": os.path.basename(model_path) or model_key,
                "status": "active",
                "published_by": created_by,
                "published_at": datetime.now(),
            }
        )

        for label_name in label_candidates or []:
            label_name = str(label_name or "").strip()
            if not label_name:
                continue
            repo.upsert_behavior_label(
                {
                    "label_name": label_name,
                    "label_category": "other",
                    "scenario_code": scenario_code,
                }
            )

        context = StructuredYoloContext(
            enabled=True,
            run_id=run_id,
            job_id=run_id,
            job_type=str(job.get("job_type") or "yolo_detection"),
            source_system=source_system,
            source_table=source_table,
            source_type=source_type,
            source_scope=source_scope or _default_scope(job, source_type),
            model_key=model_key,
            model_name=model_name,
            model_path=model_path,
            model_version_id=model_version_id,
            task_name=f"{job.get('job_type') or 'yolo_detection'}:{source_type}",
            result_dir=result_dir,
            materialize_local_inputs=materialize_local_inputs,
            source_material_dir=os.path.join(result_dir, "structured_inputs") if result_dir and materialize_local_inputs else "",
            scenario_code=scenario_code,
            created_by=created_by,
            total_assets=int(job.get("total") or 0),
        )
        repo.upsert_yolo_run(context.as_run_record())
        return context
    except Exception as exc:
        logger.exception("failed to initialize structured yolo context for job %s: %s", run_id, exc)
        return StructuredYoloContext(
            enabled=False,
            run_id=run_id,
            job_id=run_id,
            job_type=str(job.get("job_type") or "yolo_detection"),
            source_system=source_system,
            source_table=source_table,
            source_type=source_type,
            source_scope=source_scope or _default_scope(job, source_type),
            model_key=model_key,
            model_name=model_name,
            model_path=model_path,
            model_version_id="",
            task_name=f"{job.get('job_type') or 'yolo_detection'}:{source_type}",
        )


def persist_structured_yolo_batch(
    context: StructuredYoloContext,
    batch_items: Sequence[dict[str, Any]],
    batch_boxes: Sequence[Sequence[dict[str, Any]]],
    *,
    conf_thresh: float,
) -> dict[str, int]:
    if not context.enabled or not batch_items:
        return {"processed_assets": 0, "detected_assets": 0, "detection_count": 0}

    detection_records: list[dict[str, Any]] = []
    detected_assets = 0
    detection_count = 0

    for item, boxes in zip(batch_items, batch_boxes):
        content_hash = _content_hash(item)
        source_pk = str(item.get("source_pk") or item.get("name") or item.get("media_uri") or "").strip()
        asset_id = repo.build_asset_id(context.source_system, source_pk, content_hash)
        media_uri = str(item.get("media_uri") or "").strip()
        file_size_bytes = item.get("file_size_bytes")
        mime_type = item.get("mime_type") or "image/jpeg"

        if context.materialize_local_inputs and not media_uri:
            materialized_uri, materialized_size, materialized_mime = _materialize_local_media(context, item, asset_id)
            if materialized_uri:
                media_uri = materialized_uri
                if file_size_bytes is None:
                    file_size_bytes = materialized_size
                mime_type = materialized_mime or mime_type

        if not media_uri and context.source_system == "oracle":
            media_uri = str(item.get("source_uri") or item.get("url") or "").strip()

        media_record = {
            "asset_id": asset_id,
            "source_system": context.source_system,
            "source_table": context.source_table,
            "source_pk": source_pk,
            "source_row_key": _serialize_source_key(item.get("source_row_key")),
            "parent_asset_id": item.get("parent_asset_id") or context.parent_asset_id or None,
            "media_type": item.get("media_type") or ("frame" if context.source_type == "video" else "image"),
            "uri_type": item.get("uri_type") or ("url" if media_uri.startswith("http") else ("file_path" if media_uri else "unknown")),
            "media_uri": media_uri or None,
            "image_blob": None,
            "mime_type": mime_type,
            "file_size_bytes": file_size_bytes,
            "content_hash": content_hash,
            "face_id": item.get("face_id"),
            "person_id": item.get("person_id"),
            "sfzh": item.get("sfzh"),
            "person_name": item.get("person_name"),
            "age_estimate": item.get("age_estimate"),
            "device_id": item.get("device_id"),
            "device_name": item.get("device_name"),
            "shot_time": item.get("shot_time"),
            "longitude": item.get("longitude"),
            "latitude": item.get("latitude"),
            "place_name": item.get("place_name"),
            "area_code": item.get("area_code"),
            "download_status": item.get("download_status") or "downloaded",
            "detect_status": "processing",
            "error_msg": None,
        }
        repo.upsert_media_asset(media_record)

        normalized_boxes = _normalize_boxes(boxes, conf_thresh)
        if normalized_boxes:
            detected_assets += 1
        detection_count += len(normalized_boxes)

        for box in normalized_boxes:
            label_name = str(box.get("class_name") or "unknown").strip() or "unknown"
            label_code = repo.build_label_code(label_name)
            repo.upsert_behavior_label(
                {
                    "label_code": label_code,
                    "label_name": label_name,
                    "label_category": item.get("label_category") or "other",
                    "scenario_code": context.scenario_code,
                }
            )
            detection_records.append(
                {
                    "detection_id": repo.build_detection_id(context.run_id, asset_id, label_code, box),
                    "run_id": context.run_id,
                    "asset_id": asset_id,
                    "model_version_id": context.model_version_id,
                    "scenario_code": context.scenario_code,
                    "label_code": label_code,
                    "label_name": label_name,
                    "label_category": item.get("label_category") or "other",
                    "confidence": float(box.get("confidence", 0.0) or 0.0),
                    "bbox_x": float(box.get("x1", 0.0) or 0.0),
                    "bbox_y": float(box.get("y1", 0.0) or 0.0),
                    "bbox_w": float(box.get("x2", 0.0) or 0.0) - float(box.get("x1", 0.0) or 0.0),
                    "bbox_h": float(box.get("y2", 0.0) or 0.0) - float(box.get("y1", 0.0) or 0.0),
                    "bbox_json": box,
                    "track_id": item.get("track_id"),
                    "sfzh": item.get("sfzh"),
                    "person_name": item.get("person_name"),
                    "device_id": item.get("device_id"),
                    "shot_time": item.get("shot_time"),
                    "longitude": item.get("longitude"),
                    "latitude": item.get("latitude"),
                    "place_name": item.get("place_name"),
                    "review_status": "pending",
                }
            )

        repo.upsert_media_asset({**media_record, "detect_status": "success", "error_msg": None})

    if detection_records:
        repo.upsert_yolo_detections(detection_records)

    context.processed_assets += len(batch_items)
    context.detected_assets += detected_assets
    context.detection_count += detection_count
    repo.upsert_yolo_run(context.as_run_record())

    return {
        "processed_assets": len(batch_items),
        "detected_assets": detected_assets,
        "detection_count": detection_count,
    }


def seed_parent_video_asset(
    context: StructuredYoloContext,
    video_path: str,
    *,
    source_name: str = "",
) -> str:
    if not context.enabled or context.source_type != "video":
        return ""

    normalized_path = os.path.abspath(str(video_path or "").strip()) if str(video_path or "").strip() else ""
    if not normalized_path:
        return ""

    content_hash = _file_sha1(normalized_path)
    asset_id = repo.build_asset_id(context.source_system, normalized_path, content_hash)
    mime_type = mimetypes.guess_type(normalized_path)[0] or "video/mp4"
    try:
        file_size_bytes = os.path.getsize(normalized_path)
    except OSError:
        file_size_bytes = None

    media_record = {
        "asset_id": asset_id,
        "source_system": context.source_system,
        "source_table": context.source_table,
        "source_pk": normalized_path,
        "source_row_key": {
            "job_id": context.job_id,
            "source_type": context.source_type,
            "source_name": source_name,
        },
        "parent_asset_id": None,
        "media_type": "video",
        "uri_type": "file_path",
        "media_uri": normalized_path,
        "image_blob": None,
        "mime_type": mime_type,
        "file_size_bytes": file_size_bytes,
        "content_hash": content_hash,
        "download_status": "downloaded",
        "detect_status": "processing",
        "error_msg": None,
    }
    repo.upsert_media_asset(media_record)
    context.parent_asset_id = asset_id
    context.parent_media_asset = media_record
    return asset_id


def safe_persist_structured_yolo_batch(
    context: StructuredYoloContext,
    batch_items: Sequence[dict[str, Any]],
    batch_boxes: Sequence[Sequence[dict[str, Any]]],
    *,
    conf_thresh: float,
) -> dict[str, int]:
    try:
        return persist_structured_yolo_batch(
            context,
            batch_items,
            batch_boxes,
            conf_thresh=conf_thresh,
        )
    except Exception as exc:
        logger.exception("failed to persist structured yolo batch for run %s: %s", context.run_id, exc)
        return {"processed_assets": 0, "detected_assets": 0, "detection_count": 0}


def finalize_structured_yolo_run(
    context: StructuredYoloContext,
    *,
    status: str,
    error_msg: str | None = None,
) -> None:
    if not context.enabled:
        return

    context.status = status
    context.error_msg = error_msg
    context.finished_at = datetime.now()
    try:
        repo.upsert_yolo_run(context.as_run_record())
        if context.parent_media_asset:
            if status == "success":
                detect_status = "success"
            elif status == "failed":
                detect_status = "failed"
            else:
                detect_status = "skipped"
            repo.upsert_media_asset(
                {
                    **context.parent_media_asset,
                    "detect_status": detect_status,
                    "error_msg": error_msg,
                }
            )
    except Exception as exc:
        logger.exception("failed to finalize structured yolo run %s: %s", context.run_id, exc)
