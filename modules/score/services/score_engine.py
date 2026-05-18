from shared.config.config import logger
from shared.db.kingbase import query_all
from .dim_case import calc_case_score
from .dim_behavior import calc_behavior_score
from .dim_family import calc_family_score
from .dim_education import calc_education_score
from .dim_social import calc_social_score
from .score_store import upsert_score, append_history


RISK_LEVELS = [
    (80, "extreme"),
    (60, "high"),
    (40, "medium"),
    (20, "low"),
    (0, "normal"),
]


def _map_risk_level(score: int) -> str:
    for threshold, level in RISK_LEVELS:
        if score >= threshold:
            return level
    return "normal"


def calculate_score(zjhm: str) -> dict:
    dim_case, case_detail = calc_case_score(zjhm)
    dim_behavior, behavior_detail = calc_behavior_score(zjhm)
    dim_family, family_detail = calc_family_score(zjhm)
    dim_education, education_detail = calc_education_score(zjhm)
    dim_social, social_detail = calc_social_score(zjhm)

    total = min(dim_case + dim_behavior + dim_family + dim_education + dim_social, 100)
    risk_level = _map_risk_level(total)

    detail_json = {
        "case": case_detail,
        "behavior": behavior_detail,
        "family": family_detail,
        "education": education_detail,
        "social": social_detail,
    }

    upsert_score(zjhm, total, risk_level, dim_case, dim_behavior,
                 dim_family, dim_education, dim_social, detail_json)
    append_history(zjhm, total, risk_level)

    return {
        "zjhm": zjhm,
        "total_score": total,
        "risk_level": risk_level,
        "dim_case": dim_case,
        "dim_behavior": dim_behavior,
        "dim_family": dim_family,
        "dim_education": dim_education,
        "dim_social": dim_social,
        "detail": detail_json,
    }


def batch_recalculate() -> dict:
    sql = 'SELECT zjhm FROM "jcgkzx_monitoer"."wcnr_target_pool"'
    rows = query_all(sql)

    total = len(rows)
    success = 0
    failed = 0

    for row in rows:
        zjhm = row.get("zjhm")
        if not zjhm:
            continue
        try:
            calculate_score(zjhm)
            success += 1
        except Exception as e:
            failed += 1
            logger.warning("Score calculation failed for %s: %s", zjhm, e)

    logger.info("Batch recalculate complete: total=%d success=%d failed=%d", total, success, failed)
    return {"total": total, "success": success, "failed": failed}
