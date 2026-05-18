SET search_path TO jcgkzx_monitor;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    xb,
    csrq,
    source_type
)
SELECT
    NULLIF(TRIM(CAST(xyrxx_sfzh AS VARCHAR)), '') AS zjhm,
    NULLIF(TRIM(CAST(xyrxx_xm AS VARCHAR)), '') AS xm,
    NULLIF(TRIM(CAST(xyrxx_xb AS VARCHAR)), '') AS xb,
    NULLIF(TRIM(CAST(xyrxx_csrq AS VARCHAR)), '') AS csrq,
    'suspect' AS source_type
FROM ywdata.zq_zfba_wcnr_xyr
WHERE NULLIF(TRIM(CAST(xyrxx_sfzh AS VARCHAR)), '') IS NOT NULL
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    source_type
)
SELECT
    NULLIF(TRIM(CAST(sfzhm AS VARCHAR)), '') AS zjhm,
    NULLIF(TRIM(CAST(dsrxm AS VARCHAR)), '') AS xm,
    'bczj' AS source_type
FROM ywdata.b_per_qswcnrbczj
WHERE NULLIF(TRIM(CAST(sfzhm AS VARCHAR)), '') IS NOT NULL
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    source_type
)
SELECT
    NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '') AS zjhm,
    NULLIF(TRIM(CAST(xm AS VARCHAR)), '') AS xm,
    'correction' AS source_type
FROM ywdata.b_per_qsyzjszawcnr
WHERE NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '') IS NOT NULL
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    source_type
)
SELECT
    NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '') AS zjhm,
    NULLIF(TRIM(CAST(xm AS VARCHAR)), '') AS xm,
    'dropout' AS source_type
FROM ywdata.b_per_qscxwcnr
WHERE NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '') IS NOT NULL
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    source_type
)
SELECT
    NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '') AS zjhm,
    NULLIF(TRIM(CAST(xm AS VARCHAR)), '') AS xm,
    'truant' AS source_type
FROM ywdata.b_per_qskjwcnr
WHERE NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '') IS NOT NULL
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO wcnr_target_pool (
    zjhm,
    xm,
    source_type
)
SELECT
    NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '') AS zjhm,
    NULLIF(TRIM(CAST(xm AS VARCHAR)), '') AS xm,
    'lost' AS source_type
FROM ywdata.b_per_qslswcnr
WHERE NULLIF(TRIM(CAST(zjhm AS VARCHAR)), '') IS NOT NULL
ON CONFLICT (zjhm) DO NOTHING;
