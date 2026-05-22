from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def runtime_benchmark_dir(output_dir: str | None = None) -> Path:
    target = Path(output_dir) if output_dir else PROJECT_ROOT / "runtime" / "benchmarks"
    target.mkdir(parents=True, exist_ok=True)
    return target


def benchmark_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def image_files(root: str, limit: int = 0) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    paths = [
        path
        for path in Path(root).rglob("*")
        if path.is_file() and path.suffix.lower() in exts
    ]
    paths.sort(key=lambda p: str(p).lower())
    if limit and limit > 0:
        return paths[:limit]
    return paths


def write_result(payload: dict[str, Any], output_dir: str | None = None) -> Path:
    target_dir = runtime_benchmark_dir(output_dir)
    result_id = payload.get("benchmark_id") or benchmark_id("bench")
    path = target_dir / f"{result_id}.json"
    payload.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return path


def now_perf() -> float:
    return time.perf_counter()


def elapsed_seconds(start: float) -> float:
    return round(time.perf_counter() - start, 4)


def files_per_minute(total: int, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    return round(float(total) / seconds * 60.0, 2)


def env_snapshot() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "cwd": os.getcwd(),
        "project_root": str(PROJECT_ROOT),
    }

