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


def _normalize_area_level(level: str | None) -> str:
    return "sspcs" if str(level or "").strip().lower() == "sspcs" else "ssfj"


def _query_target_area_distribution(level: str, parent_code: str | None, limit: int, has_dict: bool) -> list[dict]:
    if level == "sspcs":
        code_col = "sspcsdm"
        name_col = "sspcs"
        dict_code_col = "sspcsdm"
        dict_name_col = "sspcs"
        parent_select = 'p.ssfjdm AS parent_code'
        parent_filter = 'AND (%(parent_code)s IS NULL OR p.ssfjdm = %(parent_code)s)'
    else:
        code_col = "ssfjdm"
        name_col = "ssfj"
        dict_code_col = "ssfjdm"
        dict_name_col = "ssfj"
        parent_select = 'NULL::VARCHAR AS parent_code'
        parent_filter = ''

    dict_join = ""
    label_expr = f"COALESCE(NULLIF(BTRIM(COALESCE(p.{name_col}, '')), ''), p.{code_col})"
    if has_dict:
        dict_join = f"""
        LEFT JOIN (
            SELECT {dict_code_col} AS code,
                   MAX({dict_name_col}) AS name
            FROM \"stdata\".\"b_dic_zzjgdm\"
            WHERE {dict_code_col} IS NOT NULL
            GROUP BY {dict_code_col}
        ) d ON d.code = p.{code_col}
        """
        label_expr = f"COALESCE(NULLIF(BTRIM(COALESCE(p.{name_col}, '')), ''), d.name, p.{code_col})"

    sql = f"""
        SELECT p.{code_col} AS code,
               {parent_select},
               {label_expr} AS label,
               COUNT(*) AS value
        FROM \"jcgkzx_monitor\".\"wcnr_score\" s
        JOIN \"jcgkzx_monitor\".\"wcnr_target_pool\" p ON p.zjhm = s.zjhm
        {dict_join}
        WHERE s.total_score >= 60
          AND NULLIF(BTRIM(COALESCE(p.{code_col}, '')), '') IS NOT NULL
          {parent_filter}
        GROUP BY 1, 2, 3
        ORDER BY value DESC, label
        LIMIT %(limit)s
    """
    return query_all(sql, {"parent_code": parent_code, "limit": limit})


def _query_fallback_area_distribution(level: str, parent_code: str | None, limit: int, has_dict: bool) -> list[dict]:
    if level == "sspcs":
        code_expr = "LEFT(s.zjhm, 8) || '0000'"
        parent_expr = "LEFT(s.zjhm, 6) || '000000'"
        parent_select = f"{parent_expr} AS parent_code"
        id_filter = "LENGTH(s.zjhm) >= 8 AND LEFT(s.zjhm, 8) ~ '^[0-9]{8}$'"
        parent_filter = f"AND (%(parent_code)s IS NULL OR {parent_expr} = %(parent_code)s)"
        dict_code_col = "sspcsdm"
        dict_name_col = "sspcs"
    else:
        code_expr = "LEFT(s.zjhm, 6) || '000000'"
        parent_select = "NULL::VARCHAR AS parent_code"
        id_filter = "LENGTH(s.zjhm) >= 6 AND LEFT(s.zjhm, 6) ~ '^[0-9]{6}$'"
        parent_filter = ""
        dict_code_col = "ssfjdm"
        dict_name_col = "ssfj"

    dict_join = ""
    label_expr = code_expr
    if has_dict:
        dict_join = f"""
        LEFT JOIN (
            SELECT {dict_code_col} AS code,
                   MAX({dict_name_col}) AS name
            FROM \"stdata\".\"b_dic_zzjgdm\"
            WHERE {dict_code_col} IS NOT NULL
            GROUP BY {dict_code_col}
        ) d ON d.code = {code_expr}
        """
        label_expr = f"COALESCE(d.name, {code_expr})"

    sql = f"""
        SELECT {code_expr} AS code,
               {parent_select},
               {label_expr} AS label,
               COUNT(*) AS value
        FROM \"jcgkzx_monitor\".\"wcnr_score\" s
        {dict_join}
        WHERE s.total_score >= 60
          AND {id_filter}
          {parent_filter}
        GROUP BY 1, 2, 3
        ORDER BY value DESC, label
        LIMIT %(limit)s
    """
    return query_all(sql, {"parent_code": parent_code, "limit": limit})


def get_area_distribution(
    metric: str = "risk_count",
    level: str = "ssfj",
    parent_code: str | None = None,
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

    normalized_level = _normalize_area_level(level)
    scoped_parent_code = parent_code if normalized_level == "sspcs" else None
    has_dict = _table_exists("stdata", "b_dic_zzjgdm")

    rows = _query_target_area_distribution(normalized_level, scoped_parent_code, limit, has_dict)
    if rows:
        return rows
    logger.info("Area distribution fallback triggered, primary returned %d rows", len(rows))
    return _query_fallback_area_distribution(normalized_level, scoped_parent_code, limit, has_dict)


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
