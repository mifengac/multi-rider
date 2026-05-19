from shared.db.kingbase import query_all, query_one


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


def lives_at(zjhm: str) -> list[dict]:
    sql = """
        SELECT hjdz, xzdxz
        FROM "jcgkzx_monitor"."wcnr_czrk"
        WHERE zjhm = %(zjhm)s
        LIMIT 1
    """
    row = query_one(sql, {"zjhm": zjhm})
    if not row:
        return []

    addresses = []
    for field in ("xzdxz", "hjdz"):
        value = row.get(field)
        if value and value not in addresses:
            addresses.append(value)

    results = []
    for address in addresses:
        node_id = f"L_{address}"
        results.append({
            "node": {
                "id": node_id,
                "type": "location",
                "label": address,
                "properties": {
                    "name": address,
                    "address": address,
                    "hjdz": row.get("hjdz"),
                    "xzdxz": row.get("xzdxz"),
                },
            },
            "edge": {
                "source": f"P_{zjhm}",
                "target": node_id,
                "type": "LIVES_AT",
                "label": "居住",
            },
        })
    return results


def same_school(zjhm: str, limit: int = 5) -> list[dict]:
    school_sql = """
        SELECT yxx
        FROM "ywdata"."b_per_qscxwcnr"
        WHERE zjhm = %(zjhm)s
          AND NULLIF(BTRIM(COALESCE(yxx, '')), '') IS NOT NULL
        LIMIT 1
    """
    row = query_one(school_sql, {"zjhm": zjhm})
    school_name = (row or {}).get("yxx")
    if not school_name:
        sfz_sql = """
            SELECT yxx
            FROM "ywdata"."zq_zfba_wcnr_sfzxx"
            WHERE sfzhm = %(zjhm)s
              AND NULLIF(BTRIM(COALESCE(yxx, '')), '') IS NOT NULL
            LIMIT 1
        """
        row = query_one(sfz_sql, {"zjhm": zjhm})
        school_name = (row or {}).get("yxx")
    if not school_name:
        return []

    peers_sql = """
        SELECT DISTINCT p.zjhm,
               COALESCE(p.xm, c.xm, s.xm) AS xm,
               sc.total_score,
               sc.risk_level
        FROM "jcgkzx_monitor"."wcnr_target_pool" p
        LEFT JOIN "ywdata"."b_per_qscxwcnr" c ON c.zjhm = p.zjhm
        LEFT JOIN "ywdata"."zq_zfba_wcnr_sfzxx" s ON s.sfzhm = p.zjhm
        LEFT JOIN "jcgkzx_monitor"."wcnr_score" sc ON sc.zjhm = p.zjhm
        WHERE p.zjhm <> %(zjhm)s
          AND (c.yxx = %(school)s OR s.yxx = %(school)s)
        LIMIT %(limit)s
    """
    results = []
    for row in query_all(peers_sql, {"zjhm": zjhm, "school": school_name, "limit": limit}):
        peer_zjhm = row.get("zjhm")
        if not peer_zjhm:
            continue
        node_id = f"P_{peer_zjhm}"
        results.append({
            "node": {
                "id": node_id,
                "type": "person",
                "label": row.get("xm") or peer_zjhm[:6],
                "properties": {
                    "zjhm": peer_zjhm,
                    "xm": row.get("xm"),
                    "school": school_name,
                    "risk_score": row.get("total_score"),
                    "risk_level": row.get("risk_level"),
                },
            },
            "edge": {
                "source": f"P_{zjhm}",
                "target": node_id,
                "type": "SAME_SCHOOL",
                "label": "同校",
                "properties": {"school": school_name},
            },
        })
    return results


def same_area(zjhm: str, limit: int = 5) -> list[dict]:
    area_sql = """
        SELECT sspcs
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        WHERE zjhm = %(zjhm)s
          AND sspcs IS NOT NULL
        LIMIT 1
    """
    row = query_one(area_sql, {"zjhm": zjhm})
    area_name = (row or {}).get("sspcs")
    if not area_name:
        return []

    peers_sql = """
        SELECT p.zjhm, p.xm, sc.total_score, sc.risk_level
        FROM "jcgkzx_monitor"."wcnr_target_pool" p
        LEFT JOIN "jcgkzx_monitor"."wcnr_score" sc ON sc.zjhm = p.zjhm
        WHERE p.sspcs = %(sspcs)s
          AND p.zjhm <> %(zjhm)s
        ORDER BY sc.total_score DESC NULLS LAST
        LIMIT %(limit)s
    """
    results = []
    for row in query_all(peers_sql, {"zjhm": zjhm, "sspcs": area_name, "limit": limit}):
        peer_zjhm = row.get("zjhm")
        if not peer_zjhm:
            continue
        node_id = f"P_{peer_zjhm}"
        results.append({
            "node": {
                "id": node_id,
                "type": "person",
                "label": row.get("xm") or peer_zjhm[:6],
                "properties": {
                    "zjhm": peer_zjhm,
                    "xm": row.get("xm"),
                    "sspcs": area_name,
                    "risk_score": row.get("total_score"),
                    "risk_level": row.get("risk_level"),
                },
            },
            "edge": {
                "source": f"P_{zjhm}",
                "target": node_id,
                "type": "SAME_AREA",
                "label": "同辖区",
                "properties": {"sspcs": area_name},
            },
        })
    return results
