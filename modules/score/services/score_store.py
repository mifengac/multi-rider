import json
from shared.db.kingbase import query_one, query_all, execute


def upsert_score(zjhm, total_score, risk_level, dim_case, dim_behavior,
                 dim_family, dim_education, dim_social, detail_json):
    sql = """
        INSERT INTO "jcgkzx_monitoer"."wcnr_score"
            (zjhm, total_score, risk_level, dim_case, dim_behavior,
             dim_family, dim_education, dim_social, calc_time, detail_json)
        VALUES
            (%(zjhm)s, %(total_score)s, %(risk_level)s, %(dim_case)s, %(dim_behavior)s,
             %(dim_family)s, %(dim_education)s, %(dim_social)s, CURRENT_TIMESTAMP, %(detail_json)s)
        ON CONFLICT (zjhm) DO UPDATE SET
            total_score = EXCLUDED.total_score,
            risk_level = EXCLUDED.risk_level,
            dim_case = EXCLUDED.dim_case,
            dim_behavior = EXCLUDED.dim_behavior,
            dim_family = EXCLUDED.dim_family,
            dim_education = EXCLUDED.dim_education,
            dim_social = EXCLUDED.dim_social,
            calc_time = CURRENT_TIMESTAMP,
            detail_json = EXCLUDED.detail_json
    """
    execute(sql, {
        "zjhm": zjhm, "total_score": total_score, "risk_level": risk_level,
        "dim_case": dim_case, "dim_behavior": dim_behavior,
        "dim_family": dim_family, "dim_education": dim_education,
        "dim_social": dim_social, "detail_json": json.dumps(detail_json, ensure_ascii=False),
    })


def append_history(zjhm, total_score, risk_level):
    sql = """
        INSERT INTO "jcgkzx_monitoer"."wcnr_score_history"
            (zjhm, total_score, risk_level)
        VALUES (%(zjhm)s, %(total_score)s, %(risk_level)s)
    """
    execute(sql, {"zjhm": zjhm, "total_score": total_score, "risk_level": risk_level})


def get_score(zjhm):
    sql = """
        SELECT s.*, p.xm
        FROM "jcgkzx_monitoer"."wcnr_score" s
        LEFT JOIN "jcgkzx_monitoer"."wcnr_target_pool" p ON p.zjhm = s.zjhm
        WHERE s.zjhm = %(zjhm)s
    """
    return query_one(sql, {"zjhm": zjhm})


def get_score_list(min_score=0, max_score=100, risk_level=None,
                   area_code=None, page=1, size=20, sort="desc"):
    conditions = ["s.total_score >= %(min_score)s", "s.total_score <= %(max_score)s"]
    params = {"min_score": min_score, "max_score": max_score}

    if risk_level:
        conditions.append("s.risk_level = %(risk_level)s")
        params["risk_level"] = risk_level

    if area_code:
        conditions.append("p.ssfjdm = %(area_code)s")
        params["area_code"] = area_code

    where_clause = " AND ".join(conditions)
    order = "DESC" if sort == "desc" else "ASC"

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM "jcgkzx_monitoer"."wcnr_score" s
        LEFT JOIN "jcgkzx_monitoer"."wcnr_target_pool" p ON p.zjhm = s.zjhm
        WHERE {where_clause}
    """
    total = query_one(count_sql, params).get("total", 0)

    offset = (page - 1) * size
    params["limit"] = size
    params["offset"] = offset

    list_sql = f"""
        SELECT s.zjhm, p.xm, p.xb, p.source_type, p.ssfj, p.sspcs,
               s.total_score, s.risk_level, s.dim_case, s.dim_behavior,
               s.dim_family, s.dim_education, s.dim_social, s.calc_time
        FROM "jcgkzx_monitoer"."wcnr_score" s
        LEFT JOIN "jcgkzx_monitoer"."wcnr_target_pool" p ON p.zjhm = s.zjhm
        WHERE {where_clause}
        ORDER BY s.total_score {order}
        LIMIT %(limit)s OFFSET %(offset)s
    """
    items = query_all(list_sql, params)
    return total, items


def get_score_trend(zjhm, months=6):
    sql = """
        SELECT total_score, risk_level, calc_time
        FROM "jcgkzx_monitoer"."wcnr_score_history"
        WHERE zjhm = %(zjhm)s
          AND calc_time >= CURRENT_TIMESTAMP - make_interval(months => %(months)s)
        ORDER BY calc_time
    """
    return query_all(sql, {"zjhm": zjhm, "months": months})
