SELECT
    bzr."zjlx",
    bzr."zjhm",
    bzr."xm",
    tdrz."xp"
FROM "stdata"."bzdry_ryxx" bzr
LEFT JOIN "tdsfbrk_zpxx" tdrz
    ON bzr."zjhm" = tdrz."gmsfhm"
WHERE bzr."sflg" = 1
  AND bzr."deleteflag" = 0;
