import json
import os
import sqlite3
import time
from typing import Any

from config import MODEL_DEFAULT, SQLITE_DB_PATH, logger


JOB_COLUMNS = (
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
    "conf_thresh",
    "batch_size",
    "imgsz",
    "classes_raw",
    "model_key",
    "zip_paths_json",
    "summary_text",
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

    job["zip_paths"] = zip_paths
    job["zip_parts"] = [{"path": path, "name": os.path.basename(path)} for path in zip_paths]
    job["zip_path"] = zip_paths[0] if len(zip_paths) == 1 else None
    return job


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
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
                owner_ip TEXT,
                conf_thresh REAL,
                batch_size INTEGER,
                imgsz INTEGER,
                classes_raw TEXT,
                model_key TEXT NOT NULL DEFAULT 'general',
                zip_paths_json TEXT,
                summary_text TEXT
            )
            """
        )

        columns = _existing_columns(conn, "jobs")
        if "model_key" not in columns:
            conn.execute(
                "ALTER TABLE jobs ADD COLUMN model_key TEXT NOT NULL DEFAULT 'general'"
            )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_owner_start_ts ON jobs(owner_ip, start_ts DESC)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_end_ts ON jobs(end_ts)")
        conn.commit()


def save_job(job: dict[str, Any]) -> None:
    zip_paths = _extract_zip_paths(job)
    payload = {
        "id": job.get("id", ""),
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
        "owner_ip": job.get("owner_ip", ""),
        "conf_thresh": job.get("conf_thresh"),
        "batch_size": job.get("batch_size"),
        "imgsz": job.get("imgsz"),
        "classes_raw": job.get("classes_raw", ""),
        "model_key": job.get("model_key", MODEL_DEFAULT),
        "zip_paths_json": json.dumps(zip_paths, ensure_ascii=False),
        "summary_text": job.get("summary_text", ""),
    }

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, status, message, total, processed, kept, notfound, failed,
                downloaded, start_ts, end_ts, owner_ip, conf_thresh, batch_size,
                imgsz, classes_raw, model_key, zip_paths_json, summary_text
            )
            VALUES (
                :id, :status, :message, :total, :processed, :kept, :notfound, :failed,
                :downloaded, :start_ts, :end_ts, :owner_ip, :conf_thresh, :batch_size,
                :imgsz, :classes_raw, :model_key, :zip_paths_json, :summary_text
            )
            ON CONFLICT(id) DO UPDATE SET
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
                owner_ip = excluded.owner_ip,
                conf_thresh = excluded.conf_thresh,
                batch_size = excluded.batch_size,
                imgsz = excluded.imgsz,
                classes_raw = excluded.classes_raw,
                model_key = excluded.model_key,
                zip_paths_json = excluded.zip_paths_json,
                summary_text = excluded.summary_text
            """,
            payload,
        )
        conn.commit()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_job(row)


def list_jobs(owner_ip: str, limit: int = 50) -> list[dict[str, Any]]:
    if not owner_ip:
        return []

    safe_limit = max(1, min(int(limit or 50), 200))
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE owner_ip = ? ORDER BY start_ts DESC LIMIT ?",
            (owner_ip, safe_limit),
        ).fetchall()
    return [_row_to_job(row) for row in rows if row is not None]


def cleanup_old_jobs(days: int = 7) -> int:
    cutoff = int(time.time()) - max(days, 0) * 24 * 60 * 60
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, zip_paths_json FROM jobs WHERE end_ts IS NOT NULL AND end_ts < ?",
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
