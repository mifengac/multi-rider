import json
import os
import sqlite3
import time
import shutil
from typing import Any

from config import MODEL_DEFAULT, SQLITE_DB_PATH, logger


JOB_COLUMNS = (
    "job_type",
    "id",
    "source_name",
    "source_type",
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
    "owner_key",
    "owner_ip",
    "conf_thresh",
    "batch_size",
    "imgsz",
    "classes_raw",
    "model_key",
    "zip_paths_json",
    "result_dir",
    "result_manifest_path",
    "identity_result_path",
    "identity_summary_json",
    "summary_text",
)

DATASET_COLUMNS = (
    "id",
    "name",
    "notes",
    "class_names_json",
    "status",
    "image_count",
    "labeled_count",
    "reviewed_count",
    "version_count",
    "root_dir",
    "created_ts",
    "updated_ts",
)


def _connect() -> sqlite3.Connection:
    parent = os.path.dirname(SQLITE_DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _existing_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _extract_zip_paths(job: dict[str, Any]) -> list[str]:
    if "zip_parts" in job and isinstance(job["zip_parts"], list):
        return [
            part.get("path")
            for part in job["zip_parts"]
            if isinstance(part, dict) and part.get("path")
        ]
    if "zip_paths" in job and isinstance(job["zip_paths"], list):
        return [path for path in job["zip_paths"] if path]
    if job.get("zip_path"):
        return [job["zip_path"]]
    return []


def _row_to_job(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    job = {column: row[column] for column in JOB_COLUMNS}
    try:
        zip_paths = json.loads(job.get("zip_paths_json") or "[]")
    except Exception:
        zip_paths = []
    try:
        identity_summary = json.loads(job.get("identity_summary_json") or "{}")
    except Exception:
        identity_summary = {}

    job["zip_paths"] = zip_paths
    job["zip_parts"] = [{"path": path, "name": os.path.basename(path)} for path in zip_paths]
    job["zip_path"] = zip_paths[0] if len(zip_paths) == 1 else None
    job["identity_summary"] = identity_summary
    return job


def _row_to_dataset(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    dataset = {column: row[column] for column in DATASET_COLUMNS}
    try:
        class_names = json.loads(dataset.get("class_names_json") or "[]")
    except Exception:
        class_names = []

    dataset["class_names"] = class_names
    return dataset


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL DEFAULT 'oracle',
                source_name TEXT,
                source_type TEXT,
                status TEXT NOT NULL,
                message TEXT,
                total INTEGER NOT NULL DEFAULT 0,
                processed INTEGER NOT NULL DEFAULT 0,
                kept INTEGER NOT NULL DEFAULT 0,
                notfound INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                downloaded INTEGER NOT NULL DEFAULT 0,
                start_ts INTEGER,
                end_ts INTEGER,
                owner_key TEXT,
                owner_ip TEXT,
                conf_thresh REAL,
                batch_size INTEGER,
                imgsz INTEGER,
                classes_raw TEXT,
                model_key TEXT NOT NULL DEFAULT 'general',
                zip_paths_json TEXT,
                result_dir TEXT,
                result_manifest_path TEXT,
                identity_result_path TEXT,
                identity_summary_json TEXT,
                summary_text TEXT
            )
            """
        )

        columns = _existing_columns(conn, "jobs")
        if "model_key" not in columns:
            conn.execute(
                "ALTER TABLE jobs ADD COLUMN model_key TEXT NOT NULL DEFAULT 'general'"
            )
        if "job_type" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN job_type TEXT NOT NULL DEFAULT 'oracle'")
        if "source_name" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN source_name TEXT")
        if "source_type" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN source_type TEXT")
        if "owner_key" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN owner_key TEXT")
        if "result_dir" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN result_dir TEXT")
        if "result_manifest_path" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN result_manifest_path TEXT")
        if "identity_result_path" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN identity_result_path TEXT")
        if "identity_summary_json" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN identity_summary_json TEXT")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_owner_key_start_ts ON jobs(owner_key, start_ts DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_owner_start_ts ON jobs(owner_ip, start_ts DESC)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_end_ts ON jobs(end_ts)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                class_names_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'draft',
                image_count INTEGER NOT NULL DEFAULT 0,
                labeled_count INTEGER NOT NULL DEFAULT 0,
                reviewed_count INTEGER NOT NULL DEFAULT 0,
                version_count INTEGER NOT NULL DEFAULT 0,
                root_dir TEXT NOT NULL,
                created_ts INTEGER NOT NULL,
                updated_ts INTEGER NOT NULL
            )
            """
        )

        dataset_columns = _existing_columns(conn, "datasets")
        if "notes" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
        if "class_names_json" not in dataset_columns:
            conn.execute(
                "ALTER TABLE datasets ADD COLUMN class_names_json TEXT NOT NULL DEFAULT '[]'"
            )
        if "status" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'")
        if "image_count" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN image_count INTEGER NOT NULL DEFAULT 0")
        if "labeled_count" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN labeled_count INTEGER NOT NULL DEFAULT 0")
        if "reviewed_count" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN reviewed_count INTEGER NOT NULL DEFAULT 0")
        if "version_count" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN version_count INTEGER NOT NULL DEFAULT 0")
        if "root_dir" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN root_dir TEXT NOT NULL DEFAULT ''")
        if "created_ts" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN created_ts INTEGER NOT NULL DEFAULT 0")
        if "updated_ts" not in dataset_columns:
            conn.execute("ALTER TABLE datasets ADD COLUMN updated_ts INTEGER NOT NULL DEFAULT 0")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_datasets_updated_ts ON datasets(updated_ts DESC)")
        conn.commit()


def save_job(job: dict[str, Any]) -> None:
    zip_paths = _extract_zip_paths(job)
    payload = {
        "job_type": job.get("job_type", "oracle"),
        "id": job.get("id", ""),
        "source_name": job.get("source_name", ""),
        "source_type": job.get("source_type", ""),
        "status": job.get("status", ""),
        "message": job.get("message", ""),
        "total": int(job.get("total") or 0),
        "processed": int(job.get("processed") or 0),
        "kept": int(job.get("kept") or 0),
        "notfound": int(job.get("notfound") or 0),
        "failed": int(job.get("failed") or 0),
        "downloaded": int(job.get("downloaded") or 0),
        "start_ts": job.get("start_ts"),
        "end_ts": job.get("end_ts"),
        "owner_key": job.get("owner_key", ""),
        "owner_ip": job.get("owner_ip", ""),
        "conf_thresh": job.get("conf_thresh"),
        "batch_size": job.get("batch_size"),
        "imgsz": job.get("imgsz"),
        "classes_raw": job.get("classes_raw", ""),
        "model_key": job.get("model_key", MODEL_DEFAULT),
        "zip_paths_json": json.dumps(zip_paths, ensure_ascii=False),
        "result_dir": job.get("result_dir", ""),
        "result_manifest_path": job.get("result_manifest_path", ""),
        "identity_result_path": job.get("identity_result_path", ""),
        "identity_summary_json": json.dumps(job.get("identity_summary") or {}, ensure_ascii=False),
        "summary_text": job.get("summary_text", ""),
    }

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                job_type, id, source_name, source_type, status, message, total, processed, kept, notfound, failed,
                downloaded, start_ts, end_ts, owner_key, owner_ip, conf_thresh, batch_size,
                imgsz, classes_raw, model_key, zip_paths_json, result_dir, result_manifest_path,
                identity_result_path, identity_summary_json, summary_text
            )
            VALUES (
                :job_type, :id, :source_name, :source_type, :status, :message, :total, :processed, :kept, :notfound, :failed,
                :downloaded, :start_ts, :end_ts, :owner_key, :owner_ip, :conf_thresh, :batch_size,
                :imgsz, :classes_raw, :model_key, :zip_paths_json, :result_dir, :result_manifest_path,
                :identity_result_path, :identity_summary_json, :summary_text
            )
            ON CONFLICT(id) DO UPDATE SET
                job_type = excluded.job_type,
                source_name = excluded.source_name,
                source_type = excluded.source_type,
                status = excluded.status,
                message = excluded.message,
                total = excluded.total,
                processed = excluded.processed,
                kept = excluded.kept,
                notfound = excluded.notfound,
                failed = excluded.failed,
                downloaded = excluded.downloaded,
                start_ts = excluded.start_ts,
                end_ts = excluded.end_ts,
                owner_key = excluded.owner_key,
                owner_ip = excluded.owner_ip,
                conf_thresh = excluded.conf_thresh,
                batch_size = excluded.batch_size,
                imgsz = excluded.imgsz,
                classes_raw = excluded.classes_raw,
                model_key = excluded.model_key,
                zip_paths_json = excluded.zip_paths_json,
                result_dir = excluded.result_dir,
                result_manifest_path = excluded.result_manifest_path,
                identity_result_path = excluded.identity_result_path,
                identity_summary_json = excluded.identity_summary_json,
                summary_text = excluded.summary_text
            """,
            payload,
        )
        conn.commit()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_job(row)


def save_dataset(dataset: dict[str, Any]) -> None:
    payload = {
        "id": dataset.get("id", ""),
        "name": dataset.get("name", ""),
        "notes": dataset.get("notes", ""),
        "class_names_json": json.dumps(dataset.get("class_names") or [], ensure_ascii=False),
        "status": dataset.get("status", "draft"),
        "image_count": int(dataset.get("image_count") or 0),
        "labeled_count": int(dataset.get("labeled_count") or 0),
        "reviewed_count": int(dataset.get("reviewed_count") or 0),
        "version_count": int(dataset.get("version_count") or 0),
        "root_dir": dataset.get("root_dir", ""),
        "created_ts": int(dataset.get("created_ts") or 0),
        "updated_ts": int(dataset.get("updated_ts") or 0),
    }

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO datasets (
                id, name, notes, class_names_json, status, image_count, labeled_count,
                reviewed_count, version_count, root_dir, created_ts, updated_ts
            )
            VALUES (
                :id, :name, :notes, :class_names_json, :status, :image_count, :labeled_count,
                :reviewed_count, :version_count, :root_dir, :created_ts, :updated_ts
            )
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                notes = excluded.notes,
                class_names_json = excluded.class_names_json,
                status = excluded.status,
                image_count = excluded.image_count,
                labeled_count = excluded.labeled_count,
                reviewed_count = excluded.reviewed_count,
                version_count = excluded.version_count,
                root_dir = excluded.root_dir,
                created_ts = excluded.created_ts,
                updated_ts = excluded.updated_ts
            """,
            payload,
        )
        conn.commit()


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    return _row_to_dataset(row)


def list_datasets(limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit or 100), 500))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM datasets
            ORDER BY updated_ts DESC, created_ts DESC, id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [_row_to_dataset(row) for row in rows if row is not None]


def list_jobs(owner_key: str, owner_ip: str, limit: int = 50) -> list[dict[str, Any]]:
    if not owner_key and not owner_ip:
        return []

    safe_limit = max(1, min(int(limit or 50), 200))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM jobs
            WHERE owner_key = ?
               OR (COALESCE(owner_key, '') = '' AND owner_ip = ?)
            ORDER BY start_ts DESC
            LIMIT ?
            """,
            (owner_key, owner_ip, safe_limit),
        ).fetchall()
    return [_row_to_job(row) for row in rows if row is not None]


def cleanup_old_jobs(days: int = 7) -> int:
    cutoff = int(time.time()) - max(days, 0) * 24 * 60 * 60
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, zip_paths_json, result_dir FROM jobs WHERE end_ts IS NOT NULL AND end_ts < ?",
            (cutoff,),
        ).fetchall()

        delete_ids = []
        for row in rows:
            delete_ids.append(row["id"])
            try:
                zip_paths = json.loads(row["zip_paths_json"] or "[]")
            except Exception:
                zip_paths = []
            for path in zip_paths:
                if path and os.path.isfile(path):
                    try:
                        os.remove(path)
                    except FileNotFoundError:
                        pass
                    except Exception as exc:
                        logger.warning("failed to remove zip file %s: %s", path, exc)
            result_dir = row["result_dir"]
            if result_dir and os.path.isdir(result_dir):
                try:
                    shutil.rmtree(result_dir, ignore_errors=False)
                except FileNotFoundError:
                    pass
                except Exception as exc:
                    logger.warning("failed to remove result dir %s: %s", result_dir, exc)

        if delete_ids:
            conn.executemany("DELETE FROM jobs WHERE id = ?", [(job_id,) for job_id in delete_ids])
            conn.commit()

    return len(delete_ids)


def mark_running_jobs_interrupted() -> int:
    now = int(time.time())
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE jobs
            SET status = 'interrupted',
                end_ts = COALESCE(end_ts, ?),
                message = CASE
                    WHEN message IS NULL OR message = '' THEN 'service restarted before job completed'
                    ELSE message
                END
            WHERE status = 'running'
            """,
            (now,),
        )
        conn.commit()
        return cursor.rowcount
