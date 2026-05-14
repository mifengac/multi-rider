from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from typing import Any
from uuid import uuid4

from flask import Request

from shared.config.config import SQLITE_DB_PATH, logger
from shared.ownership.ownership import get_request_owner


def _connect() -> sqlite3.Connection:
    parent = os.path.dirname(SQLITE_DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_security_tables() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS security_audit_log (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT '',
                username TEXT NOT NULL DEFAULT '',
                display_name TEXT NOT NULL DEFAULT '',
                owner_key TEXT,
                owner_ip TEXT,
                module_code TEXT NOT NULL DEFAULT '',
                action_code TEXT NOT NULL DEFAULT '',
                target_type TEXT NOT NULL DEFAULT '',
                target_id TEXT NOT NULL DEFAULT '',
                request_path TEXT NOT NULL DEFAULT '',
                request_method TEXT NOT NULL DEFAULT '',
                request_payload_digest TEXT NOT NULL DEFAULT '',
                result_status TEXT NOT NULL DEFAULT 'success',
                error_msg TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_security_audit_created ON security_audit_log(created_ts DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_security_audit_module_action ON security_audit_log(module_code, action_code, created_ts DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS security_sensitive_access_log (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT '',
                username TEXT NOT NULL DEFAULT '',
                sfzh TEXT NOT NULL DEFAULT '',
                field_codes TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL DEFAULT '',
                module_code TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_security_sensitive_created ON security_sensitive_access_log(created_ts DESC)"
        )
        conn.commit()


def current_user_from_request(request: Request) -> dict[str, Any]:
    username = (
        request.headers.get("X-Police-Id")
        or request.headers.get("X-User-Name")
        or request.cookies.get("multi_rider_username")
        or ""
    ).strip()
    display_name = (request.headers.get("X-Display-Name") or username or "演示用户").strip()
    role = (request.headers.get("X-User-Role") or "admin").strip()
    org_code = (request.headers.get("X-Org-Code") or "").strip()
    org_name = (request.headers.get("X-Org-Name") or "本地演示环境").strip()
    user_id = username or request.remote_addr or "local"
    return {
        "user_id": user_id,
        "username": username or user_id,
        "display_name": display_name,
        "roles": [item.strip() for item in role.split(",") if item.strip()] or ["admin"],
        "org_code": org_code,
        "org_name": org_name,
    }


def _digest_request(request: Request) -> str:
    raw = f"{request.method}|{request.path}|{request.query_string.decode('utf-8', 'ignore')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def record_action(
    request: Request,
    *,
    module_code: str,
    action_code: str,
    target_type: str = "",
    target_id: str = "",
    result_status: str = "success",
    error_msg: str = "",
) -> None:
    try:
        ensure_security_tables()
        owner_key, owner_ip = get_request_owner(request)
        user = current_user_from_request(request)
        payload = {
            "id": "audit_" + uuid4().hex,
            "user_id": user.get("user_id", ""),
            "username": user.get("username", ""),
            "display_name": user.get("display_name", ""),
            "owner_key": owner_key,
            "owner_ip": owner_ip,
            "module_code": module_code,
            "action_code": action_code,
            "target_type": target_type,
            "target_id": target_id,
            "request_path": request.path,
            "request_method": request.method,
            "request_payload_digest": _digest_request(request),
            "result_status": result_status,
            "error_msg": error_msg[:1000],
            "created_ts": int(time.time()),
        }
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO security_audit_log (
                    id, user_id, username, display_name, owner_key, owner_ip,
                    module_code, action_code, target_type, target_id,
                    request_path, request_method, request_payload_digest,
                    result_status, error_msg, created_ts
                )
                VALUES (
                    :id, :user_id, :username, :display_name, :owner_key, :owner_ip,
                    :module_code, :action_code, :target_type, :target_id,
                    :request_path, :request_method, :request_payload_digest,
                    :result_status, :error_msg, :created_ts
                )
                """,
                payload,
            )
            conn.commit()
    except Exception as exc:
        logger.warning("failed to write audit log: %s", exc)


def record_sensitive_access(
    request: Request,
    *,
    sfzh: str,
    field_codes: list[str],
    purpose: str,
    module_code: str = "security",
) -> None:
    ensure_security_tables()
    user = current_user_from_request(request)
    payload = {
        "id": "sensitive_" + uuid4().hex,
        "user_id": user.get("user_id", ""),
        "username": user.get("username", ""),
        "sfzh": sfzh or "",
        "field_codes": ",".join(field_codes or []),
        "purpose": purpose or "",
        "module_code": module_code,
        "created_ts": int(time.time()),
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO security_sensitive_access_log (
                id, user_id, username, sfzh, field_codes, purpose, module_code, created_ts
            )
            VALUES (
                :id, :user_id, :username, :sfzh, :field_codes, :purpose, :module_code, :created_ts
            )
            """,
            payload,
        )
        conn.commit()


def list_audit_logs(
    *,
    module_code: str = "",
    action_code: str = "",
    username: str = "",
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_security_tables()
    safe_limit = max(1, min(int(limit or 100), 500))
    clauses = []
    params: list[Any] = []
    if module_code:
        clauses.append("module_code = ?")
        params.append(module_code)
    if action_code:
        clauses.append("action_code = ?")
        params.append(action_code)
    if username:
        clauses.append("(username LIKE ? OR display_name LIKE ?)")
        params.extend([f"%{username}%", f"%{username}%"])
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM security_audit_log
            {where}
            ORDER BY created_ts DESC
            LIMIT ?
            """,
            (*params, safe_limit),
        ).fetchall()
    return [dict(row) for row in rows]


def list_sensitive_access_logs(limit: int = 100) -> list[dict[str, Any]]:
    ensure_security_tables()
    safe_limit = max(1, min(int(limit or 100), 500))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM security_sensitive_access_log
            ORDER BY created_ts DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]

