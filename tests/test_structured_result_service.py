from __future__ import annotations

import io
from pathlib import Path

from PIL import Image


def _make_image_bytes(color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    image = Image.new("RGB", (16, 16), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def test_build_structured_yolo_context_seeds_model_and_labels(monkeypatch, tmp_path):
    import modules.detection.services.structured_result_service as service

    calls: dict[str, list] = {
        "model_versions": [],
        "labels": [],
        "runs": [],
    }

    monkeypatch.setattr(service.repo, "tables_ready", lambda: True)
    monkeypatch.setattr(service.repo, "upsert_model_version", lambda record: calls["model_versions"].append(dict(record)) or "mv-test")
    monkeypatch.setattr(service.repo, "upsert_behavior_label", lambda record: calls["labels"].append(dict(record)) or record.get("label_code") or record.get("label_name"))
    monkeypatch.setattr(service.repo, "upsert_yolo_run", lambda record: calls["runs"].append(dict(record)) or record.get("run_id"))

    context = service.build_structured_yolo_context(
        {"id": "run-1", "job_type": "upload", "total": 2, "model_key": "yolo26s"},
        source_system="upload",
        source_table="local_upload",
        source_type="zip",
        model_key="yolo26s",
        model_name="YOLO 26S",
        model_path=str(tmp_path / "model.pt"),
        label_candidates=["person", "vehicle"],
        result_dir=str(tmp_path / "result"),
        materialize_local_inputs=True,
        source_scope={"job_id": "run-1"},
        scenario_code="general",
    )

    assert context.enabled is True
    assert context.run_id == "run-1"
    assert context.model_version_id == "mv-test"
    assert len(calls["model_versions"]) == 1
    assert calls["labels"] == [
        {"label_name": "person", "label_category": "other", "scenario_code": "general"},
        {"label_name": "vehicle", "label_category": "other", "scenario_code": "general"},
    ]
    assert len(calls["runs"]) == 1
    assert calls["runs"][0]["total_assets"] == 2
    assert calls["runs"][0]["status"] == "running"


def test_persist_structured_yolo_batch_materializes_and_writes_rows(monkeypatch, tmp_path):
    import modules.detection.services.structured_result_service as service

    media_records: list[dict] = []
    label_records: list[dict] = []
    detection_records: list[dict] = []
    run_records: list[dict] = []

    monkeypatch.setattr(service.repo, "upsert_media_asset", lambda record: media_records.append(dict(record)) or record.get("asset_id"))
    monkeypatch.setattr(service.repo, "upsert_behavior_label", lambda record: label_records.append(dict(record)) or record.get("label_code") or record.get("label_name"))
    monkeypatch.setattr(service.repo, "upsert_yolo_detections", lambda records: detection_records.extend(dict(record) for record in records) or len(records))
    monkeypatch.setattr(service.repo, "upsert_yolo_run", lambda record: run_records.append(dict(record)) or record.get("run_id"))

    context = service.StructuredYoloContext(
        enabled=True,
        run_id="run-2",
        job_id="run-2",
        job_type="upload",
        source_system="upload",
        source_table="local_upload",
        source_type="zip",
        source_scope={"job_id": "run-2"},
        model_key="yolo26s",
        model_name="YOLO 26S",
        model_path=str(tmp_path / "model.pt"),
        model_version_id="mv-test",
        task_name="upload:zip",
        result_dir=str(tmp_path / "result"),
        materialize_local_inputs=True,
        source_material_dir=str(tmp_path / "result" / "structured_inputs"),
        total_assets=1,
    )

    batch_items = [
        {
            "name": "demo.jpg",
            "payload_bytes": _make_image_bytes(),
            "source_pk": "run-2:demo.jpg",
            "shot_time": "2026-05-13 10:00:00",
            "media_type": "image",
            "uri_type": "file_path",
        }
    ]
    batch_boxes = [
        [
            {
                "class_index": 0,
                "class_name": "person",
                "confidence": 0.91,
                "x1": 1.0,
                "y1": 2.0,
                "x2": 9.0,
                "y2": 10.0,
            }
        ]
    ]

    summary = service.persist_structured_yolo_batch(
        context,
        batch_items,
        batch_boxes,
        conf_thresh=0.25,
    )

    assert summary == {"processed_assets": 1, "detected_assets": 1, "detection_count": 1}
    assert len(media_records) == 2
    assert media_records[0]["detect_status"] == "processing"
    assert media_records[1]["detect_status"] == "success"
    assert media_records[1]["media_uri"]
    assert Path(media_records[1]["media_uri"]).is_file()
    assert len(label_records) == 1
    assert label_records[0]["label_name"] == "person"
    assert len(detection_records) == 1
    assert detection_records[0]["run_id"] == "run-2"
    assert detection_records[0]["label_name"] == "person"
    assert len(run_records) == 1
    assert run_records[0]["processed_assets"] == 1
    assert run_records[0]["detected_assets"] == 1
    assert run_records[0]["detection_count"] == 1


def test_seed_parent_video_asset_and_finalize_updates_status(monkeypatch, tmp_path):
    import modules.detection.services.structured_result_service as service

    media_records: list[dict] = []
    run_records: list[dict] = []

    monkeypatch.setattr(service.repo, "upsert_media_asset", lambda record: media_records.append(dict(record)) or record.get("asset_id"))
    monkeypatch.setattr(service.repo, "upsert_yolo_run", lambda record: run_records.append(dict(record)) or record.get("run_id"))

    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video-demo")

    context = service.StructuredYoloContext(
        enabled=True,
        run_id="run-video-1",
        job_id="run-video-1",
        job_type="upload",
        source_system="upload",
        source_table="local_upload",
        source_type="video",
        source_scope={"job_id": "run-video-1"},
        model_key="yolo26s",
        model_name="YOLO 26S",
        model_path=str(tmp_path / "model.pt"),
        model_version_id="mv-test",
        task_name="upload:video",
    )

    asset_id = service.seed_parent_video_asset(context, str(video_path), source_name="sample.mp4")
    service.finalize_structured_yolo_run(context, status="success")

    assert asset_id
    assert context.parent_asset_id == asset_id
    assert len(media_records) == 2
    assert media_records[0]["asset_id"] == asset_id
    assert media_records[0]["media_type"] == "video"
    assert media_records[0]["detect_status"] == "processing"
    assert media_records[1]["asset_id"] == asset_id
    assert media_records[1]["detect_status"] == "success"
    assert len(run_records) == 1
    assert run_records[0]["status"] == "success"


def test_persist_structured_yolo_batch_keeps_parent_asset_id_for_frames(monkeypatch, tmp_path):
    import modules.detection.services.structured_result_service as service

    media_records: list[dict] = []
    run_records: list[dict] = []

    monkeypatch.setattr(service.repo, "upsert_media_asset", lambda record: media_records.append(dict(record)) or record.get("asset_id"))
    monkeypatch.setattr(service.repo, "upsert_yolo_run", lambda record: run_records.append(dict(record)) or record.get("run_id"))

    context = service.StructuredYoloContext(
        enabled=True,
        run_id="run-frame-1",
        job_id="run-frame-1",
        job_type="upload",
        source_system="upload",
        source_table="local_upload",
        source_type="video",
        source_scope={"job_id": "run-frame-1"},
        model_key="yolo26s",
        model_name="YOLO 26S",
        model_path=str(tmp_path / "model.pt"),
        model_version_id="mv-test",
        task_name="upload:video",
        result_dir=str(tmp_path / "result"),
        materialize_local_inputs=True,
        source_material_dir=str(tmp_path / "result" / "structured_inputs"),
        total_assets=1,
        parent_asset_id="asset-parent-video",
    )

    summary = service.persist_structured_yolo_batch(
        context,
        [
            {
                "name": "frame_000001.jpg",
                "payload_bytes": _make_image_bytes(),
                "source_pk": "sample.mp4:1",
                "source_row_key": {"video_path": "sample.mp4", "frame_index": 1},
                "media_type": "frame",
                "uri_type": "file_path",
            }
        ],
        [[]],
        conf_thresh=0.25,
    )

    assert summary == {"processed_assets": 1, "detected_assets": 0, "detection_count": 0}
    assert len(media_records) == 2
    assert media_records[0]["parent_asset_id"] == "asset-parent-video"
    assert media_records[1]["parent_asset_id"] == "asset-parent-video"
    assert len(run_records) == 1
    assert run_records[0]["processed_assets"] == 1
