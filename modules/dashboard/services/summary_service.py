from shared.db.kingbase import query_one


def get_summary() -> dict:
    total_persons_sql = """
        SELECT COUNT(*) AS total FROM "jcgkzx_monitor"."wcnr_target_pool"
    """
    high_risk_sql = """
        SELECT COUNT(*) AS total FROM "jcgkzx_monitor"."wcnr_score"
        WHERE total_score >= 60
    """
    month_cases_sql = """
        SELECT COUNT(DISTINCT a."ajxx_ajbh") AS total
        FROM "ywdata"."zq_zfba_ajxx" a
        WHERE a."ajxx_fasj" >= DATE_TRUNC('month', CURRENT_DATE)
          AND EXISTS (
              SELECT 1 FROM "ywdata"."zq_zfba_xyrxx" x
              WHERE x."ajxx_join_ajxx_ajbh" = a."ajxx_ajbh"
                AND LENGTH(x."xyrxx_sfzh") = 18
                AND DATE_PART('year',
                      AGE(a."ajxx_fasj"::date,
                          TO_DATE(SUBSTR(x."xyrxx_sfzh", 7, 8), 'YYYYMMDD'))
                    ) < 18
          )
    """
    extreme_risk_sql = """
        SELECT COUNT(*) AS total FROM "jcgkzx_monitor"."wcnr_score"
        WHERE total_score >= 80
    """
    avg_score_sql = """
        SELECT ROUND(AVG(total_score), 1) AS avg_score
        FROM "jcgkzx_monitor"."wcnr_score"
        WHERE total_score > 0
    """

    total_persons = query_one(total_persons_sql).get("total", 0)
    high_risk = query_one(high_risk_sql).get("total", 0)
    month_cases = query_one(month_cases_sql).get("total", 0)
    extreme_risk = query_one(extreme_risk_sql).get("total", 0)
    avg_score = query_one(avg_score_sql).get("avg_score", 0)

    return {
        "total_persons": total_persons,
        "high_risk_count": high_risk,
        "extreme_risk_count": extreme_risk,
        "month_cases": month_cases,
        "avg_score": float(avg_score) if avg_score else 0,
    }
