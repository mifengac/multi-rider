from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class SmokeResult:
    name: str
    ok: bool
    detail: str


def check_backend_status() -> SmokeResult:
    from modules.graph.services.etl_service import get_graph_backend_status

    try:
        payload = get_graph_backend_status()
    except Exception as exc:
        return SmokeResult("graph backend status", False, str(exc))

    ok = bool(payload.get("kingbase", {}).get("ok") and payload.get("neo4j", {}).get("ok"))
    return SmokeResult("graph backend status", ok, json.dumps(payload, ensure_ascii=False))


def check_graph_sync(limit: int, theft_only: bool) -> SmokeResult:
    from modules.graph.services.etl_service import run_graph_sync

    try:
        payload = run_graph_sync(limit=limit, theft_only=theft_only)
    except Exception as exc:
        return SmokeResult("graph sync", False, str(exc))
    return SmokeResult("graph sync", bool(payload.get("ok")), json.dumps(payload, ensure_ascii=False))


def check_graph_detect(min_size: int) -> SmokeResult:
    from modules.graph.services.algo_service import detect_gangs

    try:
        payload = detect_gangs(min_size=min_size)
    except Exception as exc:
        return SmokeResult("graph detect", False, str(exc))
    return SmokeResult("graph detect", bool(payload.get("ok")), json.dumps(payload, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run graph-specific smoke checks for multi-rider.")
    parser.add_argument("--sync-limit", type=int, default=10, help="Sample row limit used for direct graph sync.")
    parser.add_argument("--min-size", type=int, default=2, help="Minimum community size used for gang detection.")
    parser.add_argument("--skip-sync", action="store_true", help="Skip direct graph sync smoke check.")
    parser.add_argument("--skip-detect", action="store_true", help="Skip direct gang detection smoke check.")
    parser.add_argument("--all-cases", action="store_true", help="Disable theft-only filter during direct sync.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results: list[SmokeResult] = [check_backend_status()]
    if not args.skip_sync:
        results.append(check_graph_sync(limit=max(1, args.sync_limit), theft_only=not args.all_cases))
    if not args.skip_detect:
        results.append(check_graph_detect(min_size=max(2, args.min_size)))

    for result in results:
        prefix = "[OK]" if result.ok else "[FAIL]"
        print(f"{prefix} {result.name}: {result.detail}")
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())