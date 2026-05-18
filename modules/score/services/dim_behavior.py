from datetime import datetime, timedelta
from shared.db.kingbase import query_all

SEVERITY_MAP = {
    "飙车": 5, "炸街": 5, "翘车头": 5,
    "盗窃": 5, "偷窃": 5,
    "斗殴": 4, "打架": 4,
    "寻衅滋事": 4,
    "损毁财物": 3, "毁坏": 3,
    "翘课": 2, "旷课": 2, "聚集": 2,
}


def _match_severity(text: str) -> int:
    if not text:
        return 2
    for keyword, score in SEVERITY_MAP.items():
        if keyword in text:
            return score
    return 2


def _time_decay(event_time) -> float:
    if not event_time:
        return 1.0
    now = datetime.now()
    three_months = now - timedelta(days=90)
    six_months = now - timedelta(days=180)

    try:
        if isinstance(event_time, str):
            dt = datetime.fromisoformat(event_time[:19])
        else:
            dt = event_time
    except (ValueError, TypeError):
        return 1.0

    if dt >= three_months:
        return 1.5
    elif dt >= six_months:
        return 1.0
    else:
        return 0.5


def calc_behavior_score(zjhm: str) -> tuple[int, dict]:
    behavior_sql = """
        SELECT wf_sj, wfxw_cn, blxwlx_cn
        FROM "ywdata"."t_wcnrxwjl_xx"
        WHERE sfzhm = %(zjhm)s
    """
    bczj_sql = """
        SELECT wfrq AS wf_sj, wfnr AS wfxw_cn
        FROM "ywdata"."b_per_qswcnrbczj"
        WHERE sfzhm = %(zjhm)s
    """
    records = query_all(behavior_sql, {"zjhm": zjhm})
    bczj_records = query_all(bczj_sql, {"zjhm": zjhm})

    all_records = []
    for r in records:
        text = r.get("wfxw_cn") or r.get("blxwlx_cn") or ""
        all_records.append({"time": r.get("wf_sj"), "text": text, "source": "behavior"})
    for r in bczj_records:
        text = r.get("wfxw_cn") or ""
        all_records.append({"time": r.get("wf_sj"), "text": text, "source": "bczj"})

    if not all_records:
        return 0, {"record_count": 0, "records": []}

    total = 0.0
    details = []
    for rec in all_records:
        sev = _match_severity(rec["text"])
        decay = _time_decay(rec["time"])
        contribution = sev * decay
        total += contribution
        details.append({
            "text": rec["text"][:50],
            "severity": sev,
            "decay": decay,
            "contribution": round(contribution, 1),
        })

    score = min(int(total), 25)
    return score, {"record_count": len(all_records), "raw_total": round(total, 1), "records": details[:10]}
