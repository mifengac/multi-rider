SET search_path TO jcgkzx_monitor;

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

CREATE OR REPLACE FUNCTION pg_temp.derive_ssfjdm(id_no VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
AS $$
SELECT CASE
    WHEN CHAR_LENGTH(COALESCE(id_no, '')) < 6 THEN NULL
    WHEN LEFT(id_no, 2) <> '44' THEN NULL
    WHEN LEFT(id_no, 4) <> '4453' THEN NULL
    ELSE LEFT(id_no, 6) || '000000'
END;
$$;

CREATE OR REPLACE FUNCTION pg_temp.derive_ssfj_label(id_no VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
AS $$
SELECT CASE
    WHEN CHAR_LENGTH(COALESCE(id_no, '')) < 2 THEN NULL
    WHEN LEFT(id_no, 2) <> '44' THEN '外省'
    WHEN LEFT(id_no, 4) <> '4453' THEN '本省外市'
    ELSE NULL
END;
$$;

CREATE OR REPLACE FUNCTION pg_temp.derive_sspcsdm(id_no VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
AS $$
SELECT CASE
    WHEN CHAR_LENGTH(COALESCE(id_no, '')) < 8 THEN NULL
    WHEN LEFT(id_no, 4) = '4453' THEN LEFT(id_no, 8) || '0000'
    ELSE NULL
END;
$$;

DROP VIEW IF EXISTS pg_temp.zzjg_fj_dict;
CREATE TEMP VIEW zzjg_fj_dict AS
SELECT ssfjdm,
       MAX(ssfj) AS ssfj
FROM stdata.b_dic_zzjgdm
WHERE ssfjdm IS NOT NULL
GROUP BY ssfjdm;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    xb,
    csrq,
    source_type,
    ssfjdm,
    ssfj,
    sspcsdm,
    sspcs
)
WITH source_rows AS (
    SELECT
        raw.zjhm,
        raw.xm,
        raw.xb,
        raw.csrq,
        pg_temp.derive_ssfjdm(raw.zjhm) AS ssfjdm,
        pg_temp.derive_ssfj_label(raw.zjhm) AS ssfj,
        pg_temp.derive_sspcsdm(raw.zjhm) AS sspcsdm
    FROM (
        SELECT
            UPPER(NULLIF(TRIM(CAST(xyrxx_sfzh AS VARCHAR)), '')) AS zjhm,
            NULLIF(TRIM(CAST(xyrxx_xm AS VARCHAR)), '') AS xm,
            NULLIF(TRIM(CAST(xyrxx_xb AS VARCHAR)), '') AS xb,
            NULLIF(TRIM(CAST(xyrxx_csrq AS VARCHAR)), '') AS csrq
        FROM ywdata.zq_zfba_wcnr_xyr
        WHERE pg_temp.is_valid_mainland_id18(CAST(xyrxx_sfzh AS VARCHAR))
    ) raw
)
SELECT
    s.zjhm,
    s.xm,
    s.xb,
    s.csrq,
    'suspect' AS source_type,
    s.ssfjdm,
    COALESCE(s.ssfj, fj.ssfj, s.ssfjdm) AS ssfj,
    s.sspcsdm,
    NULL::VARCHAR AS sspcs
FROM source_rows s
LEFT JOIN zzjg_fj_dict fj ON fj.ssfjdm = s.ssfjdm
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    xb,
    csrq,
    source_type,
    ssfjdm,
    ssfj,
    sspcsdm,
    sspcs
)
WITH source_rows AS (
    SELECT
        raw.zjhm,
        raw.xm,
        raw.xb,
        raw.csrq,
        pg_temp.derive_ssfjdm(raw.zjhm) AS ssfjdm,
        pg_temp.derive_ssfj_label(raw.zjhm) AS ssfj,
        pg_temp.derive_sspcsdm(raw.zjhm) AS sspcsdm
    FROM (
        SELECT
            UPPER(NULLIF(TRIM(CAST(sfzhm AS VARCHAR)), '')) AS zjhm,
            NULLIF(TRIM(CAST(dsrxm AS VARCHAR)), '') AS xm,
            NULL::VARCHAR AS xb,
            NULL::VARCHAR AS csrq
        FROM ywdata.b_per_qswcnrbczj
        WHERE pg_temp.is_valid_mainland_id18(CAST(sfzhm AS VARCHAR))
    ) raw
)
SELECT
    s.zjhm,
    s.xm,
    s.xb,
    s.csrq,
    'bczj' AS source_type,
    s.ssfjdm,
    COALESCE(s.ssfj, fj.ssfj, s.ssfjdm) AS ssfj,
    s.sspcsdm,
    NULL::VARCHAR AS sspcs
FROM source_rows s
LEFT JOIN zzjg_fj_dict fj ON fj.ssfjdm = s.ssfjdm
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    xb,
    csrq,
    source_type,
    ssfjdm,
    ssfj,
    sspcsdm,
    sspcs
)
WITH source_rows AS (
    SELECT
        raw.zjhm,
        raw.xm,
        raw.xb,
        raw.csrq,
        pg_temp.derive_ssfjdm(raw.zjhm) AS ssfjdm,
        pg_temp.derive_ssfj_label(raw.zjhm) AS ssfj,
        pg_temp.derive_sspcsdm(raw.zjhm) AS sspcsdm
    FROM (
        SELECT
            UPPER(NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '')) AS zjhm,
            NULLIF(TRIM(CAST(xm AS VARCHAR)), '') AS xm,
            NULL::VARCHAR AS xb,
            NULL::VARCHAR AS csrq
        FROM ywdata.b_per_qsyzjszawcnr
        WHERE pg_temp.is_valid_mainland_id18(CAST(zjhm AS VARCHAR))
    ) raw
)
SELECT
    s.zjhm,
    s.xm,
    s.xb,
    s.csrq,
    'correction' AS source_type,
    s.ssfjdm,
    COALESCE(s.ssfj, fj.ssfj, s.ssfjdm) AS ssfj,
    s.sspcsdm,
    NULL::VARCHAR AS sspcs
FROM source_rows s
LEFT JOIN zzjg_fj_dict fj ON fj.ssfjdm = s.ssfjdm
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    xb,
    csrq,
    source_type,
    ssfjdm,
    ssfj,
    sspcsdm,
    sspcs
)
WITH source_rows AS (
    SELECT
        raw.zjhm,
        raw.xm,
        raw.xb,
        raw.csrq,
        pg_temp.derive_ssfjdm(raw.zjhm) AS ssfjdm,
        pg_temp.derive_ssfj_label(raw.zjhm) AS ssfj,
        pg_temp.derive_sspcsdm(raw.zjhm) AS sspcsdm
    FROM (
        SELECT
            UPPER(NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '')) AS zjhm,
            NULLIF(TRIM(CAST(xm AS VARCHAR)), '') AS xm,
            NULL::VARCHAR AS xb,
            NULL::VARCHAR AS csrq
        FROM ywdata.b_per_qscxwcnr
        WHERE pg_temp.is_valid_mainland_id18(CAST(zjhm AS VARCHAR))
    ) raw
)
SELECT
    s.zjhm,
    s.xm,
    s.xb,
    s.csrq,
    'dropout' AS source_type,
    s.ssfjdm,
    COALESCE(s.ssfj, fj.ssfj, s.ssfjdm) AS ssfj,
    s.sspcsdm,
    NULL::VARCHAR AS sspcs
FROM source_rows s
LEFT JOIN zzjg_fj_dict fj ON fj.ssfjdm = s.ssfjdm
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    xb,
    csrq,
    source_type,
    ssfjdm,
    ssfj,
    sspcsdm,
    sspcs
)
WITH source_rows AS (
    SELECT
        raw.zjhm,
        raw.xm,
        raw.xb,
        raw.csrq,
        pg_temp.derive_ssfjdm(raw.zjhm) AS ssfjdm,
        pg_temp.derive_ssfj_label(raw.zjhm) AS ssfj,
        pg_temp.derive_sspcsdm(raw.zjhm) AS sspcsdm
    FROM (
        SELECT
            UPPER(NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '')) AS zjhm,
            NULLIF(TRIM(CAST(xm AS VARCHAR)), '') AS xm,
            NULL::VARCHAR AS xb,
            NULL::VARCHAR AS csrq
        FROM ywdata.b_per_qskjwcnr
        WHERE pg_temp.is_valid_mainland_id18(CAST(zjhm AS VARCHAR))
    ) raw
)
SELECT
    s.zjhm,
    s.xm,
    s.xb,
    s.csrq,
    'truant' AS source_type,
    s.ssfjdm,
    COALESCE(s.ssfj, fj.ssfj, s.ssfjdm) AS ssfj,
    s.sspcsdm,
    NULL::VARCHAR AS sspcs
FROM source_rows s
LEFT JOIN zzjg_fj_dict fj ON fj.ssfjdm = s.ssfjdm
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    xb,
    csrq,
    source_type,
    ssfjdm,
    ssfj,
    sspcsdm,
    sspcs
)
WITH source_rows AS (
    SELECT
        raw.zjhm,
        raw.xm,
        raw.xb,
        raw.csrq,
        pg_temp.derive_ssfjdm(raw.zjhm) AS ssfjdm,
        pg_temp.derive_ssfj_label(raw.zjhm) AS ssfj,
        pg_temp.derive_sspcsdm(raw.zjhm) AS sspcsdm
    FROM (
        SELECT
            UPPER(NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '')) AS zjhm,
            NULLIF(TRIM(CAST(xm AS VARCHAR)), '') AS xm,
            NULL::VARCHAR AS xb,
            NULL::VARCHAR AS csrq
        FROM ywdata.b_per_qslswcnr
        WHERE pg_temp.is_valid_mainland_id18(CAST(zjhm AS VARCHAR))
    ) raw
)
SELECT
    s.zjhm,
    s.xm,
    s.xb,
    s.csrq,
    'lost' AS source_type,
    s.ssfjdm,
    COALESCE(s.ssfj, fj.ssfj, s.ssfjdm) AS ssfj,
    s.sspcsdm,
    NULL::VARCHAR AS sspcs
FROM source_rows s
LEFT JOIN zzjg_fj_dict fj ON fj.ssfjdm = s.ssfjdm
ON CONFLICT (zjhm) DO NOTHING;
