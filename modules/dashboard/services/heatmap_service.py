from shared.db.kingbase import query_all


def get_heatmap(days: int = 30) -> list[dict]:
    sql = """
        SELECT ROUND(jd::NUMERIC, 3) AS lng,
               ROUND(wd::NUMERIC, 3) AS lat,
               COUNT(*) AS weight
        FROM "jcgkzx_monitor"."wcnr_ryrl_gj"
        WHERE shot_time >= CURRENT_TIMESTAMP - make_interval(days => %(days)s)
          AND jd IS NOT NULL
          AND wd IS NOT NULL
        GROUP BY ROUND(jd::NUMERIC, 3), ROUND(wd::NUMERIC, 3)
        ORDER BY weight DESC
    """
    rows = query_all(sql, {"days": days})
    return [
        {
            "lng": float(row.get("lng")),
            "lat": float(row.get("lat")),
            "weight": int(row.get("weight", 0)),
        }
        for row in rows
        if row.get("lng") is not None and row.get("lat") is not None
    ]
