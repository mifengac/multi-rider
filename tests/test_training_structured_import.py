from __future__ import annotations

import io

from PIL import Image


def _make_image_bytes(color: tuple[int, int, int] = (0, 255, 0)) -> bytes:
    image = Image.new("RGB", (32, 24), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def test_import_structured_detections_groups_by_asset_and_saves_annotations(monkeypatch, tmp_path):
    import modules.training.services.dataset_service as service

    dataset_root = tmp_path / "ds-1"
    (dataset_root / "images").mkdir(parents=True)
    dataset = {
        "id": "ds-1",
        "root_dir": str(dataset_root),
        "class_names": ["person", "vehicle"],
    }

    saved_assets = []
    saved_annotations = []

    monkeypatch.setattr(service, "_require_dataset", lambda dataset_id: dataset)
    monkeypatch.setattr(service, "_load_image_bytes_from_media_uri", lambda media_uri: _make_image_bytes())
    monkeypatch.setattr(service, "save_dataset_asset", lambda asset: saved_assets.append(dict(asset)))
    monkeypatch.setattr(
        service,
        "save_asset_annotation",
        lambda dataset_id, asset_id, boxes: saved_annotations.append(
            {"dataset_id": dataset_id, "asset_id": asset_id, "boxes": [dict(box) for box in boxes]}
        ),
    )
    monkeypatch.setattr(service, "_refresh_dataset_counters", lambda payload: payload)
    monkeypatch.setattr(service, "list_saved_dataset_assets", lambda dataset_id, limit=8: [])

    result = service.import_structured_detections_to_dataset(
        "ds-1",
        [
            {
                "detection_id": "det-1",
                "asset_id": "asset-1",
                "run_id": "run-1",
                "media_uri": "C:/tmp/asset-1.jpg",
                "label_name": "person",
                "label_code": "person",
                "bbox_x": 1,
                "bbox_y": 2,
                "bbox_w": 10,
                "bbox_h": 8,
                "confidence": 0.95,
            },
            {
                "detection_id": "det-2",
                "asset_id": "asset-1",
                "run_id": "run-1",
                "media_uri": "C:/tmp/asset-1.jpg",
                "label_name": "vehicle",
                "label_code": "vehicle",
                "bbox_x": 12,
                "bbox_y": 5,
                "bbox_w": 9,
                "bbox_h": 7,
                "confidence": 0.91,
            },
        ],
    )

    assert result["imported"] == 1
    assert result["skipped"] == 0
    assert result["annotated"] == 1
    assert len(saved_assets) == 1
    assert saved_assets[0]["source_type"] == "structured_detection"
    assert saved_assets[0]["source_asset_id"] == "asset-1"
    assert len(saved_annotations) == 1
    assert saved_annotations[0]["dataset_id"] == "ds-1"
    assert len(saved_annotations[0]["boxes"]) == 2
    assert saved_annotations[0]["boxes"][0]["class_index"] == 0
    assert saved_annotations[0]["boxes"][1]["class_index"] == 1