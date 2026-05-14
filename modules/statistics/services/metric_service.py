from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any

from shared.config.config import KINGBASE_APP_SCHEMA, SQLITE_DB_PATH, logger


def _connect() -> sqlite3.Connection:
    parent = os.path.dirname(SQLITE_DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _row_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _parse_ts(value: str | None, default: int) -> int:
    raw = str(value or "").strip()
    if not raw:
        return default
    if raw.isdigit():
        return int(raw)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(raw, fmt)
            if fmt == "%Y-%m-%d" and raw == value:
                dt = datetime(dt.year, dt.month, dt.day)
            return int(dt.timestamp())
        except Exception:
            continue
    return default


def normalize_period(args: dict[str, Any] | None = None) -> dict[str, int | str]:
    args = args or {}
    now = int(time.time())
    start_default = int((datetime.now() - timedelta(days=30)).timestamp())
    start_ts = _parse_ts(args.get("start") or args.get("start_ts"), start_default)
    end_ts = _parse_ts(args.get("end") or args.get("end_ts"), now)
    if end_ts < start_ts:
        start_ts, end_ts = end_ts, start_ts
    return {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "start": datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M:%S"),
        "end": datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d %H:%M:%S"),
    }


def _job_where(period: dict[str, Any]) -> tuple[str, tuple[Any, ...]]:
    return "WHERE COALESCE(start_ts, end_ts, 0) BETWEEN ? AND ?", (
        period["start_ts"],
        period["end_ts"],
    )


def get_detection_metrics(period: dict[str, Any] | None = None) -> dict[str, Any]:
    period = period or normalize_period()
    with _connect() as conn:
        if not _table_exists(conn, "jobs"):
            return {
                "summary": {},
                "by_status": [],
                "by_model": [],
                "by_type": [],
                "daily": [],
                "recent_jobs": [],
            }

        where, params = _job_where(period)
        summary = _row_dict(
            conn.execute(
                f"""
                SELECT
                    COUNT(*) AS task_count,
                    COALESCE(SUM(total), 0) AS total_items,
                    COALESCE(SUM(processed), 0) AS processed_items,
                    COALESCE(SUM(kept), 0) AS hit_items,
                    COALESCE(SUM(failed), 0) AS failed_items,
                    COALESCE(SUM(downloaded), 0) AS downloaded_items,
                    COALESCE(AVG(CASE
                        WHEN end_ts IS NOT NULL AND start_ts IS NOT NULL AND end_ts > start_ts
                        THEN end_ts - start_ts
                    END), 0) AS avg_seconds
                FROM jobs
                {where}
                """,
                params,
            ).fetchone()
        )
        processed = _safe_int(summary.get("processed_items"))
        hits = _safe_int(summary.get("hit_items"))
        failed = _safe_int(summary.get("failed_items"))
        summary["hit_rate"] = round(hits / processed, 4) if processed else 0
        summary["failed_rate"] = round(failed / processed, 4) if processed else 0

        by_status = [
            dict(row)
            for row in conn.execute(
                f"SELECT COALESCE(status, 'unknown') AS status, COUNT(*) AS count FROM jobs {where} GROUP BY status ORDER BY count DESC",
                params,
            ).fetchall()
        ]
        by_model = [
            dict(row)
            for row in conn.execute(
                f"SELECT COALESCE(model_key, 'unknown') AS model_key, COUNT(*) AS count, COALESCE(SUM(kept), 0) AS hit_items FROM jobs {where} GROUP BY model_key ORDER BY count DESC",
                params,
            ).fetchall()
        ]
        by_type = [
            dict(row)
            for row in conn.execute(
                f"SELECT COALESCE(job_type, 'unknown') AS job_type, COUNT(*) AS count, COALESCE(SUM(total), 0) AS total_items FROM jobs {where} GROUP BY job_type ORDER BY count DESC",
                params,
            ).fetchall()
        ]
        daily = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                    strftime('%Y-%m-%d', COALESCE(start_ts, end_ts, 0), 'unixepoch', 'localtime') AS day,
                    COUNT(*) AS task_count,
                    COALESCE(SUM(total), 0) AS total_items,
                    COALESCE(SUM(kept), 0) AS hit_items
                FROM jobs
                {where}
                GROUP BY day
                ORDER BY day
                """,
                params,
            ).fetchall()
        ]
        recent_jobs = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT id, job_type, source_name, status, total, kept, failed, start_ts, end_ts, model_key
                FROM jobs
                {where}
                ORDER BY COALESCE(start_ts, 0) DESC, id DESC
                LIMIT 20
                """,
                params,
            ).fetchall()
        ]

    return {
        "summary": summary,
        "by_status": by_status,
        "by_model": by_model,
        "by_type": by_type,
        "daily": daily,
        "recent_jobs": recent_jobs,
    }


def get_dispatch_metrics(period: dict[str, Any] | None = None) -> dict[str, Any]:
    period = period or normalize_period()
    with _connect() as conn:
        data: dict[str, Any] = {
            "queue_summary": {},
            "queue_by_dispatch_status": [],
            "queue_by_sms_status": [],
            "dispatch_records": {},
            "dispatch_by_status": [],
            "sms_records": {},
            "sms_by_status": [],
            "recent_queue": [],
        }
        if _table_exists(conn, "dispatch_queue"):
            params = (period["start_ts"], period["end_ts"])
            where = "WHERE COALESCE(created_ts, updated_ts, 0) BETWEEN ? AND ?"
            queue_summary = _row_dict(
                conn.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(DISTINCT NULLIF(person_id_no, '')) AS person_count,
                        COALESCE(AVG(similarity_score), 0) AS avg_similarity
                    FROM dispatch_queue
                    {where}
                    """,
                    params,
                ).fetchone()
            )
            data["queue_summary"] = queue_summary
            data["queue_by_dispatch_status"] = [
                dict(row)
                for row in conn.execute(
                    f"SELECT COALESCE(dispatch_status, 'unknown') AS status, COUNT(*) AS count FROM dispatch_queue {where} GROUP BY dispatch_status ORDER BY count DESC",
                    params,
                ).fetchall()
            ]
            data["queue_by_sms_status"] = [
                dict(row)
                for row in conn.execute(
                    f"SELECT COALESCE(sms_status, 'unknown') AS status, COUNT(*) AS count FROM dispatch_queue {where} GROUP BY sms_status ORDER BY count DESC",
                    params,
                ).fetchall()
            ]
            data["recent_queue"] = [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT id, person_name, person_id_no, illegal_type, dispatch_status, sms_status, created_ts, updated_ts
                    FROM dispatch_queue
                    {where}
                    ORDER BY COALESCE(updated_ts, created_ts, 0) DESC
                    LIMIT 20
                    """,
                    params,
                ).fetchall()
            ]

        if _table_exists(conn, "dispatch_records"):
            params = (period["start_ts"], period["end_ts"])
            where = "WHERE COALESCE(created_ts, 0) BETWEEN ? AND ?"
            data["dispatch_records"] = _row_dict(
                conn.execute(f"SELECT COUNT(*) AS total FROM dispatch_records {where}", params).fetchone()
            )
            data["dispatch_by_status"] = [
                dict(row)
                for row in conn.execute(
                    f"SELECT COALESCE(status, 'unknown') AS status, COUNT(*) AS count FROM dispatch_records {where} GROUP BY status ORDER BY count DESC",
                    params,
                ).fetchall()
            ]

        if _table_exists(conn, "dispatch_sms_records"):
            params = (period["start_ts"], period["end_ts"])
            where = "WHERE COALESCE(created_ts, 0) BETWEEN ? AND ?"
            data["sms_records"] = _row_dict(
                conn.execute(f"SELECT COUNT(*) AS total FROM dispatch_sms_records {where}", params).fetchone()
            )
            data["sms_by_status"] = [
                dict(row)
                for row in conn.execute(
                    f"SELECT COALESCE(status, 'unknown') AS status, COUNT(*) AS count FROM dispatch_sms_records {where} GROUP BY status ORDER BY count DESC",
                    params,
                ).fetchall()
            ]
    return data


def get_person_metrics(period: dict[str, Any] | None = None) -> dict[str, Any]:
    period = period or normalize_period()
    dispatch = get_dispatch_metrics(period)
    queue = dispatch.get("recent_queue") or []
    top_people = []
    seen: dict[str, dict[str, Any]] = {}
    for item in queue:
        sfzh = str(item.get("person_id_no") or "").strip()
        if not sfzh:
            continue
        target = seen.setdefault(
            sfzh,
            {
                "person_id_no": sfzh,
                "person_name": item.get("person_name") or "",
                "count": 0,
                "latest_ts": 0,
            },
        )
        target["count"] += 1
        target["latest_ts"] = max(_safe_int(target.get("latest_ts")), _safe_int(item.get("updated_ts") or item.get("created_ts")))
    top_people = sorted(seen.values(), key=lambda x: (-_safe_int(x.get("count")), -_safe_int(x.get("latest_ts"))))[:20]
    return {
        "summary": {
            "dispatch_person_count": _safe_int((dispatch.get("queue_summary") or {}).get("person_count")),
            "recent_hit_people": len(top_people),
        },
        "top_people": top_people,
    }


def get_gang_metrics(period: dict[str, Any] | None = None) -> dict[str, Any]:
    period = period or normalize_period()
    result = {
        "summary": {
            "gang_count": 0,
            "member_count": 0,
            "source": "unavailable",
        },
        "top_gangs": [],
        "error": "",
    }
    try:
        from shared.db.kingbase import fetch_all, fetch_one, table_exists

        if not table_exists(KINGBASE_APP_SCHEMA, "hm_gang_result"):
            result["summary"]["source"] = "hm_gang_result not found"
            return result

        latest = fetch_one(
            f"""
            SELECT run_id
            FROM {KINGBASE_APP_SCHEMA}.hm_gang_result
            ORDER BY computed_at DESC
            LIMIT 1
            """
        )
        if not latest or not latest.get("run_id"):
            result["summary"]["source"] = "hm_gang_result empty"
            return result
        run_id = latest["run_id"]
        summary = fetch_one(
            f"""
            SELECT COUNT(DISTINCT gang_id) AS gang_count,
                   COUNT(DISTINCT member_sfzh) AS member_count
            FROM {KINGBASE_APP_SCHEMA}.hm_gang_result
            WHERE run_id = %s
            """,
            (run_id,),
        ) or {}
        top_gangs = fetch_all(
            f"""
            SELECT gang_id,
                   COUNT(*) AS member_count,
                   MAX(centrality_score) AS max_centrality
            FROM {KINGBASE_APP_SCHEMA}.hm_gang_result
            WHERE run_id = %s
            GROUP BY gang_id
            ORDER BY member_count DESC, max_centrality DESC NULLS LAST
            LIMIT 20
            """,
            (run_id,),
        )
        result["summary"] = {
            "gang_count": _safe_int(summary.get("gang_count")),
            "member_count": _safe_int(summary.get("member_count")),
            "source": "hm_gang_result",
            "run_id": run_id,
        }
        result["top_gangs"] = [dict(row) for row in top_gangs]
    except Exception as exc:
        logger.warning("failed to load gang statistics: %s", exc)
        result["error"] = str(exc)
    return result


def get_overview_metrics(args: dict[str, Any] | None = None) -> dict[str, Any]:
    period = normalize_period(args)
    detection = get_detection_metrics(period)
    dispatch = get_dispatch_metrics(period)
    person = get_person_metrics(period)
    gang = get_gang_metrics(period)
    det_summary = detection.get("summary") or {}
    queue_summary = dispatch.get("queue_summary") or {}
    dispatch_records = dispatch.get("dispatch_records") or {}
    sms_records = dispatch.get("sms_records") or {}
    overview = {
        "detection_tasks": _safe_int(det_summary.get("task_count")),
        "processed_items": _safe_int(det_summary.get("processed_items")),
        "hit_items": _safe_int(det_summary.get("hit_items")),
        "hit_rate": _safe_float(det_summary.get("hit_rate")),
        "dispatch_queue_total": _safe_int(queue_summary.get("total")),
        "dispatch_person_count": _safe_int(queue_summary.get("person_count")),
        "dispatch_records_total": _safe_int(dispatch_records.get("total")),
        "sms_records_total": _safe_int(sms_records.get("total")),
        "gang_count": _safe_int((gang.get("summary") or {}).get("gang_count")),
        "gang_member_count": _safe_int((gang.get("summary") or {}).get("member_count")),
    }
    return {
        "generated_ts": int(time.time()),
        "period": period,
        "overview": overview,
        "detection": detection,
        "dispatch": dispatch,
        "person": person,
        "gang": gang,
        "notes": [
            "警情下降率、案件下降率、干预成功率需要外部警情/案件基线和处置反馈数据，当前作为待接入指标。",
            "YOLO 结构化标签统计依赖 04 工作包完成后接入 hm_ai_yolo_detection。",
        ],
    }


def build_report(args: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = get_overview_metrics(args)
    payload["report_type"] = (args or {}).get("report_type") or "custom"
    payload["title"] = (args or {}).get("title") or "猎影哨兵态势统计报告"
    return payload


def report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)
