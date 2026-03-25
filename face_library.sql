SELECT
    bzr."zjlx",
    bzr."zjhm",
    bzr."xm",
    tdrz."xp"
FROM "stdata"."b_zdry_ryxx" bzr
LEFT JOIN "ywdata"."t_dsfb_rk_zpxx" tdrz
    ON bzr."zjhm" = tdrz."gmsfhm"
WHERE bzr."sflg" = 1
  AND bzr."deleteflag" = 0;
