from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks.common import benchmark_id, elapsed_seconds, env_snapshot, now_perf, write_result
from shared.config.config import resolve_model_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a YOLO dataset with Ultralytics validation.")
    parser.add_argument("--data", required=True, help="dataset.yaml path.")
    parser.add_argument("--model-key", default="general")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.is_file():
        raise SystemExit(f"Dataset yaml not found: {data_path}")

    from ultralytics import YOLO

    model_path = resolve_model_path(args.model_key)
    start = now_perf()
    metrics = YOLO(model_path).val(data=str(data_path), imgsz=args.imgsz, conf=args.conf, verbose=False)
    elapsed = elapsed_seconds(start)
    box = getattr(metrics, "box", None)
    payload = {
        "benchmark_id": benchmark_id("yolo_eval"),
        "scenario": "yolo_eval",
        "environment": env_snapshot(),
        "input": {
            "dataset_yaml": str(data_path.resolve()),
        },
        "model": {
            "model_key": args.model_key,
            "model_path": model_path,
            "conf": args.conf,
            "imgsz": args.imgsz,
        },
        "metrics": {
            "elapsed_seconds": elapsed,
            "precision": float(getattr(box, "mp", 0.0) or 0.0) if box else 0.0,
            "recall": float(getattr(box, "mr", 0.0) or 0.0) if box else 0.0,
            "map50": float(getattr(box, "map50", 0.0) or 0.0) if box else 0.0,
            "map50_95": float(getattr(box, "map", 0.0) or 0.0) if box else 0.0,
        },
    }
    path = write_result(payload, args.output_dir or None)
    print(f"benchmark result written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

