from shared.db.kingbase import query_one


def calc_education_score(zjhm: str) -> tuple[int, dict]:
    dropout_sql = """
        SELECT zjhm, xm FROM "ywdata"."b_per_qscxwcnr" WHERE zjhm = %(zjhm)s LIMIT 1
    """
    lost_sql = """
        SELECT zjhm, xm FROM "ywdata"."b_per_qslswcnr" WHERE zjhm = %(zjhm)s LIMIT 1
    """
    truant_sql = """
        SELECT zjhm, xm, jxqk FROM "ywdata"."b_per_qskjwcnr" WHERE zjhm = %(zjhm)s LIMIT 1
    """

    dropout = query_one(dropout_sql, {"zjhm": zjhm})
    if dropout:
        return 15, {"status": "dropout"}

    lost = query_one(lost_sql, {"zjhm": zjhm})
    if lost:
        return 13, {"status": "lost"}

    truant = query_one(truant_sql, {"zjhm": zjhm})
    if truant:
        jxqk = truant.get("jxqk") or ""
        if "频繁" in jxqk or "严重" in jxqk or "长期" in jxqk:
            return 10, {"status": "truant_frequent", "jxqk": jxqk[:50]}
        return 6, {"status": "truant", "jxqk": jxqk[:50]}

    return 0, {"status": "normal"}
