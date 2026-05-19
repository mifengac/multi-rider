from datetime import datetime

from shared.db.kingbase import query_all
from modules.profile.models import TimelineEvent


def _to_iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value)
    try:
        return datetime.fromisoformat(text[:19]).isoformat()
    except ValueError:
        return text


def _clean_detail(row: dict) -> dict:
    detail = {}
    for key, value in row.items():
        if key in {"time", "title"}:
            continue
        detail[key] = _to_iso(value) if hasattr(value, "isoformat") else value
    return detail


def _build_events(rows: list[dict], event_type: str, default_title: str) -> list[dict]:
    events = []
    for row in rows:
        event_time = _to_iso(row.get("time"))
        if not event_time:
            continue
        title = row.get("title") or default_title
        event = TimelineEvent(
            time=event_time,
            type=event_type,
            title=title,
            detail=_clean_detail(row),
        )
        events.append(event.to_dict())
    return events


def build_timeline(zjhm: str) -> list[dict]:
    case_sql = """
        SELECT a."ajxx_fasj" AS time,
               COALESCE(a."ajxx_ay", a."ajxx_ajmc", a."ajxx_ajbh") AS title,
               a."ajxx_ajbh" AS ajbh,
               a."ajxx_ajmc" AS ajmc,
               a."ajxx_ay" AS ay,
               a."ajxx_cbdw_mc" AS cbdw
        FROM "ywdata"."zq_zfba_ajxx" a
        JOIN "ywdata"."zq_zfba_xyrxx" x
          ON x."ajxx_join_ajxx_ajbh" = a."ajxx_ajbh"
        WHERE x."xyrxx_sfzh" = %(zjhm)s
    """
    behavior_sql = """
        SELECT wf_sj AS time,
               wfxw_cn AS title,
               wfxw_cn,
               blxwlx_cn,
               fsdd,
               cphm
        FROM "ywdata"."t_wcnrxwjl_xx"
        WHERE sfzhm = %(zjhm)s
    """
    trajectory_sql = """
        SELECT shot_time AS time,
               device_name AS title,
               device_name,
               jd,
               wd,
               ssfj,
               sspcs
        FROM "jcgkzx_monitor"."wcnr_ryrl_gj"
        WHERE zjhm = %(zjhm)s
        ORDER BY shot_time DESC
        LIMIT 50
    """
    hotel_sql = """
        SELECT rzsj AS time,
               lgmc AS title,
               lgmc,
               lgdz,
               lksj,
               tfrxm,
               tfrzjhm
        FROM "jcgkzx_monitor"."wcnr_ly_checkin"
        WHERE zjhm = %(zjhm)s
    """

    events = []
    events.extend(_build_events(query_all(case_sql, {"zjhm": zjhm}), "case", "案件"))
    events.extend(_build_events(query_all(behavior_sql, {"zjhm": zjhm}), "behavior", "行为"))
    events.extend(_build_events(query_all(trajectory_sql, {"zjhm": zjhm}), "trajectory", "轨迹"))
    events.extend(_build_events(query_all(hotel_sql, {"zjhm": zjhm}), "hotel", "入住"))
    return sorted(events, key=lambda item: item["time"], reverse=True)
