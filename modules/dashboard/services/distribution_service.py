from shared.db.kingbase import query_all


def get_case_type_distribution() -> list[dict]:
    sql = """
        SELECT a."ajxx_ay" AS label,
               COUNT(DISTINCT a."ajxx_ajbh") AS value
        FROM "ywdata"."zq_zfba_ajxx" a
        WHERE a."ajxx_ay" IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM "ywdata"."zq_zfba_xyrxx" x
              WHERE x."ajxx_join_ajxx_ajbh" = a."ajxx_ajbh"
                AND LENGTH(x."xyrxx_sfzh") = 18
                AND DATE_PART('year',
                      AGE(COALESCE(a."ajxx_fasj"::date, CURRENT_DATE),
                          TO_DATE(SUBSTR(x."xyrxx_sfzh", 7, 8), 'YYYYMMDD'))
                    ) < 18
          )
        GROUP BY a."ajxx_ay"
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


def get_area_distribution(metric: str = "risk_count") -> list[dict]:
    if metric == "case_count":
        sql = """
            SELECT a."ajxx_cbdw_mc" AS label,
                   COUNT(DISTINCT a."ajxx_ajbh") AS value
            FROM "ywdata"."zq_zfba_ajxx" a
            WHERE a."ajxx_cbdw_mc" IS NOT NULL
            GROUP BY a."ajxx_cbdw_mc"
            ORDER BY value DESC
            LIMIT 10
        """
        return query_all(sql)

    sql = """
        SELECT p.ssfj AS label, COUNT(*) AS value
        FROM "jcgkzx_monitor"."wcnr_score" s
        JOIN "jcgkzx_monitor"."wcnr_target_pool" p ON p.zjhm = s.zjhm
        WHERE s.total_score >= 60 AND p.ssfj IS NOT NULL
        GROUP BY p.ssfj
        ORDER BY value DESC
    """
    return query_all(sql)


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
