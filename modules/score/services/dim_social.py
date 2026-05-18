from shared.db.kingbase import query_all


def calc_social_score(zjhm: str) -> tuple[int, dict]:
    co_suspects_sql = """
        SELECT DISTINCT x2."xyrxx_sfzh", x2."xyrxx_xm",
               x1."ajxx_join_ajxx_ajbh"
        FROM "ywdata"."zq_zfba_xyrxx" x1
        JOIN "ywdata"."zq_zfba_xyrxx" x2
          ON x2."ajxx_join_ajxx_ajbh" = x1."ajxx_join_ajxx_ajbh"
          AND x2."xyrxx_sfzh" <> x1."xyrxx_sfzh"
        WHERE x1."xyrxx_sfzh" = %(zjhm)s
          AND NULLIF(BTRIM(COALESCE(x2."xyrxx_sfzh", '')), '') IS NOT NULL
    """
    co_suspects = query_all(co_suspects_sql, {"zjhm": zjhm})

    if not co_suspects:
        return 0, {"co_suspect_count": 0}

    unique_suspects = {}
    case_suspect_count = {}
    for row in co_suspects:
        sfzh = row.get("xyrxx_sfzh")
        ajbh = row.get("ajxx_join_ajxx_ajbh")
        if sfzh:
            unique_suspects[sfzh] = row.get("xyrxx_xm", "")
        if ajbh:
            case_suspect_count[ajbh] = case_suspect_count.get(ajbh, 1) + 1

    high_risk_count = 0
    if unique_suspects:
        placeholders = ", ".join([f"%(s{i})s" for i in range(len(unique_suspects))])
        params = {f"s{i}": sfzh for i, sfzh in enumerate(unique_suspects.keys())}
        score_sql = f"""
            SELECT zjhm, total_score
            FROM "jcgkzx_monitor"."wcnr_score"
            WHERE zjhm IN ({placeholders}) AND total_score >= 60
        """
        high_risk_rows = query_all(score_sql, params)
        high_risk_count = len(high_risk_rows)

    contact_score = min(high_risk_count * 3, 7)

    has_gang = any(cnt >= 3 for cnt in case_suspect_count.values())
    gang_bonus = 3 if has_gang else 0

    score = min(contact_score + gang_bonus, 10)
    detail = {
        "co_suspect_count": len(unique_suspects),
        "high_risk_contacts": high_risk_count,
        "contact_score": contact_score,
        "has_gang": has_gang,
        "gang_bonus": gang_bonus,
    }
    return score, detail
