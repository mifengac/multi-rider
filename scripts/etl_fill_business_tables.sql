SET search_path TO jcgkzx_monitor;

TRUNCATE TABLE jcgkzx_monitor.wcnr_czrk;
TRUNCATE TABLE jcgkzx_monitor.wcnr_rk_zp;
TRUNCATE TABLE jcgkzx_monitor.wcnr_ly_checkin;
TRUNCATE TABLE jcgkzx_monitor.wcnr_ryrl_gj;

INSERT INTO jcgkzx_monitor.wcnr_czrk (
    zjhm,
    xm,
    xb,
    mz,
    csrq,
    hjdz,
    xzdxz,
    whcd,
    fqxm,
    fqzjhm,
    mqxm,
    mqzjhm,
    lxdh
)
SELECT
    UPPER(NULLIF(BTRIM(CAST(s.gmsfhm AS VARCHAR)), '')) AS zjhm,
    NULLIF(BTRIM(CAST(s.xm AS VARCHAR)), '') AS xm,
    NULLIF(BTRIM(CAST(s.xb AS VARCHAR)), '') AS xb,
    NULLIF(BTRIM(CAST(s.mz AS VARCHAR)), '') AS mz,
    CASE
        WHEN s.csrq IS NOT NULL THEN TO_CHAR(s.csrq, 'YYYY-MM-DD')
        ELSE NULL
    END AS csrq,
    NULLIF(BTRIM(CAST(s.dz AS VARCHAR)), '') AS hjdz,
    COALESCE(
        NULLIF(BTRIM(CAST(s.xjzdz AS VARCHAR)), ''),
        NULLIF(BTRIM(CAST(s.sjjzdz AS VARCHAR)), '')
    ) AS xzdxz,
    NULLIF(BTRIM(CAST(s.whcd AS VARCHAR)), '') AS whcd,
    NULLIF(BTRIM(CAST(s.fqxm AS VARCHAR)), '') AS fqxm,
    NULLIF(BTRIM(CAST(s.fqzjhm AS VARCHAR)), '') AS fqzjhm,
    NULLIF(BTRIM(CAST(s.mqxm AS VARCHAR)), '') AS mqxm,
    NULLIF(BTRIM(CAST(s.mqzjhm AS VARCHAR)), '') AS mqzjhm,
    NULLIF(BTRIM(CAST(s.lxdh AS VARCHAR)), '') AS lxdh
FROM ywdata.t_ap_czrk_jbxx s
JOIN jcgkzx_monitor.wcnr_target_pool tp
  ON tp.zjhm = UPPER(NULLIF(BTRIM(CAST(s.gmsfhm AS VARCHAR)), ''))
WHERE NULLIF(BTRIM(CAST(s.gmsfhm AS VARCHAR)), '') IS NOT NULL
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO jcgkzx_monitor.wcnr_rk_zp (
    zjhm,
    xm,
    zp,
    zp_source,
    update_time
)
SELECT
    UPPER(NULLIF(BTRIM(CAST(s.gmsfhm AS VARCHAR)), '')) AS zjhm,
    NULLIF(BTRIM(CAST(s.xm AS VARCHAR)), '') AS xm,
    ENCODE(s.xp, 'base64') AS zp,
    'dsfb' AS zp_source,
    COALESCE(s.gxsj, s.jltbsj, CURRENT_TIMESTAMP) AS update_time
FROM ywdata.t_dsfb_rk_zpxx s
JOIN jcgkzx_monitor.wcnr_target_pool tp
  ON tp.zjhm = UPPER(NULLIF(BTRIM(CAST(s.gmsfhm AS VARCHAR)), ''))
WHERE NULLIF(BTRIM(CAST(s.gmsfhm AS VARCHAR)), '') IS NOT NULL
  AND s.xp IS NOT NULL
ON CONFLICT (zjhm) DO NOTHING;

INSERT INTO jcgkzx_monitor.wcnr_ly_checkin (
    zjhm,
    xm,
    xb,
    nl,
    lgmc,
    lgdz,
    rzsj,
    lksj,
    tfrxm,
    tfrzjhm,
    ssfj,
    sspcs
)
SELECT
    UPPER(NULLIF(BTRIM(CAST(s.zjhm AS VARCHAR)), '')) AS zjhm,
    NULLIF(BTRIM(CAST(s.xm AS VARCHAR)), '') AS xm,
    NULLIF(BTRIM(CAST(s.xb AS VARCHAR)), '') AS xb,
    CASE
        WHEN s.csrq IS NOT NULL
            THEN DATE_PART('year', AGE(COALESCE(s.rzsj, CURRENT_TIMESTAMP), s.csrq))::INTEGER
        ELSE NULL
    END AS nl,
    NULLIF(BTRIM(CAST(s.dwjymc AS VARCHAR)), '') AS lgmc,
    NULLIF(BTRIM(CAST(s.dwbgdz_qhnxxdz AS VARCHAR)), '') AS lgdz,
    s.rzsj,
    s.lksj,
    NULLIF(BTRIM(CAST(s.dbr AS VARCHAR)), '') AS tfrxm,
    NULL::VARCHAR AS tfrzjhm,
    NULL::VARCHAR AS ssfj,
    NULL::VARCHAR AS sspcs
FROM ywdata.t_ly_checkin_gn_merge s
JOIN jcgkzx_monitor.wcnr_target_pool tp
  ON tp.zjhm = UPPER(NULLIF(BTRIM(CAST(s.zjhm AS VARCHAR)), ''))
WHERE NULLIF(BTRIM(CAST(s.zjhm AS VARCHAR)), '') IS NOT NULL
  AND s.rzsj IS NOT NULL
  AND s.rzsj >= (CURRENT_DATE - INTERVAL '1 year')::TIMESTAMP;

WITH normalized AS (
    SELECT
        UPPER(NULLIF(BTRIM(CAST(s.id_number AS VARCHAR)), '')) AS zjhm,
        NULLIF(BTRIM(CAST(s.name AS VARCHAR)), '') AS xm,
        NULLIF(BTRIM(CAST(s.device_id AS VARCHAR)), '') AS device_id,
        COALESCE(
            NULLIF(BTRIM(CAST(s.labelvalue AS VARCHAR)), ''),
            NULLIF(BTRIM(CAST(s.directorycode AS VARCHAR)), ''),
            NULLIF(BTRIM(CAST(s.device_id AS VARCHAR)), '')
        ) AS device_name,
        CASE
            WHEN NULLIF(BTRIM(CAST(s.shot_time AS VARCHAR)), '') IS NULL THEN NULL
            WHEN BTRIM(CAST(s.shot_time AS VARCHAR)) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
                THEN BTRIM(CAST(s.shot_time AS VARCHAR))::TIMESTAMP
            WHEN BTRIM(CAST(s.shot_time AS VARCHAR)) ~ '^[0-9]{14}$'
                THEN TO_TIMESTAMP(BTRIM(CAST(s.shot_time AS VARCHAR)), 'YYYYMMDDHH24MISS')::TIMESTAMP
            ELSE NULL
        END AS shot_time,
        NULLIF(BTRIM(CAST(s.face_image AS VARCHAR)), '') AS face_image,
        NULLIF(BTRIM(CAST(s.libname AS VARCHAR)), '') AS libname
    FROM ywdata.t_spy_ryrlgj_xx s
    WHERE NULLIF(BTRIM(CAST(s.id_number AS VARCHAR)), '') IS NOT NULL
      AND NULLIF(BTRIM(CAST(s.libname AS VARCHAR)), '') IS NOT NULL
)
INSERT INTO jcgkzx_monitor.wcnr_ryrl_gj (
    zjhm,
    xm,
    device_id,
    device_name,
    shot_time,
    face_image,
    jd,
    wd,
    ssfj,
    sspcs
)
SELECT
    n.zjhm,
    n.xm,
    n.device_id,
    n.device_name,
    n.shot_time,
    n.face_image,
    112.0::NUMERIC AS jd,
    22.9::NUMERIC AS wd,
    NULL::VARCHAR AS ssfj,
    NULL::VARCHAR AS sspcs
FROM normalized n
JOIN jcgkzx_monitor.wcnr_target_pool tp
  ON tp.zjhm = n.zjhm
WHERE n.libname = '全市未成年人'
  AND n.shot_time IS NOT NULL
  AND n.shot_time >= TIMESTAMP '2026-01-01';
