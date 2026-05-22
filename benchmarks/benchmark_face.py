from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks.common import benchmark_id, elapsed_seconds, env_snapshot, files_per_minute, image_files, now_perf, write_result
from modules.face.services.library_service import identify_image_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark face identify throughput.")
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    paths = image_files(args.image_dir, limit=args.limit)
    if not paths:
        raise SystemExit(f"No images found under {args.image_dir}")

    matched = 0
    no_face = 0
    errors = 0
    start = now_perf()
    for path in paths:
        try:
            result = identify_image_path(str(path), top_k=args.top_k)
            if result.get("status") == "matched":
                matched += 1
            elif result.get("status") == "no_face":
                no_face += 1
        except Exception:
            errors += 1
    elapsed = elapsed_seconds(start)
    payload = {
        "benchmark_id": benchmark_id("face_identify"),
        "scenario": "face_identify",
        "environment": env_snapshot(),
        "input": {
            "image_dir": str(Path(args.image_dir).resolve()),
            "image_count": len(paths),
            "top_k": args.top_k,
        },
        "metrics": {
            "total_items": len(paths),
            "matched": matched,
            "no_face": no_face,
            "errors": errors,
            "elapsed_seconds": elapsed,
            "items_per_minute": files_per_minute(len(paths), elapsed),
        },
    }
    path = write_result(payload, args.output_dir or None)
    print(f"benchmark result written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

