from __future__ import annotations

import argparse
from pathlib import Path

import cv2
from PIL import Image

from benchmarks.common import benchmark_id, elapsed_seconds, env_snapshot, files_per_minute, now_perf, write_result
from shared.inference.infer_service import predict_image_boxes_batch


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark video frame sampling and YOLO detection.")
    parser.add_argument("--video", required=True, help="Video file path.")
    parser.add_argument("--model-key", default="general")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--frame-interval", type=int, default=5)
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.is_file():
        raise SystemExit(f"Video not found: {video_path}")
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise SystemExit(f"Cannot open video: {video_path}")

    sampled = 0
    total_frames_seen = 0
    detected_frames = 0
    total_detections = 0
    batch: list[Image.Image] = []
    start = now_perf()

    def flush_batch() -> None:
        nonlocal batch, detected_frames, total_detections
        if not batch:
            return
        outputs = predict_image_boxes_batch(batch, args.model_key, args.conf, args.imgsz)
        for boxes in outputs:
            total_detections += len(boxes)
            if boxes:
                detected_frames += 1
        batch = []

    while True:
        ok, frame = capture.read()
        if not ok:
            break
        total_frames_seen += 1
        if total_frames_seen % max(1, args.frame_interval) != 0:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        batch.append(Image.fromarray(rgb))
        sampled += 1
        if len(batch) >= max(1, args.batch_size):
            flush_batch()
        if args.max_frames and sampled >= args.max_frames:
            break
    flush_batch()
    capture.release()
    elapsed = elapsed_seconds(start)
    payload = {
        "benchmark_id": benchmark_id("detection_video"),
        "scenario": "detection_video",
        "environment": env_snapshot(),
        "input": {
            "video": str(video_path.resolve()),
            "frame_interval": args.frame_interval,
            "total_frames_seen": total_frames_seen,
            "sampled_frames": sampled,
        },
        "model": {
            "model_key": args.model_key,
            "conf": args.conf,
            "imgsz": args.imgsz,
            "batch_size": args.batch_size,
        },
        "metrics": {
            "total_items": sampled,
            "detected_frames": detected_frames,
            "total_detections": total_detections,
            "elapsed_seconds": elapsed,
            "items_per_minute": files_per_minute(sampled, elapsed),
        },
    }
    path = write_result(payload, args.output_dir or None)
    print(f"benchmark result written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

