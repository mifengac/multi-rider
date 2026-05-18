from shared.db.kingbase import query_all, query_one


def get_recent_trajectory(zjhm: str, days: int = 30) -> list[dict]:
    sql = """
        SELECT device_name, shot_time, jd, wd, ssfj, sspcs
        FROM "jcgkzx_monitoer"."wcnr_ryrl_gj"
        WHERE zjhm = %(zjhm)s
          AND shot_time >= CURRENT_TIMESTAMP - make_interval(days => %(days)s)
        ORDER BY shot_time DESC
        LIMIT 50
    """
    return query_all(sql, {"zjhm": zjhm, "days": days})


def get_hotspots(zjhm: str, days: int = 90) -> list[dict]:
    sql = """
        SELECT device_name AS location, COUNT(*) AS count,
               AVG(jd) AS avg_jd, AVG(wd) AS avg_wd
        FROM "jcgkzx_monitoer"."wcnr_ryrl_gj"
        WHERE zjhm = %(zjhm)s
          AND shot_time >= CURRENT_TIMESTAMP - make_interval(days => %(days)s)
          AND device_name IS NOT NULL
        GROUP BY device_name
        ORDER BY count DESC
        LIMIT 10
    """
    return query_all(sql, {"zjhm": zjhm, "days": days})


def get_time_pattern(zjhm: str, days: int = 90) -> dict:
    sql = """
        SELECT
            EXTRACT(HOUR FROM shot_time)::INTEGER AS hour,
            COUNT(*) AS count
        FROM "jcgkzx_monitoer"."wcnr_ryrl_gj"
        WHERE zjhm = %(zjhm)s
          AND shot_time >= CURRENT_TIMESTAMP - make_interval(days => %(days)s)
        GROUP BY EXTRACT(HOUR FROM shot_time)
        ORDER BY hour
    """
    rows = query_all(sql, {"zjhm": zjhm, "days": days})

    total = sum(r.get("count", 0) for r in rows)
    night_count = sum(r.get("count", 0) for r in rows
                      if r.get("hour", 0) >= 22 or r.get("hour", 0) < 6)

    night_ratio = round(night_count / total, 2) if total > 0 else 0

    peak_hours = sorted(rows, key=lambda x: x.get("count", 0), reverse=True)[:3]

    return {
        "total_records": total,
        "night_ratio": night_ratio,
        "peak_hours": [{"hour": r["hour"], "count": r["count"]} for r in peak_hours],
        "hourly_distribution": rows,
    }


def get_last_seen(zjhm: str) -> dict:
    sql = """
        SELECT device_name, shot_time, jd, wd
        FROM "jcgkzx_monitoer"."wcnr_ryrl_gj"
        WHERE zjhm = %(zjhm)s
        ORDER BY shot_time DESC
        LIMIT 1
    """
    return query_one(sql, {"zjhm": zjhm})
