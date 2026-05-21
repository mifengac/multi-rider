from shared.age_filter import build_age_exists_clause, get_age_filter_threshold
from shared.config.config import logger
from shared.db.kingbase import query_all, query_one


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
        logger.warning("Distribution table probe failed for %s.%s: %s", schema, table, exc)
        return False


def _case_type_sql(age_clause: str) -> str:
    return f"""
        SELECT a."ajxx_ay" AS label,
               COUNT(DISTINCT a."ajxx_ajbh") AS value
        FROM "ywdata"."zq_zfba_ajxx" a
        WHERE a."ajxx_ay" IS NOT NULL
          {age_clause}
        GROUP BY a."ajxx_ay"
        ORDER BY value DESC
        LIMIT 10
    """


def get_case_type_distribution() -> dict:
    if get_age_filter_threshold() <= 0:
        return {"items": query_all(_case_type_sql("")), "degraded": False}

    rows = query_all(_case_type_sql(build_age_exists_clause("a", "x")))
    if rows:
        return {"items": rows, "degraded": False}
    return {"items": query_all(_case_type_sql("")), "degraded": True}


def get_risk_level_distribution() -> list[dict]:
    sql = """
        SELECT risk_level AS label, COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_score"
        WHERE risk_level IS NOT NULL
        GROUP BY risk_level
        ORDER BY value DESC
    """
    return query_all(sql)


def get_area_distribution(
    metric: str = "risk_count",
    limit: int = 10,
) -> list[dict]:
    if metric == "case_count":
        sql = """
            SELECT a."ajxx_cbdw_mc" AS label,
                   COUNT(DISTINCT a."ajxx_ajbh") AS value
            FROM "ywdata"."zq_zfba_ajxx" a
            WHERE a."ajxx_cbdw_mc" IS NOT NULL
            GROUP BY a."ajxx_cbdw_mc"
            ORDER BY value DESC
            LIMIT %(limit)s
        """
        return query_all(sql, {"limit": limit})

    sql = """
        SELECT
            p.ssfj AS label,
            COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_score" s
        JOIN "jcgkzx_monitor"."wcnr_target_pool" p ON p.zjhm = s.zjhm
        WHERE s.total_score >= 60
          AND p.ssfj IS NOT NULL
          AND BTRIM(p.ssfj) <> ''
        GROUP BY p.ssfj
        ORDER BY value DESC, label
        LIMIT %(limit)s
    """
    return query_all(sql, {"limit": limit})


def get_school_ranking(metric: str = "risk_count") -> list[dict]:
    if metric == "case_count":
        sql = """
            SELECT sfz."yxx" AS label,
                   COUNT(DISTINCT a."ajxx_ajbh") AS value
            FROM "ywdata"."zq_zfba_ajxx" a
            JOIN "ywdata"."zq_zfba_xyrxx" x
              ON x."ajxx_join_ajxx_ajbh" = a."ajxx_ajbh"
            JOIN "ywdata"."zq_zfba_wcnr_sfzxx" sfz
              ON sfz."sfzhm" = x."xyrxx_sfzh"
            WHERE sfz."yxx" IS NOT NULL
            GROUP BY sfz."yxx"
            ORDER BY value DESC
            LIMIT 10
        """
        return query_all(sql)

    sql = """
        SELECT sfz."yxx" AS label,
               COUNT(DISTINCT s.zjhm) AS value
        FROM "jcgkzx_monitor"."wcnr_score" s
        JOIN "ywdata"."zq_zfba_wcnr_sfzxx" sfz
          ON sfz."sfzhm" = s.zjhm
        WHERE s.total_score >= 60
          AND sfz."yxx" IS NOT NULL
        GROUP BY sfz."yxx"
        ORDER BY value DESC
        LIMIT 10
    """
    return query_all(sql)


def get_age_distribution() -> list[dict]:
    sql = """
        SELECT
            CASE
                WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, csrq::DATE)) < 14 THEN '14岁以下'
                WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, csrq::DATE)) < 16 THEN '14-16岁'
                ELSE '16-18岁'
            END AS label,
            COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        WHERE csrq IS NOT NULL AND LENGTH(csrq) >= 8
        GROUP BY label
        ORDER BY label
    """
    rows = query_all(sql)
    if rows:
        return rows
    logger.info("Age distribution fallback triggered, primary returned %d rows", len(rows))

    fallback_sql = """
        SELECT
            CASE
                WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, TO_DATE(SUBSTR(zjhm, 7, 8), 'YYYYMMDD'))) < 14 THEN '14岁以下'
                WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, TO_DATE(SUBSTR(zjhm, 7, 8), 'YYYYMMDD'))) < 16 THEN '14-16岁'
                ELSE '16-18岁'
            END AS label,
            COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        WHERE LENGTH(zjhm) >= 14
          AND SUBSTR(zjhm, 7, 8) ~ '^[0-9]{8}$'
        GROUP BY label
        ORDER BY label
    """
    return query_all(fallback_sql)


def get_gender_distribution() -> list[dict]:
    sql = """
        SELECT
            CASE WHEN xb = '男' THEN '男' WHEN xb = '女' THEN '女' ELSE '未知' END AS label,
            COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        GROUP BY label
    """
    return query_all(sql)


def get_source_distribution() -> list[dict]:
    sql = """
        SELECT source_type AS label, COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        GROUP BY source_type
        ORDER BY value DESC
    """
    return query_all(sql)
