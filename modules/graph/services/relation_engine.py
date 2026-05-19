from shared.db.kingbase import query_all


def _format_time(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def appeared_at(zjhm: str, limit: int = 3) -> list[dict]:
    sql = """
        SELECT device_name, COUNT(*) AS count, MAX(shot_time) AS last_time,
               AVG(jd) AS jd, AVG(wd) AS wd
        FROM "jcgkzx_monitor"."wcnr_ryrl_gj"
        WHERE zjhm = %(zjhm)s
          AND device_name IS NOT NULL
        GROUP BY device_name
        ORDER BY count DESC, last_time DESC
        LIMIT %(limit)s
    """
    rows = query_all(sql, {"zjhm": zjhm, "limit": limit})
    results = []
    for row in rows:
        device_name = row.get("device_name")
        if not device_name:
            continue
        node_id = f"L_{device_name}"
        results.append({
            "node": {
                "id": node_id,
                "type": "location",
                "label": device_name,
                "properties": {
                    "device_name": device_name,
                    "count": row.get("count"),
                    "last_time": _format_time(row.get("last_time")),
                    "jd": _to_float(row.get("jd")),
                    "wd": _to_float(row.get("wd")),
                },
            },
            "edge": {
                "source": f"P_{zjhm}",
                "target": node_id,
                "type": "APPEARED_AT",
                "label": "出现",
                "properties": {
                    "count": row.get("count"),
                    "last_time": _format_time(row.get("last_time")),
                },
            },
        })
    return results


def checked_in(zjhm: str, limit: int = 5) -> list[dict]:
    sql = """
        SELECT lgmc, lgdz, COUNT(*) AS count, MAX(rzsj) AS last_time
        FROM "jcgkzx_monitor"."wcnr_ly_checkin"
        WHERE zjhm = %(zjhm)s
          AND lgmc IS NOT NULL
        GROUP BY lgmc, lgdz
        ORDER BY count DESC, last_time DESC
        LIMIT %(limit)s
    """
    rows = query_all(sql, {"zjhm": zjhm, "limit": limit})
    results = []
    for row in rows:
        hotel_name = row.get("lgmc")
        if not hotel_name:
            continue
        node_id = f"O_{hotel_name}"
        results.append({
            "node": {
                "id": node_id,
                "type": "organization",
                "label": hotel_name,
                "properties": {
                    "lgmc": hotel_name,
                    "lgdz": row.get("lgdz"),
                    "count": row.get("count"),
                    "last_time": _format_time(row.get("last_time")),
                },
            },
            "edge": {
                "source": f"P_{zjhm}",
                "target": node_id,
                "type": "CHECKED_IN",
                "label": "入住",
                "properties": {
                    "count": row.get("count"),
                    "last_time": _format_time(row.get("last_time")),
                },
            },
        })
    return results


def victims_of_case(ajbh: str) -> list[dict]:
    sql = """
        SELECT DISTINCT
               s."saryxx_sfzh" AS zjhm,
               s."saryxx_xm" AS xm,
               s."saryxx_csrq" AS csrq,
               s."saryxx_shfd" AS shfd
        FROM "ywdata"."zq_zfba_saryxx" s
        WHERE POSITION(%(ajbh)s IN COALESCE(s."ajxx_ajbhs", '')) > 0
          AND NULLIF(BTRIM(COALESCE(s."saryxx_sfzh", '')), '') IS NOT NULL
    """
    rows = query_all(sql, {"ajbh": ajbh})
    results = []
    for row in rows:
        zjhm = row.get("zjhm") or row.get("saryxx_sfzh")
        if not zjhm:
            continue
        results.append({
            "zjhm": zjhm,
            "xm": row.get("xm") or row.get("saryxx_xm"),
            "csrq": row.get("csrq") or row.get("saryxx_csrq"),
            "shfd": row.get("shfd") or row.get("saryxx_shfd"),
        })
    return results
