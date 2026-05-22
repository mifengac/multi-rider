/* 0) 复刻 etl_init_target_pool.sql 的身份证校验函数 */
CREATE OR REPLACE FUNCTION pg_temp.is_valid_mainland_id18(id_no VARCHAR)
RETURNS BOOLEAN
LANGUAGE SQL
AS $$
WITH normalized AS (
    SELECT UPPER(BTRIM(COALESCE(id_no, ''))) AS id_no
),
formatted AS (
    SELECT id_no
    FROM normalized
    WHERE id_no IS NOT NULL
      AND CHAR_LENGTH(id_no) = 18
      AND id_no ~ '^[1-9][0-9]{5}(18|19|20)[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])[0-9]{3}[0-9X]$'
      AND TO_CHAR(TO_DATE(SUBSTRING(id_no, 7, 8), 'YYYYMMDD'), 'YYYYMMDD') = SUBSTRING(id_no, 7, 8)
),
checked AS (
    SELECT
        id_no,
        CASE (
            (
                SUBSTRING(id_no, 1, 1)::INTEGER * 7 +
                SUBSTRING(id_no, 2, 1)::INTEGER * 9 +
                SUBSTRING(id_no, 3, 1)::INTEGER * 10 +
                SUBSTRING(id_no, 4, 1)::INTEGER * 5 +
                SUBSTRING(id_no, 5, 1)::INTEGER * 8 +
                SUBSTRING(id_no, 6, 1)::INTEGER * 4 +
                SUBSTRING(id_no, 7, 1)::INTEGER * 2 +
                SUBSTRING(id_no, 8, 1)::INTEGER * 1 +
                SUBSTRING(id_no, 9, 1)::INTEGER * 6 +
                SUBSTRING(id_no, 10, 1)::INTEGER * 3 +
                SUBSTRING(id_no, 11, 1)::INTEGER * 7 +
                SUBSTRING(id_no, 12, 1)::INTEGER * 9 +
                SUBSTRING(id_no, 13, 1)::INTEGER * 10 +
                SUBSTRING(id_no, 14, 1)::INTEGER * 5 +
                SUBSTRING(id_no, 15, 1)::INTEGER * 8 +
                SUBSTRING(id_no, 16, 1)::INTEGER * 4 +
                SUBSTRING(id_no, 17, 1)::INTEGER * 2
            ) % 11
        )
            WHEN 0 THEN '1'
            WHEN 1 THEN '0'
            WHEN 2 THEN 'X'
            WHEN 3 THEN '9'
            WHEN 4 THEN '8'
            WHEN 5 THEN '7'
            WHEN 6 THEN '6'
            WHEN 7 THEN '5'
            WHEN 8 THEN '4'
            WHEN 9 THEN '3'
            ELSE '2'
        END AS expected_check_code
    FROM formatted
)
SELECT EXISTS (
    SELECT 1
    FROM checked
    WHERE expected_check_code = RIGHT(id_no, 1)
);
$$;

/* 1) 按 ETL 脚本的真实来源顺序做统一归一化 */
DROP VIEW IF EXISTS pg_temp.wcnr_source_union;
CREATE TEMP VIEW wcnr_source_union AS
SELECT
    1 AS source_order,
    'ywdata.zq_zfba_wcnr_xyr' AS source_name,
    'suspect' AS source_type,
    UPPER(NULLIF(BTRIM(CAST(xyrxx_sfzh AS VARCHAR)), '')) AS zjhm
FROM ywdata.zq_zfba_wcnr_xyr

UNION ALL
SELECT
    2 AS source_order,
    'ywdata.b_per_qswcnrbczj' AS source_name,
    'bczj' AS source_type,
    UPPER(NULLIF(BTRIM(CAST(sfzhm AS VARCHAR)), '')) AS zjhm
FROM ywdata.b_per_qswcnrbczj

UNION ALL
SELECT
    3 AS source_order,
    'ywdata.b_per_qsyzjszawcnr' AS source_name,
    'correction' AS source_type,
    UPPER(NULLIF(BTRIM(CAST(zjhm AS VARCHAR)), '')) AS zjhm
FROM ywdata.b_per_qsyzjszawcnr

UNION ALL
SELECT
    4 AS source_order,
    'ywdata.b_per_qscxwcnr' AS source_name,
    'dropout' AS source_type,
    UPPER(NULLIF(BTRIM(CAST(zjhm AS VARCHAR)), '')) AS zjhm
FROM ywdata.b_per_qscxwcnr

UNION ALL
SELECT
    5 AS source_order,
    'ywdata.b_per_qskjwcnr' AS source_name,
    'truant' AS source_type,
    UPPER(NULLIF(BTRIM(CAST(zjhm AS VARCHAR)), '')) AS zjhm
FROM ywdata.b_per_qskjwcnr

UNION ALL
SELECT
    6 AS source_order,
    'ywdata.b_per_qslswcnr' AS source_name,
    'lost' AS source_type,
    UPPER(NULLIF(BTRIM(CAST(zjhm AS VARCHAR)), '')) AS zjhm
FROM ywdata.b_per_qslswcnr;

/* 2) 给每条数据打上“卡在哪一步”的标签 */
DROP VIEW IF EXISTS pg_temp.wcnr_source_stage;
CREATE TEMP VIEW wcnr_source_stage AS
SELECT
    source_order,
    source_name,
    source_type,
    zjhm,
    CASE WHEN zjhm IS NOT NULL THEN 1 ELSE 0 END AS non_blank_id,
    CASE WHEN zjhm IS NOT NULL AND CHAR_LENGTH(zjhm) = 18 THEN 1 ELSE 0 END AS len18_ok,
    CASE
        WHEN zjhm IS NOT NULL
         AND zjhm ~ '^[1-9][0-9]{5}(18|19|20)[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])[0-9]{3}[0-9X]$'
        THEN 1 ELSE 0
    END AS regex_ok,
    CASE
        WHEN zjhm IS NOT NULL
         AND zjhm ~ '^[1-9][0-9]{5}(18|19|20)[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])[0-9]{3}[0-9X]$'
         AND TO_CHAR(TO_DATE(SUBSTRING(zjhm, 7, 8), 'YYYYMMDD'), 'YYYYMMDD') = SUBSTRING(zjhm, 7, 8)
        THEN 1 ELSE 0
    END AS birthdate_ok,
    CASE WHEN pg_temp.is_valid_mainland_id18(zjhm) THEN 1 ELSE 0 END AS valid_id,
    CASE
        WHEN zjhm IS NULL THEN 'blank_or_whitespace'
        WHEN CHAR_LENGTH(zjhm) <> 18 THEN 'len_not_18'
        WHEN zjhm !~ '^[1-9][0-9]{5}(18|19|20)[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])[0-9]{3}[0-9X]$' THEN 'regex_fail'
        WHEN TO_CHAR(TO_DATE(SUBSTRING(zjhm, 7, 8), 'YYYYMMDD'), 'YYYYMMDD') <> SUBSTRING(zjhm, 7, 8) THEN 'birthdate_invalid'
        WHEN NOT pg_temp.is_valid_mainland_id18(zjhm) THEN 'check_code_fail'
        ELSE 'valid'
    END AS fail_reason
FROM wcnr_source_union;

/* 3) 每个来源表在 ETL 各阶段到底剩多少 */
WITH valid_distinct AS (
    SELECT
        source_order,
        source_name,
        source_type,
        zjhm
    FROM wcnr_source_stage
    WHERE valid_id = 1
    GROUP BY source_order, source_name, source_type, zjhm
),
first_source AS (
    SELECT
        zjhm,
        MIN(source_order) AS first_source_order
    FROM valid_distinct
    GROUP BY zjhm
),
source_contrib AS (
    SELECT
        v.source_order,
        v.source_name,
        v.source_type,
        COUNT(*) AS inserted_rows_in_etl_order
    FROM valid_distinct v
    JOIN first_source f
      ON f.zjhm = v.zjhm
     AND f.first_source_order = v.source_order
    GROUP BY v.source_order, v.source_name, v.source_type
)
SELECT
    s.source_order,
    s.source_name,
    s.source_type,
    COUNT(*) AS raw_rows,
    SUM(s.non_blank_id) AS non_blank_id_rows,
    SUM(s.len18_ok) AS len18_rows,
    SUM(s.regex_ok) AS regex_rows,
    SUM(s.birthdate_ok) AS birthdate_rows,
    SUM(s.valid_id) AS valid_id_rows,
    COUNT(DISTINCT CASE WHEN s.valid_id = 1 THEN s.zjhm END) AS distinct_valid_id_rows,
    COALESCE(c.inserted_rows_in_etl_order, 0) AS inserted_rows_in_etl_order,
    COUNT(DISTINCT CASE WHEN s.valid_id = 1 THEN s.zjhm END) - COALESCE(c.inserted_rows_in_etl_order, 0)
        AS duplicate_valid_ids_swallowed_by_previous_sources
FROM wcnr_source_stage s
LEFT JOIN source_contrib c
  ON c.source_order = s.source_order
 AND c.source_name = s.source_name
 AND c.source_type = s.source_type
GROUP BY
    s.source_order,
    s.source_name,
    s.source_type,
    c.inserted_rows_in_etl_order
ORDER BY s.source_order;

/* 4) 六表合并后的理论人数 vs 当前 target_pool 实际人数 */
WITH valid_union AS (
    SELECT DISTINCT zjhm
    FROM wcnr_source_stage
    WHERE valid_id = 1
)
SELECT
    (SELECT COUNT(*) FROM valid_union) AS union_distinct_valid_ids,
    (SELECT COUNT(*) FROM jcgkzx_monitor.wcnr_target_pool) AS current_target_pool_rows,
    (SELECT COUNT(*) FROM (
        SELECT zjhm FROM valid_union
        EXCEPT
        SELECT zjhm FROM jcgkzx_monitor.wcnr_target_pool
    ) t) AS valid_ids_missing_from_target_pool,
    (SELECT COUNT(*) FROM (
        SELECT zjhm FROM jcgkzx_monitor.wcnr_target_pool
        EXCEPT
        SELECT zjhm FROM valid_union
    ) t) AS extra_ids_in_target_pool;

/* 5) 看每个来源表主要死在哪一步 */
SELECT
    source_order,
    source_name,
    fail_reason,
    COUNT(*) AS rows
FROM wcnr_source_stage
GROUP BY source_order, source_name, fail_reason
ORDER BY source_order, fail_reason;