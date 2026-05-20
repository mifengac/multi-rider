#!/usr/bin/env python
# 内网诊断脚本使用方式：
#   python scripts/diagnostics/internal_dashboard_probe.py --base-url http://127.0.0.1:5001 --zjhm 445381xxxxxxxx0415
# 输出位置：
#   默认写到当前工作目录的 probe_<UTC时间戳>.json，也可通过 --out 指定完整路径。
# 处理方式：
#   执行完成后，把生成的 JSON 文件发回开发即可；脚本会记录错误，不会因单个 probe 失败中断。
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.db.kingbase import query_all, query_one  # noqa: E402


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_out_path() -> str:
    return f"probe_{_utc_now().strftime('%Y%m%dT%H%M%SZ')}.json"


def _mask_id(value: Any) -> Any:
    text = "" if value is None else str(value)
    if len(text) <= 8:
        return text
    return f"{text[:4]}{'*' * (len(text) - 8)}{text[-4:]}"


def _mask_sensitive_row(row: dict[str, Any]) -> dict[str, Any]:
    masked = {}
    id_keys = {"zjhm", "sfzhm", "sfzh", "xyrxx_sfzh", "saryxx_sfzh"}
    for key, value in row.items():
        masked[key] = _mask_id(value) if key.lower() in id_keys else value
    return masked


def _mask_sensitive_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_mask_sensitive_row(row) for row in rows]


def _git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
    except Exception:
        return None


def collect_meta() -> dict[str, Any]:
    return {
        "generated_at_utc": _utc_now().replace(microsecond=0).isoformat(),
        "git_head": _git_head(),
        "python_version": sys.version,
        "multi_rider_image": os.getenv("MULTI_RIDER_IMAGE", ""),
        "kingbase_env": {
            "KINGBASE_HOST": os.getenv("KINGBASE_HOST", ""),
            "KINGBASE_PORT": os.getenv("KINGBASE_PORT", ""),
            "KINGBASE_DB": os.getenv("KINGBASE_DB", os.getenv("KINGBASE_DBNAME", "")),
            "KINGBASE_DBNAME": os.getenv("KINGBASE_DBNAME", ""),
        },
    }


def _safe_db_probe(name: str, build: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        result = build()
        result.setdefault("ok", True)
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _target_pool_probe() -> dict[str, Any]:
    counts = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(ssfj) AS with_ssfj,
               COUNT(csrq) AS with_csrq,
               COUNT(DISTINCT ssfj) AS distinct_ssfj
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        """
    )
    samples = query_all(
        """
        SELECT zjhm, xm, ssfj, sspcs, csrq
        FROM "jcgkzx_monitor"."wcnr_target_pool"
        LIMIT 5
        """
    )
    return {"counts": counts, "sample_count": len(samples), "samples": _mask_sensitive_rows(samples)}


def _score_probe() -> dict[str, Any]:
    counts = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(*) FILTER (WHERE total_score >= 60) AS score_60,
               COUNT(*) FILTER (WHERE total_score >= 80) AS score_80
        FROM "jcgkzx_monitor"."wcnr_score"
        """
    )
    risk_distribution = query_all(
        """
        SELECT risk_level, COUNT(*) AS count
        FROM "jcgkzx_monitor"."wcnr_score"
        GROUP BY risk_level
        ORDER BY count DESC
        """
    )
    return {"counts": counts, "risk_level_distribution": risk_distribution}


def _alert_probe() -> dict[str, Any]:
    counts = query_one('SELECT COUNT(*) AS rows FROM "jcgkzx_monitor"."wcnr_alert"')
    alert_type_top10 = query_all(
        """
        SELECT alert_type, COUNT(*) AS count
        FROM "jcgkzx_monitor"."wcnr_alert"
        GROUP BY alert_type
        ORDER BY count DESC
        LIMIT 10
        """
    )
    return {"counts": counts, "alert_type_top10": alert_type_top10}


def _score_history_probe() -> dict[str, Any]:
    counts = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(DISTINCT DATE(calc_time)) AS distinct_calc_days
        FROM "jcgkzx_monitor"."wcnr_score_history"
        """
    )
    recent_calc_times = query_all(
        """
        SELECT DISTINCT calc_time
        FROM "jcgkzx_monitor"."wcnr_score_history"
        WHERE calc_time IS NOT NULL
        ORDER BY calc_time DESC
        LIMIT 3
        """
    )
    return {"counts": counts, "recent_calc_times": recent_calc_times}


def _trajectory_probe() -> dict[str, Any]:
    counts = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(*) FILTER (WHERE shot_time >= CURRENT_TIMESTAMP - INTERVAL '30 days') AS recent_30d
        FROM "jcgkzx_monitor"."wcnr_ryrl_gj"
        """
    )
    sample = query_all(
        """
        SELECT zjhm, xm, device_name, shot_time, jd, wd
        FROM "jcgkzx_monitor"."wcnr_ryrl_gj"
        ORDER BY shot_time DESC NULLS LAST
        LIMIT 1
        """
    )
    return {"counts": counts, "latest_sample": _mask_sensitive_rows(sample)}


def _case_probe() -> dict[str, Any]:
    counts = query_one(
        """
        SELECT COUNT(*) AS rows,
               MIN("ajxx_fasj") AS min_fasj,
               MAX("ajxx_fasj") AS max_fasj
        FROM "ywdata"."zq_zfba_ajxx"
        """
    )
    ay_top10 = query_all(
        """
        SELECT "ajxx_ay" AS ay, COUNT(*) AS count
        FROM "ywdata"."zq_zfba_ajxx"
        GROUP BY "ajxx_ay"
        ORDER BY count DESC
        LIMIT 10
        """
    )
    cbdw_top10 = query_all(
        """
        SELECT "ajxx_cbdw_mc" AS cbdw_mc, COUNT(*) AS count
        FROM "ywdata"."zq_zfba_ajxx"
        GROUP BY "ajxx_cbdw_mc"
        ORDER BY count DESC
        LIMIT 10
        """
    )
    return {"counts": counts, "ajxx_ay_top10": ay_top10, "ajxx_cbdw_mc_top10": cbdw_top10}


def _suspect_probe() -> dict[str, Any]:
    counts = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(*) FILTER (WHERE LENGTH("xyrxx_sfzh") = 18) AS valid_sfzh
        FROM "ywdata"."zq_zfba_xyrxx"
        """
    )
    age_distribution = query_all(
        """
        SELECT age_bucket, COUNT(*) AS count
        FROM (
            SELECT CASE
                WHEN DATE_PART('year', AGE(CURRENT_DATE, TO_DATE(SUBSTR("xyrxx_sfzh", 7, 8), 'YYYYMMDD'))) < 14 THEN '<14'
                WHEN DATE_PART('year', AGE(CURRENT_DATE, TO_DATE(SUBSTR("xyrxx_sfzh", 7, 8), 'YYYYMMDD'))) < 16 THEN '14-15'
                WHEN DATE_PART('year', AGE(CURRENT_DATE, TO_DATE(SUBSTR("xyrxx_sfzh", 7, 8), 'YYYYMMDD'))) < 18 THEN '16-17'
                ELSE '>=18'
            END AS age_bucket
            FROM "ywdata"."zq_zfba_xyrxx"
            WHERE LENGTH("xyrxx_sfzh") = 18
              AND SUBSTR("xyrxx_sfzh", 7, 8) ~ '^[0-9]{8}$'
        ) t
        GROUP BY age_bucket
        ORDER BY age_bucket
        """
    )
    return {"counts": counts, "age_distribution": age_distribution}


def _school_probe() -> dict[str, Any]:
    counts = query_one(
        """
        SELECT COUNT(*) AS rows,
               COUNT(*) FILTER (WHERE yxx IS NOT NULL) AS with_yxx
        FROM "ywdata"."zq_zfba_wcnr_sfzxx"
        """
    )
    yxx_top10 = query_all(
        """
        SELECT yxx, COUNT(*) AS count
        FROM "ywdata"."zq_zfba_wcnr_sfzxx"
        WHERE yxx IS NOT NULL
        GROUP BY yxx
        ORDER BY count DESC
        LIMIT 10
        """
    )
    return {"counts": counts, "yxx_top10": yxx_top10}


def _legacy_qscxwcnr_probe() -> dict[str, Any]:
    exists = query_one(
        """
        SELECT 1 AS exists
        FROM information_schema.tables
        WHERE table_schema = 'ywdata'
          AND table_name = 'b_per_qscxwcnr'
        LIMIT 1
        """
    )
    table_exists = bool(exists)
    columns = []
    if table_exists:
        columns = query_all(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'ywdata'
              AND table_name = 'b_per_qscxwcnr'
            ORDER BY ordinal_position
            """
        )
    return {"exists": table_exists, "columns": [row.get("column_name") for row in columns]}


def collect_db_probes() -> dict[str, Any]:
    return {
        "wcnr_target_pool": _safe_db_probe("wcnr_target_pool", _target_pool_probe),
        "wcnr_score": _safe_db_probe("wcnr_score", _score_probe),
        "wcnr_alert": _safe_db_probe("wcnr_alert", _alert_probe),
        "wcnr_score_history": _safe_db_probe("wcnr_score_history", _score_history_probe),
        "wcnr_ryrl_gj": _safe_db_probe("wcnr_ryrl_gj", _trajectory_probe),
        "zq_zfba_ajxx": _safe_db_probe("zq_zfba_ajxx", _case_probe),
        "zq_zfba_xyrxx": _safe_db_probe("zq_zfba_xyrxx", _suspect_probe),
        "zq_zfba_wcnr_sfzxx": _safe_db_probe("zq_zfba_wcnr_sfzxx", _school_probe),
        "b_per_qscxwcnr": _safe_db_probe("b_per_qscxwcnr", _legacy_qscxwcnr_probe),
    }


def _payload_count_and_first(payload: Any) -> tuple[int | None, Any]:
    if isinstance(payload, dict):
        for key in ("items", "points", "results", "nodes", "tables", "endpoint_probes"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value), value[0] if value else None
        return (1, payload) if payload else (0, None)
    if isinstance(payload, list):
        return len(payload), payload[0] if payload else None
    if payload is None:
        return 0, None
    return 1, payload


def _probe_api_url(url: str) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
            status = getattr(response, "status", None) or getattr(response, "code", None)
        payload = json.loads(raw.decode("utf-8")) if raw else None
        count, first_item = _payload_count_and_first(payload)
        return {
            "url": url,
            "status": status,
            "items_or_points_count": count,
            "first_item": first_item,
            "raw_size_bytes": len(raw),
            "error": None,
        }
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        return {
            "url": url,
            "status": exc.code,
            "items_or_points_count": None,
            "first_item": None,
            "raw_size_bytes": len(raw),
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "url": url,
            "status": None,
            "items_or_points_count": None,
            "first_item": None,
            "raw_size_bytes": 0,
            "error": str(exc),
        }


def collect_api_probes(base_url: str, zjhm: str | None = None) -> list[dict[str, Any]]:
    root = (base_url or "http://127.0.0.1:5001").rstrip("/")
    paths = [
        "/api/health",
        "/api/dashboard/data-health",
        "/api/dashboard/summary",
        "/api/dashboard/distribution?dim=case_type",
        "/api/dashboard/distribution?dim=risk_level",
        "/api/dashboard/distribution?dim=area",
        "/api/dashboard/distribution?dim=age",
        "/api/dashboard/distribution?dim=gender",
        "/api/dashboard/trend?metric=cases&months=12",
        "/api/dashboard/trend?metric=persons&months=12",
        "/api/dashboard/trend?metric=score&months=12",
        "/api/dashboard/ranking?by=area",
        "/api/dashboard/heatmap?days=30",
        "/api/dashboard/alerts?limit=5",
    ]
    if zjhm:
        quoted = urllib.parse.quote(str(zjhm).strip(), safe="")
        paths.append(f"/api/graph/person/{quoted}?depth=1")
    return [_probe_api_url(root + path) for path in paths]


def build_probe(base_url: str, zjhm: str | None = None) -> dict[str, Any]:
    return {
        "meta": collect_meta(),
        "db_probes": collect_db_probes(),
        "api_probes": collect_api_probes(base_url, zjhm),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Rider 内网 dashboard/DB 诊断脚本")
    parser.add_argument("--base-url", default="http://127.0.0.1:5001", help="已部署服务的基础 URL")
    parser.add_argument("--zjhm", default="", help="可选：用于探测关系图谱接口的证件号码")
    parser.add_argument("--out", default="", help="输出 JSON 路径，默认 probe_<UTC时间戳>.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_path = Path(args.out or _default_out_path()).resolve()
    payload = build_probe(args.base_url, args.zjhm.strip() or None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"已生成 {out_path}，请发回")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
