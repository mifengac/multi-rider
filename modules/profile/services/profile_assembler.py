from itertools import combinations

from shared.config.config import logger
from shared.db.kingbase import query_one, query_all
from modules.score.services.score_store import get_score_trend


def get_basic_info(zjhm: str) -> dict:
    sql = """
        SELECT c.zjhm, c.xm, c.xb, c.mz, c.csrq, c.hjdz, c.xzdxz, c.whcd,
               c.fqxm, c.fqzjhm, c.mqxm, c.mqzjhm, c.lxdh
        FROM "jcgkzx_monitor"."wcnr_czrk" c
        WHERE c.zjhm = %(zjhm)s
    """
    row = query_one(sql, {"zjhm": zjhm})
    if not row:
        pool_sql = """
            SELECT zjhm, xm, xb, csrq, ssfj, sspcs
            FROM "jcgkzx_monitor"."wcnr_target_pool"
            WHERE zjhm = %(zjhm)s
        """
        row = query_one(pool_sql, {"zjhm": zjhm})
    return row or {}


def get_photo(zjhm: str) -> dict:
    sql = """
        SELECT zjhm, zp, zp_source
        FROM "jcgkzx_monitor"."wcnr_rk_zp"
        WHERE zjhm = %(zjhm)s
    """
    return query_one(sql, {"zjhm": zjhm})


def get_family_info(zjhm: str) -> dict:
    sql = """
        SELECT knjtlx, etlb, fmsftswc, jhr1xm, jhr1lxdh, fxdj
        FROM "ywdata"."b_per_qskjwcnr"
        WHERE zjhm = %(zjhm)s
        LIMIT 1
    """
    try:
        return query_one(sql, {"zjhm": zjhm})
    except Exception:
        return {}


def get_education_info(zjhm: str) -> dict:
    dropout_sql = """
        SELECT
            zjhm,
            xm,
            NULL::VARCHAR AS yxx,
            NULL::VARCHAR AS nj,
            jxqk,
            NULL::VARCHAR AS ssbm
        FROM "ywdata"."b_per_qscxwcnr"
        WHERE zjhm = %(zjhm)s LIMIT 1
    """
    truant_sql = """
        SELECT zjhm, xm, jxqk, fxdj
        FROM "ywdata"."b_per_qskjwcnr"
        WHERE zjhm = %(zjhm)s LIMIT 1
    """
    lost_sql = """
        SELECT zjhm, xm, ly
        FROM "ywdata"."b_per_qslswcnr"
        WHERE zjhm = %(zjhm)s LIMIT 1
    """
    sfz_sql = """
        SELECT yxx, nj, jzyy, whdj
        FROM "ywdata"."zq_zfba_wcnr_sfzxx"
        WHERE sfzhm = %(zjhm)s LIMIT 1
    """

    dropout = query_one(dropout_sql, {"zjhm": zjhm})
    if dropout:
        return {"status": "dropout", **dropout}

    lost = query_one(lost_sql, {"zjhm": zjhm})
    if lost:
        return {"status": "lost", **lost}

    truant = query_one(truant_sql, {"zjhm": zjhm})
    if truant:
        return {"status": "truant", **truant}

    sfz = query_one(sfz_sql, {"zjhm": zjhm})
    if sfz:
        return {"status": "enrolled", **sfz}

    return {"status": "unknown"}


def get_cases(zjhm: str) -> list[dict]:
    sql = """
        SELECT a."ajxx_ajbh", a."ajxx_ajmc", a."ajxx_ay",
               a."ajxx_fasj", a."ajxx_cbdw_mc"
        FROM "ywdata"."zq_zfba_ajxx" a
        JOIN "ywdata"."zq_zfba_xyrxx" x
          ON x."ajxx_join_ajxx_ajbh" = a."ajxx_ajbh"
        WHERE x."xyrxx_sfzh" = %(zjhm)s
        ORDER BY a."ajxx_fasj" DESC
    """
    return query_all(sql, {"zjhm": zjhm})


def get_behaviors(zjhm: str) -> list[dict]:
    sql = """
        SELECT wf_sj, wfxw_cn, blxwlx_cn, fsdd, cphm
        FROM "ywdata"."t_wcnrxwjl_xx"
        WHERE sfzhm = %(zjhm)s
        ORDER BY wf_sj DESC
        LIMIT 20
    """
    return query_all(sql, {"zjhm": zjhm})


def get_hotel_records(zjhm: str) -> list[dict]:
    sql = """
        SELECT lgmc, lgdz, rzsj, lksj, tfrxm, tfrzjhm
        FROM "jcgkzx_monitor"."wcnr_ly_checkin"
        WHERE zjhm = %(zjhm)s
        ORDER BY rzsj DESC
        LIMIT 10
    """
    return query_all(sql, {"zjhm": zjhm})


def get_co_suspects(zjhm: str) -> list[dict]:
    sql = """
        SELECT x2."xyrxx_sfzh" AS zjhm, x2."xyrxx_xm" AS xm,
               COUNT(*) AS case_count
        FROM "ywdata"."zq_zfba_xyrxx" x1
        JOIN "ywdata"."zq_zfba_xyrxx" x2
          ON x2."ajxx_join_ajxx_ajbh" = x1."ajxx_join_ajxx_ajbh"
          AND x2."xyrxx_sfzh" <> x1."xyrxx_sfzh"
        WHERE x1."xyrxx_sfzh" = %(zjhm)s
          AND NULLIF(BTRIM(COALESCE(x2."xyrxx_sfzh", '')), '') IS NOT NULL
        GROUP BY x2."xyrxx_sfzh", x2."xyrxx_xm"
        ORDER BY case_count DESC
        LIMIT 10
    """
    return query_all(sql, {"zjhm": zjhm})


def get_score_info(zjhm: str) -> dict:
    sql = """
        SELECT total_score, risk_level, dim_case, dim_behavior,
               dim_family, dim_education, dim_social, calc_time
        FROM "jcgkzx_monitor"."wcnr_score"
        WHERE zjhm = %(zjhm)s
    """
    return query_one(sql, {"zjhm": zjhm})


def detect_gang(zjhm: str, xm: str | None, co_suspects: list[dict]) -> dict:
    member_map = {zjhm: xm or ""}
    for item in co_suspects:
        co_zjhm = item.get("zjhm")
        if co_zjhm:
            member_map[co_zjhm] = item.get("xm") or ""

    if len(member_map) < 3:
        return {"is_gang": False, "size": 0, "members": []}

    params = {f"p{i}": person_zjhm for i, person_zjhm in enumerate(member_map)}
    placeholders = ", ".join([f"%(p{i})s" for i in range(len(member_map))])
    sql = f"""
        SELECT x."ajxx_join_ajxx_ajbh" AS ajbh,
               x."xyrxx_sfzh" AS zjhm,
               x."xyrxx_xm" AS xm
        FROM "ywdata"."zq_zfba_xyrxx" x
        WHERE x."xyrxx_sfzh" IN ({placeholders})
          AND NULLIF(BTRIM(COALESCE(x."xyrxx_sfzh", '')), '') IS NOT NULL
    """
    rows = query_all(sql, params)
    cases_by_person = {person_zjhm: set() for person_zjhm in member_map}
    for row in rows:
        row_zjhm = row.get("zjhm")
        ajbh = row.get("ajbh")
        if row_zjhm in cases_by_person and ajbh:
            cases_by_person[row_zjhm].add(ajbh)
            if row.get("xm"):
                member_map[row_zjhm] = row.get("xm")

    people = list(member_map.keys())
    linked_pairs = set()
    for left, right in combinations(people, 2):
        if cases_by_person.get(left, set()) & cases_by_person.get(right, set()):
            linked_pairs.add(frozenset((left, right)))

    for size in range(len(people), 2, -1):
        for group in combinations(people, size):
            if zjhm not in group:
                continue
            if all(frozenset(pair) in linked_pairs for pair in combinations(group, 2)):
                ordered = [zjhm] + [person_zjhm for person_zjhm in people if person_zjhm != zjhm and person_zjhm in group]
                return {
                    "is_gang": True,
                    "size": len(ordered),
                    "members": [{"zjhm": person_zjhm, "xm": member_map.get(person_zjhm, "")} for person_zjhm in ordered],
                }

    return {"is_gang": False, "size": 0, "members": []}


def assemble_profile(zjhm: str) -> dict:
    basic = get_basic_info(zjhm)
    if not basic:
        return {}
    co_suspects = get_co_suspects(zjhm)
    try:
        score_trend = get_score_trend(zjhm, 6)
    except Exception as exc:
        logger.warning("Score trend skipped for %s: %s", zjhm, exc)
        score_trend = []

    return {
        "basic": basic,
        "photo": get_photo(zjhm),
        "family": get_family_info(zjhm),
        "education": get_education_info(zjhm),
        "cases": get_cases(zjhm),
        "behaviors": get_behaviors(zjhm),
        "hotels": get_hotel_records(zjhm),
        "relations": {
            "co_suspects": co_suspects,
            "gang": detect_gang(zjhm, basic.get("xm"), co_suspects),
        },
        "score": get_score_info(zjhm),
        "score_trend": score_trend,
    }
