from __future__ import annotations


def test_model_meta_path_uses_registered_model_path_case_insensitively(monkeypatch, tmp_path):
    import modules.training.services.model_registry_service as service

    model_path = tmp_path / "model" / "yolo" / "production" / "yolov8s-worldv2.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"placeholder")

    monkeypatch.setattr(service, "list_upload_model_paths", lambda: {"yolov8s-worldv2.pt": str(model_path)})

    assert service._model_meta_path("YOLOV8S-WORLDV2.PT") == str(model_path.with_suffix(".meta.json"))


def test_model_slot_views_resolve_registered_path_case_insensitively(monkeypatch, tmp_path):
    import modules.training.services.model_registry_service as service

    model_path = tmp_path / "model" / "yolo" / "production" / "yolov8s-worldv2.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"placeholder")

    monkeypatch.setattr(service, "list_upload_model_paths", lambda: {"yolov8s-worldv2.pt": str(model_path)})
    monkeypatch.setattr(service, "_load_slot_registry", lambda: {"slots": {}, "updated_ts": None})
    monkeypatch.setattr(
        service,
        "_current_model_name_for_slot",
        lambda slot_key: "YOLOV8S-WORLDV2.PT" if slot_key == "general" else "",
    )
    monkeypatch.setattr(service, "get_deployment_slot_model_name", lambda slot_key: "")

    general_slot = next(item for item in service.get_model_slot_views() if item["slot_key"] == "general")

    assert general_slot["current_model"] == "YOLOV8S-WORLDV2.PT"
    assert general_slot["current_path"] == str(model_path)
