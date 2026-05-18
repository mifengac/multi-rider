from shared.db.kingbase import query_one, query_all


def get_basic_info(zjhm: str) -> dict:
    sql = """
        SELECT c.zjhm, c.xm, c.xb, c.mz, c.csrq, c.hjdz, c.xzdxz, c.whcd,
               c.fqxm, c.fqzjhm, c.mqxm, c.mqzjhm, c.lxdh
        FROM "jcgkzx_monitoer"."wcnr_czrk" c
        WHERE c.zjhm = %(zjhm)s
    """
    row = query_one(sql, {"zjhm": zjhm})
    if not row:
        pool_sql = """
            SELECT zjhm, xm, xb, csrq, ssfj, sspcs
            FROM "jcgkzx_monitoer"."wcnr_target_pool"
            WHERE zjhm = %(zjhm)s
        """
        row = query_one(pool_sql, {"zjhm": zjhm})
    return row or {}


def get_photo(zjhm: str) -> dict:
    sql = """
        SELECT zjhm, zp, zp_source
        FROM "jcgkzx_monitoer"."wcnr_rk_zp"
        WHERE zjhm = %(zjhm)s
    """
    return query_one(sql, {"zjhm": zjhm})


def get_family_info(zjhm: str) -> dict:
    sql = """
        SELECT jtqk, knjtlx, etlb, fmsftswc, jhr1xm, jhr1zjhm, jhr1lxdh, fxdj
        FROM "ywdata"."b_per_qskjwcnr"
        WHERE zjhm = %(zjhm)s
        LIMIT 1
    """
    return query_one(sql, {"zjhm": zjhm})


def get_education_info(zjhm: str) -> dict:
    dropout_sql = """
        SELECT zjhm, xm, yxx, nj, jxqk, ssbm
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
        SELECT a.ajxx_ajbh, a.ajxx_ajmc, a.ajxx_ay, a.ajxx_fasj, a.ajxx_cbdw_mc
        FROM "ywdata"."zq_zfba_wcnr_ajxx" a
        JOIN "ywdata"."zq_zfba_wcnr_xyr" x
          ON x.ajxx_join_ajxx_ajbh = a.ajxx_ajbh
        WHERE x.xyrxx_sfzh = %(zjhm)s
        ORDER BY a.ajxx_fasj DESC
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
        FROM "jcgkzx_monitoer"."wcnr_ly_checkin"
        WHERE zjhm = %(zjhm)s
        ORDER BY rzsj DESC
        LIMIT 10
    """
    return query_all(sql, {"zjhm": zjhm})


def get_co_suspects(zjhm: str) -> list[dict]:
    sql = """
        SELECT DISTINCT x2.xyrxx_sfzh AS zjhm, x2.xyrxx_xm AS xm,
               COUNT(*) AS case_count
        FROM "ywdata"."zq_zfba_wcnr_xyr" x1
        JOIN "ywdata"."zq_zfba_wcnr_xyr" x2
          ON x2.ajxx_join_ajxx_ajbh = x1.ajxx_join_ajxx_ajbh
          AND x2.xyrxx_sfzh <> x1.xyrxx_sfzh
        WHERE x1.xyrxx_sfzh = %(zjhm)s
        GROUP BY x2.xyrxx_sfzh, x2.xyrxx_xm
        ORDER BY case_count DESC
        LIMIT 10
    """
    return query_all(sql, {"zjhm": zjhm})


def get_score_info(zjhm: str) -> dict:
    sql = """
        SELECT total_score, risk_level, dim_case, dim_behavior,
               dim_family, dim_education, dim_social, calc_time
        FROM "jcgkzx_monitoer"."wcnr_score"
        WHERE zjhm = %(zjhm)s
    """
    return query_one(sql, {"zjhm": zjhm})


def assemble_profile(zjhm: str) -> dict:
    basic = get_basic_info(zjhm)
    if not basic:
        return {}

    return {
        "basic": basic,
        "photo": get_photo(zjhm),
        "family": get_family_info(zjhm),
        "education": get_education_info(zjhm),
        "cases": get_cases(zjhm),
        "behaviors": get_behaviors(zjhm),
        "hotels": get_hotel_records(zjhm),
        "relations": {
            "co_suspects": get_co_suspects(zjhm),
        },
        "score": get_score_info(zjhm),
    }
