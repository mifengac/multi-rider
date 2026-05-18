import math
from typing import Any

from shared.db.kingbase import query_all
from shared.ai.ruizhi_client import embedding, rerank, RuizhiApiError

QINCAI_PATTERN = "盗窃|抢劫|抢夺|诈骗|敲诈勒索"


def fetch_recent_qincai_cases(months: int = 6) -> list[dict[str, Any]]:
    sql = f"""
        SELECT a.ajxx_ajbh AS ajbh,
               a.ajxx_ajmc AS ajmc,
               a.ajxx_ay   AS ay,
               a.ajxx_fasj AS fasj,
               a.ajxx_cbdw_mc AS cbdw
        FROM "ywdata"."zq_zfba_wcnr_ajxx" a
        WHERE a.ajxx_ay ~ %(pattern)s
          AND a.ajxx_fasj IS NOT NULL
          AND a.ajxx_fasj >= CURRENT_DATE - INTERVAL '{int(months)} months'
        ORDER BY a.ajxx_fasj DESC
        LIMIT 50
    """
    rows = query_all(sql, {"pattern": QINCAI_PATTERN})
    return [dict(r) for r in rows]


def _case_text(c: dict) -> str:
    parts = []
    if c.get("ay"):
        parts.append(c["ay"])
    if c.get("ajmc"):
        parts.append(c["ajmc"])
    if c.get("fasj"):
        parts.append(f"时间:{c['fasj']}")
    if c.get("cbdw"):
        parts.append(f"单位:{c['cbdw']}")
    return " ".join(parts) or "未知案件"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_similarity(vectors: list[list[float]], threshold: float = 0.6) -> list[dict]:
    pairs = []
    n = len(vectors)
    for i in range(n):
        for j in range(i + 1, n):
            score = _cosine_similarity(vectors[i], vectors[j])
            if score >= threshold:
                pairs.append({"i": i, "j": j, "score": score})
    pairs.sort(key=lambda p: p["score"], reverse=True)
    return pairs


def find_serial_candidates(cases: list[dict], top_k: int = 10) -> list[dict]:
    if len(cases) < 2:
        return []

    texts = [_case_text(c) for c in cases]

    try:
        vectors = embedding(texts)
    except RuizhiApiError:
        return []

    pairs = compute_similarity(vectors, threshold=0.55)

    if pairs and len(pairs) > 2:
        anchor = texts[pairs[0]["i"]]
        candidates = list({texts[p["j"]] for p in pairs[:20]} | {texts[p["i"]] for p in pairs[:20]})
        try:
            reranked = rerank(anchor, candidates, top_k=min(top_k, len(candidates)))
            for r in reranked:
                r["rerank_score"] = r.get("relevance_score", r.get("score", 0))
        except RuizhiApiError:
            pass

    return pairs[:top_k]
