from datetime import datetime, timedelta
from shared.db.kingbase import query_all


def calc_case_score(zjhm: str) -> tuple[int, dict]:
    cases_sql = """
        SELECT a."ajxx_ajbh", a."ajxx_ay", a."ajxx_fasj"
        FROM "ywdata"."zq_zfba_ajxx" a
        JOIN "ywdata"."zq_zfba_xyrxx" x
          ON x."ajxx_join_ajxx_ajbh" = a."ajxx_ajbh"
        WHERE x."xyrxx_sfzh" = %(zjhm)s
    """
    bczj_sql = """
        SELECT ajbh, ay, wfsj AS ajxx_fasj
        FROM "ywdata"."b_evt_jjzdbczjajxx"
        WHERE dsrsfzmhm = %(zjhm)s
    """
    cases = query_all(cases_sql, {"zjhm": zjhm})
    bczj_cases = query_all(bczj_sql, {"zjhm": zjhm})

    seen_ajbh = {c.get("ajxx_ajbh") for c in cases if c.get("ajxx_ajbh")}
    for bc in bczj_cases:
        if bc.get("ajbh") not in seen_ajbh:
            cases.append({
                "ajxx_ajbh": bc.get("ajbh"),
                "ajxx_ay": bc.get("ay", ""),
                "ajxx_fasj": bc.get("ajxx_fasj"),
            })

    case_count = len(cases)
    if case_count == 0:
        return 0, {"case_count": 0, "cases": []}

    if case_count == 1:
        base = 8
    elif case_count == 2:
        base = 15
    else:
        base = 22

    one_year_ago = datetime.now() - timedelta(days=365)
    severity_total = 0
    case_details = []

    for c in cases:
        ay = c.get("ajxx_ay") or ""
        fasj = c.get("ajxx_fasj")

        if any(k in ay for k in ("抢劫", "抢夺", "故意伤害")):
            sev = 4
        elif any(k in ay for k in ("盗窃", "诈骗")):
            sev = 3
        elif any(k in ay for k in ("寻衅滋事", "聚众斗殴")):
            sev = 2
        else:
            sev = 1

        is_old = False
        if fasj:
            try:
                if isinstance(fasj, str):
                    fasj_dt = datetime.fromisoformat(fasj[:19])
                else:
                    fasj_dt = fasj
                if fasj_dt < one_year_ago:
                    sev = sev // 2
                    is_old = True
            except (ValueError, TypeError):
                pass

        severity_total += sev
        case_details.append({"ajbh": c.get("ajxx_ajbh"), "ay": ay, "severity": sev, "old": is_old})

    score = min(base + severity_total, 30)
    detail = {"case_count": case_count, "base": base, "severity_total": severity_total, "cases": case_details}
    return score, detail
