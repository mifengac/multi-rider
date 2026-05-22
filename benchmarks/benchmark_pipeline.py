from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from benchmarks.common import benchmark_id, elapsed_seconds, env_snapshot, image_files, now_perf, write_result
from modules.dispatch.services.queue_service import build_dispatch_payload
from shared.inference.infer_service import predict_image_boxes_batch


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark a minimal detection -> dispatch payload pipeline.")
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--model-key", default="general")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    paths = image_files(args.image_dir, limit=args.limit)
    if not paths:
        raise SystemExit(f"No images found under {args.image_dir}")

    images = []
    for path in paths:
        with Image.open(path) as img:
            images.append(img.convert("RGB"))

    detection_start = now_perf()
    detections = predict_image_boxes_batch(images, args.model_key, args.conf, args.imgsz)
    detection_elapsed = elapsed_seconds(detection_start)

    dispatch_start = now_perf()
    payload_count = 0
    for index, boxes in enumerate(detections):
        if not boxes:
            continue
        build_dispatch_payload(
            {
                "person_name": "测试对象",
                "person_id_no": "000000000000000000",
                "person_phone": "",
                "illegal_type": boxes[0].get("class_name") or "AI 命中线索",
                "source_name": Path(paths[index]).name,
                "sssj_dm": "",
                "sssj_mc": "",
            }
        )
        payload_count += 1
    dispatch_elapsed = elapsed_seconds(dispatch_start)

    payload = {
        "benchmark_id": benchmark_id("pipeline"),
        "scenario": "pipeline",
        "environment": env_snapshot(),
        "input": {
            "image_dir": str(Path(args.image_dir).resolve()),
            "image_count": len(paths),
        },
        "model": {
            "model_key": args.model_key,
            "conf": args.conf,
            "imgsz": args.imgsz,
        },
        "metrics": {
            "total_items": len(paths),
            "detected_items": sum(1 for item in detections if item),
            "dispatch_payloads": payload_count,
            "detection_seconds": detection_elapsed,
            "dispatch_payload_seconds": dispatch_elapsed,
            "pipeline_seconds": round(detection_elapsed + dispatch_elapsed, 4),
        },
    }
    path = write_result(payload, args.output_dir or None)
    print(f"benchmark result written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

