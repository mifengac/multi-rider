from __future__ import annotations

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


def run_all_rules() -> dict:
    rules = {
        "high_risk_face_hit": scan_high_risk_face_hit,
        "night_aggregation": scan_night_aggregation,
        "abnormal_hotel_checkin": scan_abnormal_hotel_checkin,
    }
    result = {}
    for name, func in rules.items():
        try:
            result[name] = func()
        except Exception as exc:
            logger.warning("Alert rule %s failed: %s", name, exc)
            result[name] = 0
    return result
