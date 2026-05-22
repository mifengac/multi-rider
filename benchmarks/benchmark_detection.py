from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from benchmarks.common import (
    benchmark_id,
    elapsed_seconds,
    env_snapshot,
    files_per_minute,
    image_files,
    now_perf,
    write_result,
)
from shared.inference.infer_service import predict_image_boxes_batch


def _chunks(items: list[Path], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark YOLO image detection throughput.")
    parser.add_argument("--image-dir", required=True, help="Directory containing test images.")
    parser.add_argument("--model-key", default="general")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--prompt-classes", default="", help="Comma separated text prompts for YOLO-World models.")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    paths = image_files(args.image_dir, limit=args.limit)
    if not paths:
        raise SystemExit(f"No images found under {args.image_dir}")

    prompt_classes = [item.strip() for item in args.prompt_classes.split(",") if item.strip()] or None
    total_detections = 0
    detected_images = 0
    failed_images = 0
    start = now_perf()
    for batch_paths in _chunks(paths, max(1, args.batch_size)):
        images = []
        valid_paths = []
        for path in batch_paths:
            try:
                with Image.open(path) as img:
                    images.append(img.convert("RGB"))
                valid_paths.append(path)
            except Exception:
                failed_images += 1
        if not images:
            continue
        outputs = predict_image_boxes_batch(
            images,
            model_key=args.model_key,
            conf_thresh=args.conf,
            imgsz=args.imgsz,
            prompt_classes=prompt_classes,
        )
        for boxes in outputs:
            total_detections += len(boxes)
            if boxes:
                detected_images += 1

    elapsed = elapsed_seconds(start)
    payload = {
        "benchmark_id": benchmark_id("detection_images"),
        "scenario": "detection_images",
        "environment": env_snapshot(),
        "input": {
            "image_dir": str(Path(args.image_dir).resolve()),
            "image_count": len(paths),
            "limit": args.limit,
        },
        "model": {
            "model_key": args.model_key,
            "conf": args.conf,
            "imgsz": args.imgsz,
            "batch_size": args.batch_size,
            "prompt_classes": prompt_classes or [],
        },
        "metrics": {
            "total_items": len(paths),
            "failed_images": failed_images,
            "detected_images": detected_images,
            "total_detections": total_detections,
            "elapsed_seconds": elapsed,
            "items_per_minute": files_per_minute(len(paths), elapsed),
        },
    }
    path = write_result(payload, args.output_dir or None)
    print(f"benchmark result written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

