from shared.age_filter import build_age_exists_clause, get_age_filter_threshold
from shared.db.kingbase import query_all


def _case_trend_sql(age_clause: str) -> str:
    return f"""
        SELECT TO_CHAR(a."ajxx_fasj", 'YYYY-MM') AS month,
               COUNT(DISTINCT a."ajxx_ajbh") AS count
        FROM "ywdata"."zq_zfba_ajxx" a
        WHERE a."ajxx_fasj" >= CURRENT_DATE - make_interval(months => %(months)s)
          AND a."ajxx_fasj" IS NOT NULL
          {age_clause}
        GROUP BY TO_CHAR(a."ajxx_fasj", 'YYYY-MM')
        ORDER BY month
    """


def get_case_trend(months: int = 12) -> dict:
    params = {"months": months}
    if get_age_filter_threshold() <= 0:
        return {"points": query_all(_case_trend_sql(""), params), "degraded": False}

    rows = query_all(_case_trend_sql(build_age_exists_clause("a", "x")), params)
    if rows:
        return {"points": rows, "degraded": False}
    return {"points": query_all(_case_trend_sql(""), params), "degraded": True}


def get_person_trend(months: int = 12) -> list[dict]:
    sql = """
        SELECT TO_CHAR(calc_time, 'YYYY-MM') AS month,
               COUNT(DISTINCT zjhm) AS count
        FROM "jcgkzx_monitor"."wcnr_score_history"
        WHERE calc_time >= CURRENT_DATE - make_interval(months => %(months)s)
          AND total_score >= 60
        GROUP BY TO_CHAR(calc_time, 'YYYY-MM')
        ORDER BY month
    """
    return query_all(sql, {"months": months})


def get_score_trend(months: int = 12) -> list[dict]:
    sql = """
        SELECT TO_CHAR(calc_time, 'YYYY-MM') AS month,
               ROUND(AVG(total_score), 1) AS avg_score
        FROM "jcgkzx_monitor"."wcnr_score_history"
        WHERE calc_time >= CURRENT_DATE - make_interval(months => %(months)s)
        GROUP BY TO_CHAR(calc_time, 'YYYY-MM')
        ORDER BY month
    """
    return query_all(sql, {"months": months})
