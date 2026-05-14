from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any
from uuid import uuid4

from shared.config.config import SQLITE_DB_PATH


def _connect() -> sqlite3.Connection:
    parent = os.path.dirname(SQLITE_DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _json_loads(value: str, default: Any) -> Any:
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def ensure_ruizhi_tables() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ruizhi_call_log (
                id TEXT PRIMARY KEY,
                module_code TEXT NOT NULL DEFAULT '',
                operation TEXT NOT NULL DEFAULT '',
                model_name TEXT NOT NULL DEFAULT '',
                request_digest TEXT NOT NULL DEFAULT '',
                response_digest TEXT NOT NULL DEFAULT '',
                status_code INTEGER NOT NULL DEFAULT 0,
                success INTEGER NOT NULL DEFAULT 0,
                elapsed_ms INTEGER NOT NULL DEFAULT 0,
                error_msg TEXT NOT NULL DEFAULT '',
                operator_id TEXT NOT NULL DEFAULT '',
                operator_name TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ruizhi_call_log_created ON ruizhi_call_log(created_ts DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ruizhi_call_log_module ON ruizhi_call_log(module_code, operation, created_ts DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ruizhi_assistant_session (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                scenario_code TEXT NOT NULL DEFAULT 'general',
                related_sfzh TEXT NOT NULL DEFAULT '',
                related_job_id TEXT NOT NULL DEFAULT '',
                related_queue_id TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL DEFAULT 0,
                updated_ts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ruizhi_session_updated ON ruizhi_assistant_session(updated_ts DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ruizhi_assistant_message (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                content_text TEXT NOT NULL DEFAULT '',
                content_digest TEXT NOT NULL DEFAULT '',
                model_name TEXT NOT NULL DEFAULT '',
                tool_call_json TEXT NOT NULL DEFAULT '{}',
                docs_ref_json TEXT NOT NULL DEFAULT '[]',
                created_ts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ruizhi_message_session ON ruizhi_assistant_message(session_id, created_ts)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ruizhi_kb_mapping (
                id TEXT PRIMARY KEY,
                kb_name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                split_config_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                created_by TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL DEFAULT 0,
                updated_ts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ruizhi_kb_file (
                id TEXT PRIMARY KEY,
                kb_name TEXT NOT NULL DEFAULT '',
                file_id TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL DEFAULT '',
                bytes INTEGER NOT NULL DEFAULT 0,
                parse_status TEXT NOT NULL DEFAULT '',
                callback_status TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def save_call_log(item: dict[str, Any]) -> str:
    ensure_ruizhi_tables()
    log_id = item.get("id") or "rz_call_" + uuid4().hex
    payload = {
        "id": log_id,
        "module_code": item.get("module_code", ""),
        "operation": item.get("operation", ""),
        "model_name": item.get("model_name", ""),
        "request_digest": item.get("request_digest", ""),
        "response_digest": item.get("response_digest", ""),
        "status_code": int(item.get("status_code") or 0),
        "success": 1 if item.get("success") else 0,
        "elapsed_ms": int(item.get("elapsed_ms") or 0),
        "error_msg": str(item.get("error_msg") or "")[:2000],
        "operator_id": item.get("operator_id", ""),
        "operator_name": item.get("operator_name", ""),
        "created_ts": int(item.get("created_ts") or time.time()),
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ruizhi_call_log (
                id, module_code, operation, model_name, request_digest, response_digest,
                status_code, success, elapsed_ms, error_msg, operator_id, operator_name, created_ts
            )
            VALUES (
                :id, :module_code, :operation, :model_name, :request_digest, :response_digest,
                :status_code, :success, :elapsed_ms, :error_msg, :operator_id, :operator_name, :created_ts
            )
            """,
            payload,
        )
        conn.commit()
    return log_id


def list_call_logs(limit: int = 100, module_code: str = "") -> list[dict[str, Any]]:
    ensure_ruizhi_tables()
    safe_limit = max(1, min(int(limit or 100), 500))
    params: list[Any] = []
    where = ""
    if module_code:
        where = "WHERE module_code = ?"
        params.append(module_code)
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM ruizhi_call_log
            {where}
            ORDER BY created_ts DESC
            LIMIT ?
            """,
            (*params, safe_limit),
        ).fetchall()
    return [dict(row) for row in rows]


def create_session(
    *,
    title: str,
    scenario_code: str = "general",
    related_sfzh: str = "",
    related_job_id: str = "",
    related_queue_id: str = "",
    created_by: str = "",
) -> dict[str, Any]:
    ensure_ruizhi_tables()
    now = int(time.time())
    session = {
        "id": "rz_session_" + uuid4().hex,
        "title": title or "AI 研判会话",
        "scenario_code": scenario_code or "general",
        "related_sfzh": related_sfzh or "",
        "related_job_id": related_job_id or "",
        "related_queue_id": related_queue_id or "",
        "created_by": created_by or "",
        "created_ts": now,
        "updated_ts": now,
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ruizhi_assistant_session (
                id, title, scenario_code, related_sfzh, related_job_id, related_queue_id,
                created_by, created_ts, updated_ts
            )
            VALUES (
                :id, :title, :scenario_code, :related_sfzh, :related_job_id, :related_queue_id,
                :created_by, :created_ts, :updated_ts
            )
            """,
            session,
        )
        conn.commit()
    return session


def touch_session(session_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE ruizhi_assistant_session SET updated_ts = ? WHERE id = ?",
            (int(time.time()), session_id),
        )
        conn.commit()


def get_session(session_id: str) -> dict[str, Any] | None:
    ensure_ruizhi_tables()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM ruizhi_assistant_session WHERE id = ? LIMIT 1", (session_id,)).fetchone()
    return dict(row) if row else None


def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    ensure_ruizhi_tables()
    safe_limit = max(1, min(int(limit or 50), 200))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM ruizhi_assistant_session
            ORDER BY updated_ts DESC, created_ts DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_message(
    *,
    session_id: str,
    role: str,
    content_text: str,
    content_digest: str = "",
    model_name: str = "",
    tool_call: Any = None,
    docs_ref: Any = None,
) -> dict[str, Any]:
    ensure_ruizhi_tables()
    message = {
        "id": "rz_msg_" + uuid4().hex,
        "session_id": session_id,
        "role": role,
        "content_text": content_text or "",
        "content_digest": content_digest or "",
        "model_name": model_name or "",
        "tool_call_json": _json_dumps(tool_call or {}),
        "docs_ref_json": _json_dumps(docs_ref or []),
        "created_ts": int(time.time()),
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ruizhi_assistant_message (
                id, session_id, role, content_text, content_digest, model_name,
                tool_call_json, docs_ref_json, created_ts
            )
            VALUES (
                :id, :session_id, :role, :content_text, :content_digest, :model_name,
                :tool_call_json, :docs_ref_json, :created_ts
            )
            """,
            message,
        )
        conn.commit()
    touch_session(session_id)
    return message


def list_messages(session_id: str, limit: int = 200) -> list[dict[str, Any]]:
    ensure_ruizhi_tables()
    safe_limit = max(1, min(int(limit or 200), 500))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM ruizhi_assistant_message
            WHERE session_id = ?
            ORDER BY created_ts ASC
            LIMIT ?
            """,
            (session_id, safe_limit),
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["tool_call"] = _json_loads(item.pop("tool_call_json", ""), {})
        item["docs_ref"] = _json_loads(item.pop("docs_ref_json", ""), [])
        items.append(item)
    return items


def upsert_kb_mapping(item: dict[str, Any]) -> dict[str, Any]:
    ensure_ruizhi_tables()
    now = int(time.time())
    kb_name = item.get("kb_name") or item.get("name") or ""
    payload = {
        "id": item.get("id") or "rz_kb_" + uuid4().hex,
        "kb_name": kb_name,
        "display_name": item.get("display_name") or kb_name,
        "description": item.get("description", ""),
        "split_config_json": _json_dumps(item.get("split_config") or {}),
        "status": item.get("status", "active"),
        "created_by": item.get("created_by", ""),
        "created_ts": int(item.get("created_ts") or now),
        "updated_ts": now,
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ruizhi_kb_mapping (
                id, kb_name, display_name, description, split_config_json, status, created_by, created_ts, updated_ts
            )
            VALUES (
                :id, :kb_name, :display_name, :description, :split_config_json, :status, :created_by, :created_ts, :updated_ts
            )
            ON CONFLICT(kb_name) DO UPDATE SET
                display_name = excluded.display_name,
                description = excluded.description,
                split_config_json = excluded.split_config_json,
                status = excluded.status,
                updated_ts = excluded.updated_ts
            """,
            payload,
        )
        conn.commit()
    return payload


def list_kb_mappings(limit: int = 100) -> list[dict[str, Any]]:
    ensure_ruizhi_tables()
    safe_limit = max(1, min(int(limit or 100), 500))
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM ruizhi_kb_mapping ORDER BY updated_ts DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["split_config"] = _json_loads(item.pop("split_config_json", ""), {})
        items.append(item)
    return items


def save_kb_file(item: dict[str, Any]) -> dict[str, Any]:
    ensure_ruizhi_tables()
    payload = {
        "id": item.get("id") or "rz_kb_file_" + uuid4().hex,
        "kb_name": item.get("kb_name", ""),
        "file_id": item.get("file_id", ""),
        "filename": item.get("filename", ""),
        "purpose": item.get("purpose", ""),
        "bytes": int(item.get("bytes") or 0),
        "parse_status": item.get("parse_status", ""),
        "callback_status": item.get("callback_status", ""),
        "created_ts": int(item.get("created_ts") or time.time()),
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ruizhi_kb_file (
                id, kb_name, file_id, filename, purpose, bytes, parse_status, callback_status, created_ts
            )
            VALUES (
                :id, :kb_name, :file_id, :filename, :purpose, :bytes, :parse_status, :callback_status, :created_ts
            )
            """,
            payload,
        )
        conn.commit()
    return payload

