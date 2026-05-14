from __future__ import annotations

import json
import os
import sqlite3
import time
from uuid import uuid4

from shared.config.config import SQLITE_DB_PATH
from modules.statistics.services.metric_service import build_report


def _connect() -> sqlite3.Connection:
    parent = os.path.dirname(SQLITE_DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_report_table() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS statistics_report_cache (
                id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL DEFAULT 'custom',
                title TEXT NOT NULL DEFAULT '',
                period_start INTEGER NOT NULL DEFAULT 0,
                period_end INTEGER NOT NULL DEFAULT 0,
                report_json TEXT NOT NULL DEFAULT '{}',
                created_ts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_statistics_report_cache_created ON statistics_report_cache(created_ts DESC)"
        )
        conn.commit()


def generate_report(args: dict | None = None) -> dict:
    args = args or {}
    ensure_report_table()
    report = build_report(args)
    report_id = "report_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]
    period = report.get("period") or {}
    row = {
        "id": report_id,
        "report_type": report.get("report_type") or "custom",
        "title": report.get("title") or "",
        "period_start": int(period.get("start_ts") or 0),
        "period_end": int(period.get("end_ts") or 0),
        "report_json": json.dumps(report, ensure_ascii=False),
        "created_ts": int(time.time()),
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO statistics_report_cache (
                id, report_type, title, period_start, period_end, report_json, created_ts
            )
            VALUES (
                :id, :report_type, :title, :period_start, :period_end, :report_json, :created_ts
            )
            """,
            row,
        )
        conn.commit()
    return {"report_id": report_id, "report": report}


def list_reports(limit: int = 20) -> list[dict]:
    ensure_report_table()
    safe_limit = max(1, min(int(limit or 20), 100))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, report_type, title, period_start, period_end, created_ts
            FROM statistics_report_cache
            ORDER BY created_ts DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]

