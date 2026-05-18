from shared.db.kingbase import query_all


def get_case_trend(months: int = 12) -> list[dict]:
    sql = """
        SELECT TO_CHAR(ajxx_fasj, 'YYYY-MM') AS month, COUNT(*) AS count
        FROM "ywdata"."zq_zfba_wcnr_ajxx"
        WHERE ajxx_fasj >= CURRENT_DATE - make_interval(months => %(months)s)
          AND ajxx_fasj IS NOT NULL
        GROUP BY TO_CHAR(ajxx_fasj, 'YYYY-MM')
        ORDER BY month
    """
    return query_all(sql, {"months": months})


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
