from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from shared.db.kingbase import query_one


def _pct(filled: Any, total: Any) -> float | None:
    total_int = int(total or 0)
    if total_int <= 0:
        return None
    return round(int(filled or 0) * 100.0 / total_int, 1)


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value).split(" ")[0]


def _safe_table(name: str, build: Callable[[], dict]) -> dict:
    try:
        item = build()
    except Exception as exc:
        return {"name": name, "error": str(exc)}
    item.setdefault("name", name)
    return item


def _target_pool() -> dict:
    row = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(*) FILTER (WHERE ssfj IS NOT NULL) AS with_ssfj,
               COUNT(*) FILTER (WHERE csrq IS NOT NULL) AS with_csrq
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        """
    )
    total = int(row.get("rows") or 0)
    return {
        "name": "jcgkzx_monitor.wcnr_target_pool",
        "rows": total,
        "fields": {
            "ssfj_filled_pct": _pct(row.get("with_ssfj"), total),
            "csrq_filled_pct": _pct(row.get("with_csrq"), total),
        },
    }


def _score() -> dict:
    row = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(*) FILTER (WHERE risk_level IS NOT NULL) AS with_risk
        FROM "jcgkzx_monitor"."wcnr_score"
        """
    )
    total = int(row.get("rows") or 0)
    return {
        "name": "jcgkzx_monitor.wcnr_score",
        "rows": total,
        "fields": {"risk_level_filled_pct": _pct(row.get("with_risk"), total)},
    }


def _alert() -> dict:
    row = query_one('SELECT COUNT(*) AS rows FROM "jcgkzx_monitor"."wcnr_alert"')
    total = int(row.get("rows") or 0)
    item = {"name": "jcgkzx_monitor.wcnr_alert", "rows": total, "fields": {}}
    if total == 0:
        item["warn"] = "alert table empty"
    return item


def _trajectory() -> dict:
    row = query_one('SELECT COUNT(*) AS rows FROM "jcgkzx_monitor"."wcnr_ryrl_gj"')
    item = {"name": "jcgkzx_monitor.wcnr_ryrl_gj", "rows": int(row.get("rows") or 0)}
    try:
        last_30d = query_one(
            """
            SELECT COUNT(*) AS rows,
                   COUNT(*) FILTER (WHERE jd IS NOT NULL AND wd IS NOT NULL) AS with_coord
            FROM "jcgkzx_monitor"."wcnr_ryrl_gj"
            WHERE shot_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            """
        )
        total_30d = int(last_30d.get("rows") or 0)
        item["last_30d"] = {
            "rows": total_30d,
            "with_coord_pct": _pct(last_30d.get("with_coord"), total_30d),
        }
    except Exception as exc:
        item["last_30d"] = {"error": str(exc)}
    return item


def _score_history() -> dict:
    row = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(DISTINCT DATE(calc_time)) AS distinct_calc_days
        FROM "jcgkzx_monitor"."wcnr_score_history"
        """
    )
    days = int(row.get("distinct_calc_days") or 0)
    item = {
        "name": "jcgkzx_monitor.wcnr_score_history",
        "rows": int(row.get("rows") or 0),
        "distinct_calc_days": days,
    }
    if days <= 1:
        item["warn"] = "only 1 snapshot day"
    return item


def _count_only(name: str, sql_name: str) -> dict:
    row = query_one(f'SELECT COUNT(*) AS rows FROM {sql_name}')
    return {"name": name, "rows": int(row.get("rows") or 0)}


def _cases() -> dict:
    row = query_one(
        """
        SELECT COUNT(*) AS rows,
               MIN("ajxx_fasj") AS min_fasj,
               MAX("ajxx_fasj") AS max_fasj
        FROM "ywdata"."zq_zfba_ajxx"
        """
    )
    return {
        "name": "ywdata.zq_zfba_ajxx",
        "rows": int(row.get("rows") or 0),
        "fasj_range": [_date_text(row.get("min_fasj")), _date_text(row.get("max_fasj"))],
    }


def _add_warnings(tables: list[dict]) -> list[str]:
    warnings: list[str] = []
    for item in tables:
        name = item.get("name")
        if name == "jcgkzx_monitor.wcnr_alert" and item.get("rows") == 0:
            warnings.append("wcnr_alert table empty (no alerts seeded yet)")
        fields = item.get("fields") or {}
        for field, value in fields.items():
            if value is None or value >= 50:
                continue
            if name == "jcgkzx_monitor.wcnr_target_pool" and field == "ssfj_filled_pct":
                warnings.append("wcnr_target_pool.ssfj 100% missing (will degrade area ranking)")
            elif name == "jcgkzx_monitor.wcnr_target_pool" and field == "csrq_filled_pct":
                warnings.append("wcnr_target_pool.csrq 100% missing (will degrade age distribution)")
            else:
                warnings.append(f"{name}.{field} filled below 50%")
    return warnings


def collect_health() -> dict:
    tables = [
        _safe_table("jcgkzx_monitor.wcnr_target_pool", _target_pool),
        _safe_table("jcgkzx_monitor.wcnr_score", _score),
        _safe_table("jcgkzx_monitor.wcnr_alert", _alert),
        _safe_table("jcgkzx_monitor.wcnr_ryrl_gj", _trajectory),
        _safe_table("jcgkzx_monitor.wcnr_score_history", _score_history),
        _safe_table(
            "jcgkzx_monitor.wcnr_ly_checkin",
            lambda: _count_only("jcgkzx_monitor.wcnr_ly_checkin", '"jcgkzx_monitor"."wcnr_ly_checkin"'),
        ),
        _safe_table("ywdata.zq_zfba_ajxx", _cases),
        _safe_table(
            "ywdata.zq_zfba_xyrxx",
            lambda: _count_only("ywdata.zq_zfba_xyrxx", '"ywdata"."zq_zfba_xyrxx"'),
        ),
        _safe_table(
            "ywdata.zq_zfba_wcnr_sfzxx",
            lambda: _count_only("ywdata.zq_zfba_wcnr_sfzxx", '"ywdata"."zq_zfba_wcnr_sfzxx"'),
        ),
    ]
    return {
        "timestamp": datetime.now().replace(microsecond=0).isoformat(),
        "tables": tables,
        "warnings": _add_warnings(tables),
    }
