from shared.db.kingbase import query_one


def calc_family_score(zjhm: str) -> tuple[int, dict]:
    sql = """
        SELECT jtqk, knjtlx, etlb, fmsftswc, jhr1xm, jhr1lxdh
        FROM "ywdata"."b_per_qskjwcnr"
        WHERE zjhm = %(zjhm)s
        LIMIT 1
    """
    row = query_one(sql, {"zjhm": zjhm})
    if not row:
        return 0, {"source": "no_data"}

    score = 0
    detail = {}

    fmsftswc = row.get("fmsftswc") or ""
    if "双方" in fmsftswc or "父母均" in fmsftswc:
        score += 8
        detail["parents_out"] = "both"
    elif "外出" in fmsftswc or "务工" in fmsftswc:
        score += 5
        detail["parents_out"] = "one"

    knjtlx = row.get("knjtlx") or ""
    if any(k in knjtlx for k in ("低保", "边缘", "困难")):
        score += 5
        detail["poverty"] = knjtlx

    jhr1xm = row.get("jhr1xm") or ""
    etlb = row.get("etlb") or ""

    if not jhr1xm or "孤儿" in etlb or "困境" in etlb:
        score += 10
        detail["guardian_missing"] = True
    elif "留守" in etlb:
        score += 4
        detail["left_behind"] = True

    score = min(score, 20)
    detail["raw_score"] = score
    detail["jtqk"] = (row.get("jtqk") or "")[:100]
    return score, detail
