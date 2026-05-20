from __future__ import annotations

import importlib
import json
import os
import time
from datetime import datetime

from shared.config.config import logger
from shared.db.kingbase import execute, query_all, query_one


def _table_exists(schema: str, table: str) -> bool:
    sql = """
        SELECT 1 AS exists
        FROM information_schema.tables
        WHERE table_schema = %(s)s
          AND table_name = %(t)s
        LIMIT 1
    """
    try:
        return bool(query_one(sql, {"s": schema, "t": table}))
    except Exception as exc:
        logger.warning("Table existence probe failed for %s.%s: %s", schema, table, exc)
        return False


def _tables_exist(*tables: tuple[str, str]) -> bool:
    return all(_table_exists(schema, table) for schema, table in tables)


def _table_columns(schema: str, table: str) -> set[str]:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %(s)s
          AND table_name = %(t)s
    """
    try:
        return {str(row.get("column_name")) for row in query_all(sql, {"s": schema, "t": table}) if row.get("column_name")}
    except Exception as exc:
        logger.warning("Column probe failed for %s.%s: %s", schema, table, exc)
        return set()


def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _pick_first_column(columns: set[str], candidates: tuple[str, ...]) -> str | None:
    lower_map = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


def _alert_exists(alert_type: str, zjhm: str | None, location: str | None, window_minutes: int = 30) -> bool:
    conditions = [
        "alert_type = %(alert_type)s",
        "trigger_time >= CURRENT_TIMESTAMP - make_interval(mins => %(window_minutes)s)",
    ]
    params = {
        "alert_type": alert_type,
        "window_minutes": window_minutes,
    }
    if zjhm:
        conditions.append("zjhm = %(zjhm)s")
        params["zjhm"] = zjhm
    if location:
        conditions.append("location = %(location)s")
        params["location"] = location

    sql = """
        SELECT 1 AS exists
        FROM "jcgkzx_monitor"."wcnr_alert"
        WHERE {where_clause}
        LIMIT 1
    """.format(where_clause=" AND ".join(conditions))
    return bool(query_one(sql, params))


def _insert_alert(
    *,
    zjhm: str | None,
    xm: str | None,
    alert_type: str,
    alert_level: str,
    alert_content: str,
    location: str | None,
    trigger_time,
) -> bool:
    if _alert_exists(alert_type, zjhm, location):
        return False

    sql = """
        INSERT INTO "jcgkzx_monitor"."wcnr_alert"
            (zjhm, xm, alert_type, alert_level, alert_content, location, trigger_time)
        VALUES
            (%(zjhm)s, %(xm)s, %(alert_type)s, %(alert_level)s,
             %(alert_content)s, %(location)s, %(trigger_time)s)
    """
    params = {
        "zjhm": zjhm,
        "xm": xm,
        "alert_type": alert_type,
        "alert_level": alert_level,
        "alert_content": alert_content,
        "location": location,
        "trigger_time": trigger_time,
    }
    try:
        return execute(sql, params) > 0
    except Exception as exc:
        logger.warning("Insert alert failed type=%s zjhm=%s: %s", alert_type, zjhm, exc)
        return False


def scan_high_risk_face_hit(window_minutes: int = 5) -> int:
    if not _tables_exist(
        ("jcgkzx_monitor", "wcnr_ryrl_gj"),
        ("jcgkzx_monitor", "wcnr_score"),
        ("jcgkzx_monitor", "wcnr_target_pool"),
        ("jcgkzx_monitor", "wcnr_alert"),
    ):
        return 0

    sql = """
        SELECT g.zjhm, p.xm, g.device_name, g.shot_time, s.total_score
        FROM "jcgkzx_monitor"."wcnr_ryrl_gj" g
        JOIN "jcgkzx_monitor"."wcnr_score" s
          ON s.zjhm = g.zjhm
        LEFT JOIN "jcgkzx_monitor"."wcnr_target_pool" p
          ON p.zjhm = g.zjhm
        WHERE g.shot_time >= CURRENT_TIMESTAMP - make_interval(mins => %(window_minutes)s)
          AND s.total_score >= 80
          AND g.zjhm IS NOT NULL
        ORDER BY g.shot_time DESC
        LIMIT 200
    """
    count = 0
    for row in query_all(sql, {"window_minutes": max(1, int(window_minutes or 5))}):
        zjhm = row.get("zjhm")
        device_name = row.get("device_name") or "未知设备"
        xm = row.get("xm") or zjhm
        if not zjhm:
            continue
        inserted = _insert_alert(
            zjhm=zjhm,
            xm=xm,
            alert_type="high_risk_face_hit",
            alert_level="critical",
            alert_content=f"{xm} 在 {device_name} 出现",
            location=device_name,
            trigger_time=row.get("shot_time"),
        )
        if inserted:
            count += 1
    return count


def scan_night_aggregation() -> int:
    if not _tables_exist(
        ("jcgkzx_monitor", "wcnr_ryrl_gj"),
        ("jcgkzx_monitor", "wcnr_score"),
        ("jcgkzx_monitor", "wcnr_target_pool"),
        ("jcgkzx_monitor", "wcnr_alert"),
    ):
        return 0

    sql = """
        WITH recent AS (
            SELECT g.device_name,
                   g.zjhm,
                   COALESCE(p.xm, g.zjhm) AS xm,
                   g.shot_time,
                   COALESCE(s.total_score, 0) AS total_score
            FROM "jcgkzx_monitor"."wcnr_ryrl_gj" g
            LEFT JOIN "jcgkzx_monitor"."wcnr_score" s
              ON s.zjhm = g.zjhm
            LEFT JOIN "jcgkzx_monitor"."wcnr_target_pool" p
              ON p.zjhm = g.zjhm
            WHERE g.shot_time >= CURRENT_TIMESTAMP - INTERVAL '30 minutes'
              AND (EXTRACT(HOUR FROM g.shot_time) >= 22 OR EXTRACT(HOUR FROM g.shot_time) < 6)
              AND g.device_name IS NOT NULL
              AND g.zjhm IS NOT NULL
        )
        SELECT device_name,
               COUNT(DISTINCT zjhm) AS person_count,
               COUNT(DISTINCT CASE WHEN total_score >= 60 THEN zjhm END) AS high_risk_count,
               MAX(shot_time) AS last_time,
               STRING_AGG(DISTINCT xm, '、') AS names
        FROM recent
        GROUP BY device_name
        HAVING COUNT(DISTINCT zjhm) >= 3
           AND COUNT(DISTINCT CASE WHEN total_score >= 60 THEN zjhm END) >= 2
        ORDER BY last_time DESC
        LIMIT 50
    """
    count = 0
    for row in query_all(sql):
        device_name = row.get("device_name") or "未知地点"
        person_count = int(row.get("person_count") or 0)
        high_risk_count = int(row.get("high_risk_count") or 0)
        inserted = _insert_alert(
            zjhm=None,
            xm=row.get("names") or "多人聚集",
            alert_type="night_aggregation",
            alert_level="warning",
            alert_content=f"{device_name} 夜间聚集 {person_count} 人，其中高风险 {high_risk_count} 人",
            location=device_name,
            trigger_time=row.get("last_time"),
        )
        if inserted:
            count += 1
    return count


def scan_abnormal_hotel_checkin() -> int:
    if not _tables_exist(
        ("jcgkzx_monitor", "wcnr_ly_checkin"),
        ("jcgkzx_monitor", "wcnr_target_pool"),
        ("jcgkzx_monitor", "wcnr_alert"),
    ):
        return 0

    has_family = _table_exists("ywdata", "b_per_qskjwcnr")
    has_basic = _table_exists("jcgkzx_monitor", "wcnr_czrk")
    family_join = 'LEFT JOIN "ywdata"."b_per_qskjwcnr" f ON f.zjhm = c.zjhm' if has_family else ""
    basic_join = 'LEFT JOIN "jcgkzx_monitor"."wcnr_czrk" r ON r.zjhm = c.zjhm' if has_basic else ""
    guardian_parts = []
    if has_family:
        guardian_parts.append("f.jhr1xm")
    if has_basic:
        guardian_parts.extend(["r.fqxm", "r.mqxm"])
    guardian_expr = "COALESCE({})".format(", ".join(guardian_parts)) if guardian_parts else "NULL::VARCHAR"

    sql = """
        WITH checkins AS (
            SELECT c.zjhm,
                   p.xm,
                   c.lgmc,
                   c.lgdz,
                   c.rzsj,
                   c.tfrxm,
                   {guardian_expr} AS guardian_name
            FROM "jcgkzx_monitor"."wcnr_ly_checkin" c
            JOIN "jcgkzx_monitor"."wcnr_target_pool" p
              ON p.zjhm = c.zjhm
            {family_join}
            {basic_join}
            WHERE c.rzsj >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
              AND c.zjhm IS NOT NULL
        )
        SELECT *
        FROM checkins
        WHERE NULLIF(BTRIM(COALESCE(tfrxm, '')), '') IS NULL
           OR guardian_name IS NULL
           OR tfrxm <> guardian_name
        ORDER BY rzsj DESC
        LIMIT 100
    """.format(
        guardian_expr=guardian_expr,
        family_join=family_join,
        basic_join=basic_join,
    )
    count = 0
    for row in query_all(sql):
        zjhm = row.get("zjhm")
        hotel_name = row.get("lgmc") or row.get("lgdz") or "旅馆"
        if not zjhm:
            continue
        xm = row.get("xm") or zjhm
        inserted = _insert_alert(
            zjhm=zjhm,
            xm=xm,
            alert_type="abnormal_hotel_checkin",
            alert_level="warning",
            alert_content=f"{xm} 入住{hotel_name}，同住人异常",
            location=hotel_name,
            trigger_time=row.get("rzsj"),
        )
        if inserted:
            count += 1
    return count


def scan_school_perimeter(radius_m: int = 200) -> int:
    if not _tables_exist(
        ("jcgkzx_monitor", "wcnr_ryrl_gj"),
        ("jcgkzx_monitor", "wcnr_score"),
        ("jcgkzx_monitor", "wcnr_target_pool"),
        ("jcgkzx_monitor", "wcnr_alert"),
        ("ywdata", "sh_fzxxsj_xx"),
    ):
        return 0

    columns = _table_columns("ywdata", "sh_fzxxsj_xx")
    lng_col = _pick_first_column(columns, ("jd", "lng", "longitude", "经度"))
    lat_col = _pick_first_column(columns, ("wd", "lat", "latitude", "纬度"))
    if not lng_col or not lat_col:
        logger.info("School perimeter rule skipped: ywdata.sh_fzxxsj_xx has no usable lng/lat columns")
        return 0

    name_col = _pick_first_column(columns, ("xxmc", "xxjc", "school_name", "name", "mc", "学校名称"))
    school_name_expr = f"s.{_quote_ident(name_col)}" if name_col else "'学校'"
    lng_expr = f"s.{_quote_ident(lng_col)}"
    lat_expr = f"s.{_quote_ident(lat_col)}"

    try:
        safe_radius = max(1, int(radius_m or 200))
    except (TypeError, ValueError):
        safe_radius = 200

    dist_expr = f"""
        2 * 6371000 * ASIN(SQRT(LEAST(1,
            POWER(SIN(RADIANS((r.lat - school.school_lat) / 2)), 2)
            + COS(RADIANS(school.school_lat)) * COS(RADIANS(r.lat))
            * POWER(SIN(RADIANS((r.lng - school.school_lng) / 2)), 2)
        )))
    """
    sql = f"""
        WITH school AS (
            SELECT {school_name_expr} AS xxmc,
                   {lng_expr}::DOUBLE PRECISION AS school_lng,
                   {lat_expr}::DOUBLE PRECISION AS school_lat
            FROM "ywdata"."sh_fzxxsj_xx" s
            WHERE {lng_expr} IS NOT NULL
              AND {lat_expr} IS NOT NULL
        ),
        recent AS (
            SELECT g.zjhm,
                   COALESCE(p.xm, g.xm, g.zjhm) AS xm,
                   g.device_name,
                   g.shot_time,
                   g.jd::DOUBLE PRECISION AS lng,
                   g.wd::DOUBLE PRECISION AS lat
            FROM "jcgkzx_monitor"."wcnr_ryrl_gj" g
            JOIN "jcgkzx_monitor"."wcnr_score" sc
              ON sc.zjhm = g.zjhm
            LEFT JOIN "jcgkzx_monitor"."wcnr_target_pool" p
              ON p.zjhm = g.zjhm
            WHERE g.shot_time >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
              AND sc.total_score >= 80
              AND g.zjhm IS NOT NULL
              AND g.jd IS NOT NULL
              AND g.wd IS NOT NULL
        ),
        hits AS (
            SELECT r.zjhm, r.xm, r.device_name, r.shot_time, school.xxmc,
                   {dist_expr} AS dist
            FROM recent r
            CROSS JOIN school
        )
        SELECT *
        FROM hits
        WHERE dist <= %(radius_m)s
        ORDER BY shot_time DESC
        LIMIT 200
    """

    count = 0
    try:
        rows = query_all(sql, {"radius_m": safe_radius})
    except Exception as exc:
        logger.warning("School perimeter rule query failed: %s", exc)
        return 0

    for row in rows:
        zjhm = row.get("zjhm")
        xm = row.get("xm") or zjhm
        school_name = row.get("xxmc") or "学校"
        try:
            distance = round(float(row.get("dist") or 0))
        except (TypeError, ValueError):
            distance = 0
        inserted = _insert_alert(
            zjhm=zjhm,
            xm=xm,
            alert_type="school_perimeter_high_risk",
            alert_level="warning",
            alert_content=f"{xm} 出现在学校 {school_name} 周边 ~{distance}米",
            location=school_name,
            trigger_time=row.get("shot_time"),
        )
        if inserted:
            count += 1
    return count


SPEEDING_KEYWORDS = ("飙车", "翘车头", "炸街")


def _row_text(row: dict) -> str:
    fields = (
        "category", "class_name", "label", "type", "event_type", "illegal_type",
        "source_name", "device_id", "device_name", "summary_text", "classes_raw",
        "model_key",
    )
    return " ".join(str(row.get(field) or "") for field in fields)


def _row_confidence(row: dict) -> float:
    for key in ("confidence", "conf", "score", "probability"):
        value = row.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _row_trigger_time(row: dict):
    for key in ("trigger_time", "detected_at", "created_at", "end_time", "end_ts", "start_ts"):
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except (OSError, ValueError):
                return None
        return value
    return datetime.now()


def _call_detection_repository(window_minutes: int, min_confidence: float) -> list[dict] | None:
    try:
        repo = importlib.import_module("modules.detection.repositories.ai_result_repository")
    except Exception:
        return None

    for name in ("list_recent_results", "get_recent_results", "query_recent_results", "find_recent_results"):
        func = getattr(repo, name, None)
        if not callable(func):
            continue
        for args, kwargs in (
            ((), {"window_minutes": window_minutes, "min_confidence": min_confidence}),
            ((), {"minutes": window_minutes, "confidence": min_confidence}),
            ((), {"limit": 200}),
            ((), {}),
        ):
            try:
                rows = func(*args, **kwargs)
                if rows is None:
                    continue
                return [dict(row) for row in rows]
            except TypeError:
                continue
            except Exception as exc:
                logger.warning("Detection repository call %s failed: %s", name, exc)
                return []
    logger.info("Detection repository has no supported recent-result interface")
    return []


def _manifest_detection_rows(job: dict) -> list[dict]:
    manifest_path = job.get("result_manifest_path")
    if not manifest_path or not os.path.isfile(manifest_path):
        return []
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except Exception as exc:
        logger.warning("Read detection manifest failed %s: %s", manifest_path, exc)
        return []

    rows = []
    for item in manifest.get("items") or []:
        if not isinstance(item, dict):
            continue
        detections = item.get("detections") or item.get("boxes") or item.get("results") or []
        if detections:
            for detection in detections:
                if isinstance(detection, dict):
                    row = dict(job)
                    row.update(item)
                    row.update(detection)
                    rows.append(row)
        else:
            row = dict(job)
            row.update(item)
            rows.append(row)
    return rows


def _sqlite_detection_rows(window_minutes: int, min_confidence: float) -> list[dict]:
    try:
        from shared.db.sqlite import list_all_jobs
    except Exception as exc:
        logger.info("SQLite detection job reader unavailable: %s", exc)
        return []

    cutoff = time.time() - max(1, int(window_minutes or 5)) * 60
    rows = []
    try:
        jobs = list_all_jobs(limit=100)
    except Exception as exc:
        logger.warning("List detection jobs failed: %s", exc)
        return []

    for job in jobs:
        end_ts = job.get("end_ts") or job.get("start_ts") or 0
        try:
            if float(end_ts or 0) < cutoff:
                continue
        except (TypeError, ValueError):
            continue
        if str(job.get("status") or "") not in {"done", "completed"}:
            continue
        manifest_rows = _manifest_detection_rows(job)
        if manifest_rows:
            rows.extend(manifest_rows)
            continue
        if int(job.get("kept") or 0) <= 0:
            continue
        row = dict(job)
        row["confidence"] = float(job.get("conf_thresh") or 0)
        rows.append(row)
    return [row for row in rows if _row_confidence(row) >= min_confidence]


def scan_speeding_detection() -> int:
    if not _table_exists("jcgkzx_monitor", "wcnr_alert"):
        return 0

    window_minutes = 5
    min_confidence = 0.6
    rows = _call_detection_repository(window_minutes, min_confidence)
    if not rows:
        rows = _sqlite_detection_rows(window_minutes, min_confidence)
    if not rows:
        logger.info("Speeding detection rule skipped: no detection repository rows or SQLite results")
        return 0

    count = 0
    for row in rows:
        text = _row_text(row)
        model_key = str(row.get("model_key") or "").lower()
        if not any(keyword in text for keyword in SPEEDING_KEYWORDS) and model_key != "bczj":
            continue
        confidence = _row_confidence(row)
        if confidence < min_confidence:
            continue
        device_id = row.get("device_id") or row.get("device_name") or row.get("source_name")
        if not device_id:
            continue
        inserted = _insert_alert(
            zjhm=row.get("zjhm"),
            xm=row.get("xm"),
            alert_type="speeding_detected",
            alert_level="warning",
            alert_content=f"飙车检测命中 device={device_id}",
            location=row.get("source_name") or row.get("device_name") or str(device_id),
            trigger_time=_row_trigger_time(row),
        )
        if inserted:
            count += 1
    return count


def run_all_rules() -> dict:
    rules = {
        "high_risk_face_hit": scan_high_risk_face_hit,
        "night_aggregation": scan_night_aggregation,
        "abnormal_hotel_checkin": scan_abnormal_hotel_checkin,
        "school_perimeter_high_risk": scan_school_perimeter,
        "speeding_detected": scan_speeding_detection,
    }
    result = {}
    for name, func in rules.items():
        try:
            result[name] = func()
        except Exception as exc:
            logger.warning("Alert rule %s failed: %s", name, exc)
            result[name] = 0
    return result
