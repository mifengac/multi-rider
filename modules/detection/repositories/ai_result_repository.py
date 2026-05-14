from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from typing import Any, Sequence

from shared.config.config import logger, resolve_model_path
from shared.db import kingbase


SCHEMA_NAME = "jcgkzx_monitor"
TABLE_MODEL_VERSION = "hm_ai_model_version"
TABLE_BEHAVIOR_LABEL = "hm_ai_behavior_label"
TABLE_MEDIA_ASSET = "hm_ai_media_asset"
TABLE_YOLO_RUN = "hm_ai_yolo_run"
TABLE_YOLO_DETECTION = "hm_ai_yolo_detection"
TABLE_TRAINING_SAMPLE = "hm_ai_training_sample"

VALID_LABEL_CATEGORIES = {"behavior", "object", "place", "person", "vehicle", "scene", "other"}
VALID_MEDIA_TYPES = {"image", "video", "frame", "face", "background", "other"}
VALID_URI_TYPES = {"url", "file_path", "api_ref", "db_column", "blob", "unknown"}
VALID_DOWNLOAD_STATUSES = {"pending", "downloaded", "skipped", "failed"}
VALID_DETECT_STATUSES = {"pending", "processing", "success", "failed", "skipped"}
VALID_RUN_STATUSES = {"running", "success", "failed", "canceled"}
VALID_REVIEW_STATUSES = {"pending", "confirmed", "rejected", "ignored"}
VALID_REVIEW_RESULTS = {"true_positive", "false_positive", "false_negative", "other"}
VALID_MODEL_TASKS = {"yolo_detection", "face_recognition", "risk_score", "other"}
VALID_MODEL_STATUS = {"staging", "active", "archived", "disabled"}
VALID_SAMPLE_TYPES = {"positive", "negative", "hard_negative", "unlabeled"}
VALID_ANNOTATION_STATUSES = {"unreviewed", "labeled", "approved", "rejected"}
VALID_DATASET_SPLITS = {"train", "val", "test", "pool"}


def tables_ready() -> bool:
    required_tables = (
        TABLE_BEHAVIOR_LABEL,
        TABLE_MODEL_VERSION,
        TABLE_MEDIA_ASSET,
        TABLE_YOLO_RUN,
        TABLE_YOLO_DETECTION,
    )
    return all(kingbase.table_exists(SCHEMA_NAME, table_name) for table_name in required_tables)


def _clean_code(value: str, fallback_prefix: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip().lower()).strip("._-")
    if raw:
        return raw[:64]
    digest = hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()[:12]
    return f"{fallback_prefix}_{digest}"


def build_label_code(label_name: str) -> str:
    return _clean_code(label_name, "label")


def build_model_version_id(model_key: str, model_path: str | None = None) -> str:
    seed = [str(model_key or "").strip()]
    if model_path:
        seed.append(os.path.abspath(model_path))
        try:
            stat_result = os.stat(model_path)
            seed.append(str(int(stat_result.st_size)))
            seed.append(str(int(stat_result.st_mtime)))
        except OSError:
            pass
    digest = hashlib.sha1("|".join(seed).encode("utf-8")).hexdigest()[:16]
    return f"mv_{digest}"


def build_asset_id(source_system: str, source_pk: str, content_hash: str | None = None) -> str:
    seed_parts = [str(source_system or "").strip(), str(source_pk or "").strip(), str(content_hash or "").strip()]
    seed = "|".join(part for part in seed_parts if part)
    if not seed:
        seed = hashlib.sha1(os.urandom(16)).hexdigest()
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
    return f"asset_{digest}"


def build_detection_id(run_id: str, asset_id: str, label_code: str, box: dict[str, Any]) -> str:
    payload = {
        "run_id": str(run_id or "").strip(),
        "asset_id": str(asset_id or "").strip(),
        "label_code": str(label_code or "").strip(),
        "confidence": round(float(box.get("confidence", 0.0) or 0.0), 6),
        "x1": round(float(box.get("x1", 0.0) or 0.0), 4),
        "y1": round(float(box.get("y1", 0.0) or 0.0), 4),
        "x2": round(float(box.get("x2", 0.0) or 0.0), 4),
        "y2": round(float(box.get("y2", 0.0) or 0.0), 4),
    }
    digest = hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"det_{digest}"


def build_training_sample_id(detection_id: str, asset_id: str, sample_type: str) -> str:
    seed = "|".join(
        [
            str(detection_id or "").strip(),
            str(asset_id or "").strip(),
            str(sample_type or "").strip(),
        ]
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
    return f"sample_{digest}"


def _json_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)

    text = str(value).strip()
    if not text:
        return None

    patterns = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    )
    for pattern in patterns:
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        logger.debug("unable to parse datetime value: %s", value)
        return None


def _clamp_enum(value: Any, allowed: set[str], fallback: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in allowed else fallback


def upsert_model_version(record: dict[str, Any]) -> str:
    model_key = str(record.get("model_code") or record.get("model_key") or "unknown").strip() or "unknown"
    model_path = str(record.get("model_file_uri") or record.get("model_path") or "").strip() or None
    model_version_id = str(record.get("model_version_id") or build_model_version_id(model_key, model_path))
    label_config_json = _json_text(record.get("label_config_json") or record.get("label_config"))
    metrics_json = _json_text(record.get("metrics_json") or record.get("metrics"))

    row = kingbase.fetch_one(
        f"""
        INSERT INTO {SCHEMA_NAME}.{TABLE_MODEL_VERSION} (
            model_version_id,
            model_code,
            model_name,
            model_task,
            version_name,
            model_file_uri,
            config_uri,
            label_config_json,
            train_dataset_version,
            metrics_json,
            status,
            published_by,
            published_at,
            created_at,
            updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON CONFLICT (model_version_id) DO UPDATE SET
            model_code = EXCLUDED.model_code,
            model_name = EXCLUDED.model_name,
            model_task = EXCLUDED.model_task,
            version_name = EXCLUDED.version_name,
            model_file_uri = EXCLUDED.model_file_uri,
            config_uri = EXCLUDED.config_uri,
            label_config_json = EXCLUDED.label_config_json,
            train_dataset_version = EXCLUDED.train_dataset_version,
            metrics_json = EXCLUDED.metrics_json,
            status = EXCLUDED.status,
            published_by = EXCLUDED.published_by,
            published_at = EXCLUDED.published_at,
            updated_at = NOW()
        RETURNING model_version_id
        """,
        (
            model_version_id,
            model_key,
            str(record.get("model_name") or model_key),
            _clamp_enum(record.get("model_task"), VALID_MODEL_TASKS, "yolo_detection"),
            str(record.get("version_name") or os.path.basename(model_path or "") or model_key),
            model_path,
            record.get("config_uri"),
            label_config_json,
            record.get("train_dataset_version"),
            metrics_json,
            _clamp_enum(record.get("status"), VALID_MODEL_STATUS, "staging"),
            record.get("published_by"),
            _coerce_datetime(record.get("published_at")),
        ),
    )
    return str((row or {}).get("model_version_id") or model_version_id)


def upsert_behavior_label(record: dict[str, Any]) -> str:
    label_name = str(record.get("label_name") or "").strip()
    if not label_name:
        raise ValueError("label_name is required")
    label_code = str(record.get("label_code") or build_label_code(label_name))

    row = kingbase.fetch_one(
        f"""
        INSERT INTO {SCHEMA_NAME}.{TABLE_BEHAVIOR_LABEL} (
            label_code,
            label_name,
            label_category,
            scenario_code,
            default_risk_weight,
            enabled,
            description,
            created_at,
            updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON CONFLICT (label_code) DO UPDATE SET
            label_name = EXCLUDED.label_name,
            label_category = EXCLUDED.label_category,
            scenario_code = EXCLUDED.scenario_code,
            default_risk_weight = EXCLUDED.default_risk_weight,
            enabled = EXCLUDED.enabled,
            description = EXCLUDED.description,
            updated_at = NOW()
        RETURNING label_code
        """,
        (
            label_code,
            label_name,
            _clamp_enum(record.get("label_category"), VALID_LABEL_CATEGORIES, "other"),
            record.get("scenario_code"),
            record.get("default_risk_weight", 0),
            bool(record.get("enabled", True)),
            record.get("description"),
        ),
    )
    return str((row or {}).get("label_code") or label_code)


def upsert_media_asset(record: dict[str, Any]) -> str:
    source_system = str(record.get("source_system") or "unknown").strip() or "unknown"
    source_pk = str(record.get("source_pk") or "").strip()
    content_hash = str(record.get("content_hash") or "").strip() or None
    asset_id = str(record.get("asset_id") or build_asset_id(source_system, source_pk, content_hash))

    row = kingbase.fetch_one(
        f"""
        INSERT INTO {SCHEMA_NAME}.{TABLE_MEDIA_ASSET} (
            asset_id,
            source_system,
            source_table,
            source_pk,
            source_row_key,
            parent_asset_id,
            media_type,
            uri_type,
            media_uri,
            image_blob,
            mime_type,
            file_size_bytes,
            content_hash,
            face_id,
            person_id,
            sfzh,
            person_name,
            age_estimate,
            device_id,
            device_name,
            shot_time,
            longitude,
            latitude,
            place_name,
            area_code,
            download_status,
            detect_status,
            error_msg,
            created_at,
            updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON CONFLICT (asset_id) DO UPDATE SET
            source_system = EXCLUDED.source_system,
            source_table = EXCLUDED.source_table,
            source_pk = EXCLUDED.source_pk,
            source_row_key = EXCLUDED.source_row_key,
            parent_asset_id = EXCLUDED.parent_asset_id,
            media_type = EXCLUDED.media_type,
            uri_type = EXCLUDED.uri_type,
            media_uri = EXCLUDED.media_uri,
            image_blob = COALESCE(EXCLUDED.image_blob, {SCHEMA_NAME}.{TABLE_MEDIA_ASSET}.image_blob),
            mime_type = EXCLUDED.mime_type,
            file_size_bytes = EXCLUDED.file_size_bytes,
            content_hash = EXCLUDED.content_hash,
            face_id = EXCLUDED.face_id,
            person_id = EXCLUDED.person_id,
            sfzh = EXCLUDED.sfzh,
            person_name = EXCLUDED.person_name,
            age_estimate = EXCLUDED.age_estimate,
            device_id = EXCLUDED.device_id,
            device_name = EXCLUDED.device_name,
            shot_time = EXCLUDED.shot_time,
            longitude = EXCLUDED.longitude,
            latitude = EXCLUDED.latitude,
            place_name = EXCLUDED.place_name,
            area_code = EXCLUDED.area_code,
            download_status = EXCLUDED.download_status,
            detect_status = EXCLUDED.detect_status,
            error_msg = EXCLUDED.error_msg,
            updated_at = NOW()
        RETURNING asset_id
        """,
        (
            asset_id,
            source_system,
            record.get("source_table"),
            source_pk,
            _json_text(record.get("source_row_key")),
            record.get("parent_asset_id"),
            _clamp_enum(record.get("media_type"), VALID_MEDIA_TYPES, "other"),
            _clamp_enum(record.get("uri_type"), VALID_URI_TYPES, "unknown"),
            record.get("media_uri"),
            record.get("image_blob"),
            record.get("mime_type"),
            record.get("file_size_bytes"),
            content_hash,
            record.get("face_id"),
            record.get("person_id"),
            record.get("sfzh"),
            record.get("person_name"),
            record.get("age_estimate"),
            record.get("device_id"),
            record.get("device_name"),
            _coerce_datetime(record.get("shot_time")),
            record.get("longitude"),
            record.get("latitude"),
            record.get("place_name"),
            record.get("area_code"),
            _clamp_enum(record.get("download_status"), VALID_DOWNLOAD_STATUSES, "pending"),
            _clamp_enum(record.get("detect_status"), VALID_DETECT_STATUSES, "pending"),
            record.get("error_msg"),
        ),
    )
    return str((row or {}).get("asset_id") or asset_id)


def upsert_yolo_run(record: dict[str, Any]) -> str:
    run_id = str(record.get("run_id") or record.get("id") or "").strip()
    if not run_id:
        raise ValueError("run_id is required")

    row = kingbase.fetch_one(
        f"""
        INSERT INTO {SCHEMA_NAME}.{TABLE_YOLO_RUN} (
            run_id,
            task_name,
            model_version_id,
            model_code,
            source_scope,
            scenario_code,
            status,
            total_assets,
            processed_assets,
            detected_assets,
            detection_count,
            started_at,
            finished_at,
            error_msg,
            created_by,
            created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
        )
        ON CONFLICT (run_id) DO UPDATE SET
            task_name = EXCLUDED.task_name,
            model_version_id = EXCLUDED.model_version_id,
            model_code = EXCLUDED.model_code,
            source_scope = EXCLUDED.source_scope,
            scenario_code = EXCLUDED.scenario_code,
            status = EXCLUDED.status,
            total_assets = EXCLUDED.total_assets,
            processed_assets = EXCLUDED.processed_assets,
            detected_assets = EXCLUDED.detected_assets,
            detection_count = EXCLUDED.detection_count,
            started_at = EXCLUDED.started_at,
            finished_at = EXCLUDED.finished_at,
            error_msg = EXCLUDED.error_msg,
            created_by = EXCLUDED.created_by
        RETURNING run_id
        """,
        (
            run_id,
            str(record.get("task_name") or record.get("job_type") or "yolo_detection"),
            str(record.get("model_version_id") or ""),
            str(record.get("model_code") or record.get("model_key") or "unknown"),
            _json_text(record.get("source_scope")),
            record.get("scenario_code"),
            _clamp_enum(record.get("status"), VALID_RUN_STATUSES, "running"),
            int(record.get("total_assets") or 0),
            int(record.get("processed_assets") or 0),
            int(record.get("detected_assets") or 0),
            int(record.get("detection_count") or 0),
            _coerce_datetime(record.get("started_at")) or datetime.now(),
            _coerce_datetime(record.get("finished_at")),
            record.get("error_msg"),
            record.get("created_by") or "hm_ai_worker",
        ),
    )
    return str((row or {}).get("run_id") or run_id)


def upsert_yolo_detections(records: Sequence[dict[str, Any]]) -> int:
    rows: list[tuple[Any, ...]] = []
    for record in records:
        run_id = str(record.get("run_id") or "").strip()
        asset_id = str(record.get("asset_id") or "").strip()
        label_name = str(record.get("label_name") or "").strip()
        if not run_id or not asset_id or not label_name:
            continue

        label_code = str(record.get("label_code") or build_label_code(label_name))
        detection_id = str(record.get("detection_id") or build_detection_id(run_id, asset_id, label_code, record))
        x1 = float(record.get("bbox_x") if record.get("bbox_x") is not None else record.get("x1") or 0.0)
        y1 = float(record.get("bbox_y") if record.get("bbox_y") is not None else record.get("y1") or 0.0)
        bbox_w = record.get("bbox_w")
        bbox_h = record.get("bbox_h")
        if bbox_w is None:
            bbox_w = float(record.get("x2") or 0.0) - x1
        if bbox_h is None:
            bbox_h = float(record.get("y2") or 0.0) - y1

        rows.append(
            (
                detection_id,
                run_id,
                asset_id,
                record.get("model_version_id"),
                record.get("scenario_code"),
                label_code,
                label_name,
                record.get("label_category"),
                record.get("confidence"),
                x1,
                y1,
                bbox_w,
                bbox_h,
                _json_text(record.get("bbox_json") or record.get("bbox")),
                record.get("track_id"),
                record.get("sfzh"),
                record.get("person_name"),
                record.get("device_id"),
                _coerce_datetime(record.get("shot_time")),
                record.get("longitude"),
                record.get("latitude"),
                record.get("place_name"),
                _clamp_enum(record.get("review_status"), VALID_REVIEW_STATUSES, "pending"),
                record.get("review_result") if record.get("review_result") in VALID_REVIEW_RESULTS else None,
                record.get("reviewer_id"),
                record.get("reviewer_name"),
                _coerce_datetime(record.get("reviewed_at")),
                record.get("review_comment"),
            )
        )

    if not rows:
        return 0

    kingbase.execute_many(
        f"""
        INSERT INTO {SCHEMA_NAME}.{TABLE_YOLO_DETECTION} (
            detection_id,
            run_id,
            asset_id,
            model_version_id,
            scenario_code,
            label_code,
            label_name,
            label_category,
            confidence,
            bbox_x,
            bbox_y,
            bbox_w,
            bbox_h,
            bbox_json,
            track_id,
            sfzh,
            person_name,
            device_id,
            shot_time,
            longitude,
            latitude,
            place_name,
            review_status,
            review_result,
            reviewer_id,
            reviewer_name,
            reviewed_at,
            review_comment
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (detection_id) DO UPDATE SET
            run_id = EXCLUDED.run_id,
            asset_id = EXCLUDED.asset_id,
            model_version_id = EXCLUDED.model_version_id,
            scenario_code = EXCLUDED.scenario_code,
            label_code = EXCLUDED.label_code,
            label_name = EXCLUDED.label_name,
            label_category = EXCLUDED.label_category,
            confidence = EXCLUDED.confidence,
            bbox_x = EXCLUDED.bbox_x,
            bbox_y = EXCLUDED.bbox_y,
            bbox_w = EXCLUDED.bbox_w,
            bbox_h = EXCLUDED.bbox_h,
            bbox_json = EXCLUDED.bbox_json,
            track_id = EXCLUDED.track_id,
            sfzh = EXCLUDED.sfzh,
            person_name = EXCLUDED.person_name,
            device_id = EXCLUDED.device_id,
            shot_time = EXCLUDED.shot_time,
            longitude = EXCLUDED.longitude,
            latitude = EXCLUDED.latitude,
            place_name = EXCLUDED.place_name,
            review_status = EXCLUDED.review_status,
            review_result = EXCLUDED.review_result,
            reviewer_id = EXCLUDED.reviewer_id,
            reviewer_name = EXCLUDED.reviewer_name,
            reviewed_at = EXCLUDED.reviewed_at,
            review_comment = EXCLUDED.review_comment,
            updated_at = NOW()
        """,
        rows,
    )
    return len(rows)


def list_yolo_runs(limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    where_clause = ""
    params: list[Any] = []
    if status:
        where_clause = "WHERE status = %s"
        params.append(status)
    params.append(max(1, int(limit)))
    return kingbase.fetch_all(
        f"""
        SELECT
            run_id,
            task_name,
            model_version_id,
            model_code,
            source_scope,
            scenario_code,
            status,
            total_assets,
            processed_assets,
            detected_assets,
            detection_count,
            started_at,
            finished_at,
            error_msg,
            created_by,
            created_at
        FROM {SCHEMA_NAME}.{TABLE_YOLO_RUN}
        {where_clause}
        ORDER BY started_at DESC
        LIMIT %s
        """,
        tuple(params),
    )


def get_yolo_run(run_id: str) -> dict[str, Any] | None:
    return kingbase.fetch_one(
        f"""
        SELECT *
        FROM {SCHEMA_NAME}.{TABLE_YOLO_RUN}
        WHERE run_id = %s
        """,
        (run_id,),
    )


def list_media_assets(
    limit: int = 100,
    asset_id: str | None = None,
    parent_asset_id: str | None = None,
    source_system: str | None = None,
    source_table: str | None = None,
    media_type: str | None = None,
    detect_status: str | None = None,
) -> list[dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if asset_id:
        filters.append("a.asset_id = %s")
        params.append(asset_id)
    if parent_asset_id:
        filters.append("a.parent_asset_id = %s")
        params.append(parent_asset_id)
    if source_system:
        filters.append("a.source_system = %s")
        params.append(source_system)
    if source_table:
        filters.append("a.source_table = %s")
        params.append(source_table)
    if media_type:
        filters.append("a.media_type = %s")
        params.append(_clamp_enum(media_type, VALID_MEDIA_TYPES, "other"))
    if detect_status:
        filters.append("a.detect_status = %s")
        params.append(_clamp_enum(detect_status, VALID_DETECT_STATUSES, "pending"))

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(max(1, int(limit)))
    return kingbase.fetch_all(
        f"""
        SELECT
            a.*,
            COALESCE(d.detection_count, 0) AS detection_count,
            COALESCE(c.child_count, 0) AS child_count
        FROM {SCHEMA_NAME}.{TABLE_MEDIA_ASSET} a
        LEFT JOIN (
            SELECT asset_id, COUNT(*) AS detection_count
            FROM {SCHEMA_NAME}.{TABLE_YOLO_DETECTION}
            GROUP BY asset_id
        ) d
            ON d.asset_id = a.asset_id
        LEFT JOIN (
            SELECT parent_asset_id, COUNT(*) AS child_count
            FROM {SCHEMA_NAME}.{TABLE_MEDIA_ASSET}
            WHERE parent_asset_id IS NOT NULL
            GROUP BY parent_asset_id
        ) c
            ON c.parent_asset_id = a.asset_id
        {where_clause}
        ORDER BY a.created_at DESC
        LIMIT %s
        """,
        tuple(params),
    )


def get_media_asset(asset_id: str) -> dict[str, Any] | None:
    rows = list_media_assets(limit=1, asset_id=asset_id)
    return dict(rows[0]) if rows else None


def list_yolo_detections(
    limit: int = 100,
    run_id: str | None = None,
    label_code: str | None = None,
    sfzh: str | None = None,
    start_time: Any | None = None,
    end_time: Any | None = None,
    source_system: str | None = None,
    source_table: str | None = None,
    review_status: str | None = None,
) -> list[dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if run_id:
        filters.append("d.run_id = %s")
        params.append(run_id)
    if label_code:
        filters.append("d.label_code = %s")
        params.append(label_code)
    if sfzh:
        filters.append("d.sfzh = %s")
        params.append(sfzh)
    if start_time:
        filters.append("COALESCE(d.shot_time, a.shot_time) >= %s")
        params.append(_coerce_datetime(start_time) or start_time)
    if end_time:
        filters.append("COALESCE(d.shot_time, a.shot_time) <= %s")
        params.append(_coerce_datetime(end_time) or end_time)
    if source_system:
        filters.append("a.source_system = %s")
        params.append(source_system)
    if source_table:
        filters.append("a.source_table = %s")
        params.append(source_table)
    if review_status:
        filters.append("d.review_status = %s")
        params.append(_clamp_enum(review_status, VALID_REVIEW_STATUSES, "pending"))

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(max(1, int(limit)))
    return kingbase.fetch_all(
        f"""
        SELECT
            d.detection_id,
            d.run_id,
            d.asset_id,
            d.model_version_id,
            d.scenario_code,
            d.label_code,
            d.label_name,
            d.label_category,
            d.confidence,
            d.bbox_x,
            d.bbox_y,
            d.bbox_w,
            d.bbox_h,
            d.bbox_json,
            d.track_id,
            d.sfzh,
            d.person_name,
            d.device_id,
            d.shot_time,
            d.longitude,
            d.latitude,
            d.place_name,
            d.review_status,
            d.review_result,
            d.reviewer_id,
            d.reviewer_name,
            d.reviewed_at,
            d.review_comment,
            d.created_at,
            d.updated_at,
            a.source_system,
            a.source_table,
            a.source_pk,
            a.parent_asset_id,
            a.media_uri,
            a.content_hash,
            a.download_status,
            a.detect_status
        FROM {SCHEMA_NAME}.{TABLE_YOLO_DETECTION} d
        LEFT JOIN {SCHEMA_NAME}.{TABLE_MEDIA_ASSET} a
            ON a.asset_id = d.asset_id
        {where_clause}
        ORDER BY d.created_at DESC
        LIMIT %s
        """,
        tuple(params),
    )


def get_yolo_detection(detection_id: str) -> dict[str, Any] | None:
    return kingbase.fetch_one(
        f"""
        SELECT
            d.*,
            a.source_system,
            a.source_table,
            a.source_pk,
            a.parent_asset_id,
            a.media_uri,
            a.content_hash,
            a.download_status,
            a.detect_status
        FROM {SCHEMA_NAME}.{TABLE_YOLO_DETECTION} d
        LEFT JOIN {SCHEMA_NAME}.{TABLE_MEDIA_ASSET} a
            ON a.asset_id = d.asset_id
        WHERE d.detection_id = %s
        """,
        (detection_id,),
    )


def update_yolo_detection_review(
    detection_id: str,
    *,
    review_status: str,
    review_result: str | None = None,
    reviewer_id: str | None = None,
    reviewer_name: str | None = None,
    review_comment: str | None = None,
) -> dict[str, Any] | None:
    normalized_status = _clamp_enum(review_status, VALID_REVIEW_STATUSES, "pending")
    normalized_result = review_result if review_result in VALID_REVIEW_RESULTS else None
    reviewed_at = None if normalized_status == "pending" else datetime.now()

    return kingbase.fetch_one(
        f"""
        UPDATE {SCHEMA_NAME}.{TABLE_YOLO_DETECTION}
        SET
            review_status = %s,
            review_result = %s,
            reviewer_id = %s,
            reviewer_name = %s,
            reviewed_at = %s,
            review_comment = %s,
            updated_at = NOW()
        WHERE detection_id = %s
        RETURNING *
        """,
        (
            normalized_status,
            normalized_result,
            reviewer_id,
            reviewer_name,
            reviewed_at,
            review_comment,
            detection_id,
        ),
    )


def upsert_training_sample(record: dict[str, Any]) -> str:
    asset_id = str(record.get("asset_id") or "").strip()
    if not asset_id:
        raise ValueError("asset_id is required")

    detection_id = str(record.get("detection_id") or "").strip() or None
    sample_type = _clamp_enum(record.get("sample_type"), VALID_SAMPLE_TYPES, "unlabeled")
    sample_id = str(
        record.get("sample_id")
        or build_training_sample_id(detection_id or "", asset_id, sample_type)
    )

    row = kingbase.fetch_one(
        f"""
        INSERT INTO {SCHEMA_NAME}.{TABLE_TRAINING_SAMPLE} (
            sample_id,
            asset_id,
            detection_id,
            source_type,
            source_ref_id,
            sample_media_uri,
            sample_image_blob,
            scenario_code,
            label_code,
            label_name,
            sample_type,
            annotation_status,
            annotation_json,
            dataset_split,
            dataset_version,
            target_model_code,
            quality_score,
            labeled_by,
            labeled_at,
            approved_by,
            approved_at,
            review_comment,
            created_at,
            updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON CONFLICT (sample_id) DO UPDATE SET
            asset_id = EXCLUDED.asset_id,
            detection_id = EXCLUDED.detection_id,
            source_type = EXCLUDED.source_type,
            source_ref_id = EXCLUDED.source_ref_id,
            sample_media_uri = EXCLUDED.sample_media_uri,
            sample_image_blob = COALESCE(EXCLUDED.sample_image_blob, {SCHEMA_NAME}.{TABLE_TRAINING_SAMPLE}.sample_image_blob),
            scenario_code = EXCLUDED.scenario_code,
            label_code = EXCLUDED.label_code,
            label_name = EXCLUDED.label_name,
            sample_type = EXCLUDED.sample_type,
            annotation_status = EXCLUDED.annotation_status,
            annotation_json = EXCLUDED.annotation_json,
            dataset_split = EXCLUDED.dataset_split,
            dataset_version = EXCLUDED.dataset_version,
            target_model_code = EXCLUDED.target_model_code,
            quality_score = EXCLUDED.quality_score,
            labeled_by = EXCLUDED.labeled_by,
            labeled_at = EXCLUDED.labeled_at,
            approved_by = EXCLUDED.approved_by,
            approved_at = EXCLUDED.approved_at,
            review_comment = EXCLUDED.review_comment,
            updated_at = NOW()
        RETURNING sample_id
        """,
        (
            sample_id,
            asset_id,
            detection_id,
            str(record.get("source_type") or "other"),
            record.get("source_ref_id"),
            record.get("sample_media_uri"),
            record.get("sample_image_blob"),
            record.get("scenario_code"),
            record.get("label_code"),
            record.get("label_name"),
            sample_type,
            _clamp_enum(record.get("annotation_status"), VALID_ANNOTATION_STATUSES, "unreviewed"),
            _json_text(record.get("annotation_json") or record.get("annotation")),
            _clamp_enum(record.get("dataset_split"), VALID_DATASET_SPLITS, "pool"),
            record.get("dataset_version"),
            record.get("target_model_code"),
            record.get("quality_score"),
            record.get("labeled_by"),
            _coerce_datetime(record.get("labeled_at")),
            record.get("approved_by"),
            _coerce_datetime(record.get("approved_at")),
            record.get("review_comment"),
        ),
    )
    return str((row or {}).get("sample_id") or sample_id)


def sync_training_sample_from_detection_review(detection_id: str) -> dict[str, Any] | None:
    detection = get_yolo_detection(detection_id)
    if not detection:
        return None

    review_result = str(detection.get("review_result") or "").strip().lower()
    if review_result == "true_positive":
        sample_type = "positive"
    elif review_result == "false_positive":
        sample_type = "negative"
    elif review_result == "false_negative":
        sample_type = "hard_negative"
    else:
        return None

    sample_id = upsert_training_sample(
        {
            "sample_id": build_training_sample_id(detection_id, str(detection.get("asset_id") or ""), sample_type),
            "asset_id": detection.get("asset_id"),
            "detection_id": detection_id,
            "source_type": "review_feedback",
            "source_ref_id": detection_id,
            "sample_media_uri": detection.get("media_uri"),
            "scenario_code": detection.get("scenario_code"),
            "label_code": detection.get("label_code"),
            "label_name": detection.get("label_name"),
            "sample_type": sample_type,
            "annotation_status": "approved",
            "annotation_json": detection.get("bbox_json"),
            "target_model_code": detection.get("model_code"),
            "quality_score": detection.get("confidence"),
            "labeled_by": detection.get("reviewer_name") or detection.get("reviewer_id"),
            "labeled_at": detection.get("reviewed_at"),
            "approved_by": detection.get("reviewer_name") or detection.get("reviewer_id"),
            "approved_at": detection.get("reviewed_at"),
            "review_comment": detection.get("review_comment"),
        }
    )

    return {
        "sample_id": sample_id,
        "detection_id": detection_id,
        "asset_id": detection.get("asset_id"),
        "sample_type": sample_type,
        "sample_media_uri": detection.get("media_uri"),
    }
