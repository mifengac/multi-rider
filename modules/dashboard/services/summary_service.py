from shared.config.config import logger
from shared.db.kingbase import query_all, query_one
from shared.age_filter import build_age_exists_clause, get_age_filter_threshold


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
        logger.warning("Summary table probe failed for %s.%s: %s", schema, table, exc)
        return False


def _table_columns(schema: str, table: str) -> set[str]:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %(s)s
          AND table_name = %(t)s
    """
    try:
        return {row.get("column_name") for row in query_all(sql, {"s": schema, "t": table}) if row.get("column_name")}
    except Exception as exc:
        logger.warning("Summary column probe failed for %s.%s: %s", schema, table, exc)
        return set()


def _change_pct(current, previous):
    if previous in (None, 0):
        return None
    return round((float(current or 0) - float(previous)) * 100.0 / float(previous), 1)


def _case_count_sql(where_clause: str, age_clause: str) -> str:
    return f"""
        SELECT COUNT(DISTINCT a."ajxx_ajbh") AS total
        FROM "ywdata"."zq_zfba_ajxx" a
        WHERE {where_clause}
          {age_clause}
    """


def _query_case_count_with_degrade(where_clause: str) -> tuple[int, bool]:
    if get_age_filter_threshold() <= 0:
        row = query_one(_case_count_sql(where_clause, ""))
        return int(row.get("total") or 0), False

    row = query_one(_case_count_sql(where_clause, build_age_exists_clause("a", "x")))
    total = int(row.get("total") or 0)
    if total:
        return total, False

    logger.info("Summary case count fallback triggered, primary returned %d rows", total)
    fallback = query_one(_case_count_sql(where_clause, ""))
    return int(fallback.get("total") or 0), True


def get_summary() -> dict:
    total_persons_sql = """
        SELECT COUNT(*) AS total FROM "jcgkzx_monitor"."wcnr_target_pool"
    """
    high_risk_sql = """
        SELECT COUNT(*) AS total FROM "jcgkzx_monitor"."wcnr_score"
        WHERE total_score >= 60
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
    month_cases, month_cases_degraded = _query_case_count_with_degrade(
        "a.\"ajxx_fasj\" >= DATE_TRUNC('month', CURRENT_DATE)"
    )
    month_cases_prev, month_cases_prev_degraded = _query_case_count_with_degrade(
        "a.\"ajxx_fasj\" >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'\n"
        "          AND a.\"ajxx_fasj\" < DATE_TRUNC('month', CURRENT_DATE)"
    )
    extreme_risk = query_one(extreme_risk_sql).get("total", 0)
    avg_score = query_one(avg_score_sql).get("avg_score", 0)

    result = {
        "total_persons": total_persons,
        "high_risk_count": high_risk,
        "extreme_risk_count": extreme_risk,
        "month_cases": month_cases,
        "month_cases_prev": month_cases_prev,
        "month_cases_change_pct": _change_pct(month_cases, month_cases_prev),
        "month_cases_degraded": month_cases_degraded or month_cases_prev_degraded,
        "avg_score": float(avg_score) if avg_score else 0,
    }

    if _table_exists("jcgkzx_monitor", "wcnr_score_history"):
        high_risk_prev_sql = """
            WITH latest AS (
                SELECT zjhm, MAX(calc_time) AS calc_time
                FROM "jcgkzx_monitor"."wcnr_score_history"
                WHERE calc_time >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
                  AND calc_time < DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY zjhm
            )
            SELECT COUNT(*) AS total
            FROM latest l
            JOIN "jcgkzx_monitor"."wcnr_score_history" h
              ON h.zjhm = l.zjhm
             AND h.calc_time = l.calc_time
            WHERE h.total_score >= 60
        """
        high_risk_prev = query_one(high_risk_prev_sql).get("total", 0)
        result["high_risk_count_prev"] = high_risk_prev
        result["high_risk_count_change_pct"] = _change_pct(high_risk, high_risk_prev)
    else:
        result["high_risk_count_prev"] = None
        result["high_risk_count_change_pct"] = None

    if _table_exists("jcgkzx_monitor", "wcnr_visit"):
        visit_fields = _table_columns("jcgkzx_monitor", "wcnr_visit")
        time_col = next((col for col in ("visit_time", "visit_date", "create_time", "created_at") if col in visit_fields), None)
        pass_col = next((col for col in ("is_pass", "pass_status", "status", "result") if col in visit_fields), None)
        if time_col and pass_col:
            if pass_col == "is_pass":
                pass_expr = '"is_pass" = TRUE'
            else:
                pass_expr = f'"{pass_col}" IN (\'达标\', \'合格\', \'pass\', \'passed\')'
            visit_sql = f"""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN {pass_expr} THEN 1 ELSE 0 END) AS passed
                FROM "jcgkzx_monitor"."wcnr_visit"
                WHERE "{time_col}" >= DATE_TRUNC('month', CURRENT_DATE)
            """
            try:
                visit = query_one(visit_sql)
                visit_total = int(visit.get("total") or 0)
                visit_passed = int(visit.get("passed") or 0)
                result["visit_total_month"] = visit_total
                result["visit_pass_rate"] = round(visit_passed * 100.0 / visit_total, 1) if visit_total else None
            except Exception as exc:
                logger.warning("Visit summary skipped: %s", exc)

    return result
