from shared.db.kingbase import query_all


def get_case_type_distribution() -> list[dict]:
    sql = """
        SELECT ajxx_ay AS label, COUNT(*) AS value
        FROM "ywdata"."zq_zfba_wcnr_ajxx"
        WHERE ajxx_ay IS NOT NULL
        GROUP BY ajxx_ay
        ORDER BY value DESC
        LIMIT 10
    """
    return query_all(sql)


def get_risk_level_distribution() -> list[dict]:
    sql = """
        SELECT risk_level AS label, COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_score"
        WHERE risk_level IS NOT NULL
        GROUP BY risk_level
        ORDER BY value DESC
    """
    return query_all(sql)


def get_area_distribution() -> list[dict]:
    sql = """
        SELECT p.ssfj AS label, COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_score" s
        JOIN "jcgkzx_monitor"."wcnr_target_pool" p ON p.zjhm = s.zjhm
        WHERE s.total_score >= 60 AND p.ssfj IS NOT NULL
        GROUP BY p.ssfj
        ORDER BY value DESC
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
    return query_all(sql)


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
