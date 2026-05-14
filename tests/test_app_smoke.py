from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_app_factory_registers_expected_endpoints(app_module):
    flask_app = app_module.create_app()

    assert "healthz" in flask_app.view_functions
    assert "livez" in flask_app.view_functions
    assert "diagnostics.task_queue_diagnostics" in flask_app.view_functions
    assert "job.index" in flask_app.view_functions
    assert "upload.upload_start" in flask_app.view_functions
    assert "dispatch.dispatch_auth_status" in flask_app.view_functions
    assert "face.face_library_status" in flask_app.view_functions
    assert "train.dataset_list" in flask_app.view_functions
    assert "job.structured_run_list" in flask_app.view_functions
    assert "job.structured_detection_review_update" in flask_app.view_functions
    assert "job.structured_media_asset_list" in flask_app.view_functions
    assert "job.structured_media_asset_lineage" in flask_app.view_functions
    assert "train.dataset_import_structured_detections" in flask_app.view_functions
    assert "training_api.dataset_import_structured_detections" in flask_app.view_functions


def test_livez_returns_process_ok(client):
    response = client.get("/livez")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "service": "multi-rider"}


def test_healthz_returns_ok_payload(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_health_report",
        lambda: {
            "ok": True,
            "timestamp": 1710000000,
            "checks": {
                "sqlite": {"ok": True},
                "output_dir": {"ok": True},
                "models": {"ok": True},
                "task_queue": {"ok": True},
            },
        },
    )

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_healthz_returns_503_when_unhealthy(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_health_report",
        lambda: {
            "ok": False,
            "timestamp": 1710000000,
            "checks": {
                "sqlite": {"ok": False, "error": "db locked"},
                "output_dir": {"ok": True},
                "models": {"ok": True},
                "task_queue": {"ok": True},
            },
        },
    )

    response = client.get("/healthz")

    assert response.status_code == 503
    assert response.get_json()["checks"]["sqlite"]["ok"] is False


def test_task_queue_diagnostics_route_returns_mocked_snapshot(client, monkeypatch):
    import modules.diagnostics.routes as diagnostics_routes

    calls = []

    def fake_snapshot(**kwargs):
        calls.append(kwargs)
        return {
            "generated_ts": 1710000000,
            "filters": {"task_type": kwargs["task_type"], "status": kwargs["status"], "limit": 200},
            "stale_after_seconds": 3600,
            "totals": {"total": 1, "pending": 1, "running": 0, "completed": 0, "failed": 0, "stale_running": 0},
            "by_status": [{"status": "pending", "count": 1}],
            "by_type_status": [{"task_type": "upload", "status": "pending", "count": 1}],
            "tasks": [{"task_id": "task-1", "task_type": "upload", "status": "pending", "job_id": "job-1"}],
        }

    monkeypatch.setattr(diagnostics_routes, "get_task_queue_snapshot", fake_snapshot)
    monkeypatch.setattr(
        diagnostics_routes,
        "get_health_report",
        lambda: {"ok": True, "checks": {"task_queue": {"ok": True, "running_count": 0}}},
    )

    response = client.get("/diagnostics/task-queue?task_type=upload&status=pending&limit=999")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["totals"]["total"] == 1
    assert payload["health"]["task_queue"]["ok"] is True
    assert calls == [{"task_type": "upload", "status": "pending", "limit": "999"}]


def test_index_template_wires_task_queue_diagnostics_tab(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "tabBtnDiagnostics" in html
    assert "tabDiagnostics" in html
    assert "modules/diagnostics/task-queue.js" in html


def test_task_queue_diagnostics_template_has_read_only_controls():
    template = (REPO_ROOT / "templates" / "modules" / "diagnostics" / "_task_queue_tab.html").read_text(encoding="utf-8")
    script = (REPO_ROOT / "static" / "modules" / "diagnostics" / "task-queue.js").read_text(encoding="utf-8")

    assert "diagRefreshBtn" in template
    assert "diagRemediation" in template
    assert "diagTaskRows" in template
    assert "/diagnostics/task-queue" in script
    assert "worker.py" in script
    assert "reset_stale" not in template.lower()
    assert "delete" not in template.lower()


def test_header_primary_button_has_tab_specific_actions():
    template = (REPO_ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    script = (REPO_ROOT / "static" / "modules" / "detection" / "tasks.js").read_text(encoding="utf-8")

    assert "runTabPrimaryAction('Oracle')" in template
    assert "function runTabPrimaryAction(tab)" in script
    assert "submitFormById('uploadForm')" in script
    assert "submitFormById('trainRunForm')" in script
    assert "sendDispatchTasks()" in script
    assert "refreshTaskQueueDiagnostics()" in script


def test_history_detail_template_wires_structured_media_lineage():
    template = (REPO_ROOT / "templates" / "modules" / "detection" / "history" / "history_detail.html").read_text(encoding="utf-8")

    assert "lineageDrawer" in template
    assert "查看媒体链路" in template
    assert "/detection/api/structured/assets/" in template


def test_result_detail_drawer_wires_structured_media_lineage():
    template = (REPO_ROOT / "templates" / "modules" / "detection" / "_result_detail_drawer.html").read_text(encoding="utf-8")
    script = (REPO_ROOT / "static" / "modules" / "detection" / "results.js").read_text(encoding="utf-8")

    assert "resultDetailLineage" in template
    assert "loadResultLineage" in script
    assert "structured_lineage_url" in script


def test_file_routes_use_mocked_job_payload(client, monkeypatch, tmp_path):
    import modules.detection.file_routes as file_routes

    part1 = tmp_path / "part1.zip"
    part2 = tmp_path / "part2.zip"
    for path, text in ((part1, "first"), (part2, "second")):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("payload.txt", text)

    job = {
        "id": "job-1",
        "status": "done",
        "zip_path": "",
        "zip_parts": [
            {"name": "part1.zip", "path": str(part1)},
            {"name": "part2.zip", "path": str(part2)},
        ],
        "end_ts": 1710000000,
        "summary_text": "summary text",
        "owner_key": "owner-key",
        "owner_ip": "127.0.0.1",
    }

    monkeypatch.setattr(file_routes, "_resolve_job", lambda job_id: job)
    monkeypatch.setattr(file_routes, "get_request_owner", lambda request: ("owner-key", "127.0.0.1"))

    response = client.get("/download/job-1")
    assert response.status_code == 200
    assert "下载分片" in response.get_data(as_text=True)

    part_response = client.get("/download/job-1/part1.zip")
    assert part_response.status_code == 200
    assert part_response.mimetype == "application/zip"

    summary_response = client.get("/summary/job-1")
    assert summary_response.status_code == 200
    assert summary_response.get_data(as_text=True) == "summary text"


def test_upload_route_rejects_invalid_file_type(client):
    response = client.post(
        "/upload/start",
        data={"file": (BytesIO(b"hello"), "notes.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "不支持的文件类型" in response.get_json()["error"]


def test_job_routes_return_mocked_history(client, monkeypatch):
    import modules.detection.job_routes as job_routes

    monkeypatch.setattr(job_routes, "get_request_owner", lambda request: ("owner-key", "127.0.0.1"))
    monkeypatch.setattr(job_routes, "list_running_jobs", lambda owner_key, owner_ip: [])
    monkeypatch.setattr(
        job_routes,
        "list_saved_jobs",
        lambda owner_key, owner_ip, limit=50: [
            {
                "id": "job-1",
                "job_type": "oracle",
                "source_name": "demo",
                "source_type": "video",
                "start_ts": 1710000000,
                "end_ts": 1710000300,
                "status": "done",
                "kept": 1,
                "total": 1,
                "zip_parts": [{"path": "a.zip"}],
                "model_key": "general",
                "identity_summary": {"matched": 1},
            }
        ],
    )

    running_response = client.get("/jobs")
    assert running_response.get_json()["running_count"] == 0

    history_response = client.get("/history")
    history_payload = history_response.get_json()
    assert history_payload["jobs"][0]["detail_url"].endswith("/history-page/job-1")
    assert history_payload["jobs"][0]["download_url"].endswith("/download/job-1")


def test_job_routes_history_detail_exposes_structured_lineage_fields(client, monkeypatch):
    import modules.detection.job_routes as job_routes

    monkeypatch.setattr(
        job_routes,
        "get_saved_job",
        lambda job_id: {
            "id": job_id,
            "status": "done",
            "job_type": "upload",
            "source_type": "video",
            "source_name": "sample.mp4",
            "result_manifest_path": "C:/tmp/manifest.json",
            "identity_result_path": "C:/tmp/identity.json",
            "zip_parts": [],
            "identity_summary": {"recognized_asset_count": 1},
        },
    )
    monkeypatch.setattr(job_routes.os.path, "isfile", lambda path: True)
    monkeypatch.setattr(job_routes, "load_result_manifest", lambda path: {"items": [{"id": "0001.jpg"}]})
    monkeypatch.setattr(job_routes, "load_identity_report", lambda path: {"summary": {"recognized_asset_count": 1}, "items": []})
    monkeypatch.setattr(
        job_routes,
        "attach_identity_to_manifest_items",
        lambda manifest, identity_report: [
            {
                "id": "0001.jpg",
                "name": "0001.jpg",
                "origin_name": "frame_001.jpg",
                "size_bytes": 128,
                "structured_asset_id": "asset-frame-1",
                "identity": None,
            }
        ],
    )
    monkeypatch.setattr(job_routes, "_get_face_library_status", lambda: {"ready": True})

    response = client.get("/history/job-1")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["items"][0]["structured_asset_id"] == "asset-frame-1"
    assert payload["items"][0]["structured_lineage_url"].endswith("/detection/api/structured/assets/asset-frame-1/lineage")


def test_job_routes_return_mocked_structured_results(client, monkeypatch):
    import modules.detection.job_routes as job_routes

    run_calls = []
    detection_calls = []

    monkeypatch.setattr(
        job_routes.structured_repo,
        "list_yolo_runs",
        lambda limit=50, status=None: run_calls.append({"limit": limit, "status": status}) or [
            {
                "run_id": "run-1",
                "task_name": "oracle:oracle",
                "model_code": "general",
                "source_scope": '{"source_type":"oracle"}',
                "status": "success",
                "total_assets": 3,
                "processed_assets": 3,
                "detected_assets": 2,
                "detection_count": 4,
                "started_at": datetime(2026, 5, 13, 10, 0, 0),
                "finished_at": datetime(2026, 5, 13, 10, 1, 0),
            }
        ],
    )
    monkeypatch.setattr(
        job_routes.structured_repo,
        "get_yolo_run",
        lambda run_id: {
            "run_id": run_id,
            "task_name": "oracle:oracle",
            "model_code": "general",
            "source_scope": '{"source_type":"oracle"}',
            "status": "success",
            "total_assets": 3,
            "processed_assets": 3,
            "detected_assets": 2,
            "detection_count": 4,
            "started_at": datetime(2026, 5, 13, 10, 0, 0),
            "finished_at": datetime(2026, 5, 13, 10, 1, 0),
        },
    )
    monkeypatch.setattr(
        job_routes.structured_repo,
        "list_yolo_detections",
        lambda limit=100, **filters: detection_calls.append({"limit": limit, **filters}) or [
            {
                "detection_id": "det-1",
                "run_id": filters.get("run_id") or "run-1",
                "asset_id": "asset-1",
                "label_code": "person",
                "label_name": "person",
                "confidence": 0.91,
                "bbox_json": '{"x1":1,"y1":2,"x2":9,"y2":10}',
                "review_status": "pending",
                "source_system": filters.get("source_system") or "oracle",
                "media_uri": "https://example.com/a.jpg",
                "created_at": datetime(2026, 5, 13, 10, 0, 5),
            }
        ],
    )

    runs_response = client.get("/detection/api/structured/runs?limit=5&status=success")
    runs_payload = runs_response.get_json()
    assert runs_response.status_code == 200
    assert runs_payload["count"] == 1
    assert runs_payload["items"][0]["run_id"] == "run-1"
    assert runs_payload["items"][0]["source_scope"]["source_type"] == "oracle"
    assert run_calls == [{"limit": 5, "status": "success"}]

    run_response = client.get("/detection/api/structured/runs/run-1?detection_limit=2")
    run_payload = run_response.get_json()
    assert run_response.status_code == 200
    assert run_payload["run"]["run_id"] == "run-1"
    assert run_payload["detections"][0]["detection_id"] == "det-1"
    assert detection_calls[0]["limit"] == 2
    assert detection_calls[0]["run_id"] == "run-1"

    detections_response = client.get(
        "/detection/api/structured/detections?run_id=run-1&sfzh=320101199001010011&source_system=oracle&review_status=pending&limit=20"
    )
    detections_payload = detections_response.get_json()
    assert detections_response.status_code == 200
    assert detections_payload["items"][0]["bbox_json"]["x1"] == 1
    assert detection_calls[1]["limit"] == 20
    assert detection_calls[1]["sfzh"] == "320101199001010011"
    assert detection_calls[1]["source_system"] == "oracle"
    assert detection_calls[1]["review_status"] == "pending"


def test_job_routes_return_mocked_structured_media_assets(client, monkeypatch):
    import modules.detection.job_routes as job_routes

    asset_calls = []
    lineage_calls = []

    monkeypatch.setattr(
        job_routes.structured_repo,
        "list_media_assets",
        lambda limit=100, **filters: (asset_calls if filters.get("parent_asset_id") != "asset-parent" else lineage_calls).append({"limit": limit, **filters}) or [
            {
                "asset_id": filters.get("asset_id") or (filters.get("parent_asset_id") and "asset-child-1") or "asset-parent",
                "parent_asset_id": filters.get("parent_asset_id") or None,
                "media_type": "video" if not filters.get("parent_asset_id") else "frame",
                "media_uri": "C:/tmp/sample.mp4" if not filters.get("parent_asset_id") else "C:/tmp/frame_001.jpg",
                "detect_status": "success",
                "source_row_key": '{"frame_index":1}',
                "created_at": datetime(2026, 5, 13, 10, 0, 0),
                "child_count": 1 if not filters.get("parent_asset_id") else 0,
                "detection_count": 0,
            }
        ],
    )
    monkeypatch.setattr(
        job_routes.structured_repo,
        "get_media_asset",
        lambda asset_id: {
            "asset_id": asset_id,
            "parent_asset_id": "asset-root" if asset_id == "asset-parent" else None,
            "media_type": "video",
            "media_uri": f"C:/tmp/{asset_id}.mp4",
            "detect_status": "success",
            "source_row_key": '{"job_id":"run-1"}',
            "created_at": datetime(2026, 5, 13, 10, 0, 0),
            "child_count": 1,
            "detection_count": 0,
        },
    )

    assets_response = client.get(
        "/detection/api/structured/assets?parent_asset_id=asset-parent&media_type=frame&detect_status=success&limit=50"
    )
    assets_payload = assets_response.get_json()
    assert assets_response.status_code == 200
    assert assets_payload["count"] == 1
    assert assets_payload["items"][0]["asset_id"] == "asset-child-1"
    assert assets_payload["items"][0]["source_row_key"]["frame_index"] == 1
    assert asset_calls == []
    assert lineage_calls == [{"limit": 50, "asset_id": None, "parent_asset_id": "asset-parent", "source_system": None, "source_table": None, "media_type": "frame", "detect_status": "success"}]

    lineage_response = client.get("/detection/api/structured/assets/asset-parent/lineage?child_limit=10")
    lineage_payload = lineage_response.get_json()
    assert lineage_response.status_code == 200
    assert lineage_payload["asset"]["asset_id"] == "asset-parent"
    assert lineage_payload["parent"]["asset_id"] == "asset-root"
    assert lineage_payload["children"][0]["asset_id"] == "asset-child-1"


def test_job_routes_update_structured_detection_review(client, monkeypatch):
    import modules.detection.job_routes as job_routes

    sample_calls = []

    monkeypatch.setattr(
        job_routes.structured_repo,
        "update_yolo_detection_review",
        lambda detection_id, **payload: {
            "detection_id": detection_id,
            "review_status": payload["review_status"],
            "review_result": payload["review_result"],
            "reviewer_name": payload["reviewer_name"],
            "review_comment": payload["review_comment"],
            "reviewed_at": datetime(2026, 5, 13, 10, 2, 0),
        },
    )
    monkeypatch.setattr(
        job_routes.structured_repo,
        "sync_training_sample_from_detection_review",
        lambda detection_id: sample_calls.append(detection_id) or {
            "sample_id": "sample-1",
            "detection_id": detection_id,
            "sample_type": "positive",
        },
    )

    response = client.post(
        "/detection/api/structured/detections/det-1/review",
        json={
            "review_status": "confirmed",
            "review_result": "true_positive",
            "reviewer_name": "Alice",
            "review_comment": "looks good",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["item"]["detection_id"] == "det-1"
    assert payload["item"]["review_status"] == "confirmed"
    assert payload["item"]["review_result"] == "true_positive"
    assert payload["training_sample"]["sample_id"] == "sample-1"
    assert sample_calls == ["det-1"]


def test_job_routes_reject_invalid_structured_detection_review_status(client):
    response = client.post(
        "/detection/api/structured/detections/det-1/review",
        json={"review_status": "bad-status"},
    )

    assert response.status_code == 400
    assert "invalid review_status" in response.get_json()["error"]


def test_training_routes_import_structured_detections(client, monkeypatch):
    import modules.training.routes as train_routes

    monkeypatch.setattr(train_routes, "list_datasets", lambda limit=100: [])
    monkeypatch.setattr(train_routes, "attach_recent_assets", lambda items: items)
    monkeypatch.setattr(train_routes, "summarize_datasets", lambda items: {"dataset_count": len(items)})
    monkeypatch.setattr(
        train_routes,
        "get_structured_detections_by_ids",
        lambda ids: [
            {
                "detection_id": detection_id,
                "asset_id": f"asset-{index}",
                "run_id": "run-1",
                "media_uri": f"C:/tmp/{detection_id}.jpg",
                "label_name": "person",
                "label_code": "person",
                "bbox_x": 1,
                "bbox_y": 2,
                "bbox_w": 8,
                "bbox_h": 8,
                "confidence": 0.9,
            }
            for index, detection_id in enumerate(ids, start=1)
        ],
    )
    monkeypatch.setattr(
        train_routes,
        "import_structured_detections_to_dataset",
        lambda dataset_id, detections: {
            "dataset": {"id": dataset_id, "recent_assets": []},
            "imported": len(detections),
            "skipped": 0,
            "annotated": len(detections),
            "recent_assets": [],
        },
    )

    response = client.post(
        "/training/api/import-structured-detections",
        json={"dataset_id": "ds-1", "detection_ids": ["det-1", "det-2"]},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["imported"] == 2
    assert payload["annotated"] == 2
    assert payload["dataset_id"] == "ds-1"
    assert payload["detection_ids"] == ["det-1", "det-2"]


def test_training_routes_reject_invalid_structured_detection_import_payload(client):
    response = client.post(
        "/training/api/import-structured-detections",
        json={"dataset_id": "", "detection_ids": []},
    )

    assert response.status_code == 400
    assert "dataset_id is required" in response.get_json()["error"]


def test_dispatch_routes_return_mocked_payloads(client, monkeypatch):
    import modules.dispatch.routes as dispatch_routes

    queue_item = {
        "id": "queue-1",
        "source_job_id": "job-1",
        "source_asset_id": "asset-1",
        "source_job_type": "upload",
        "source_name": "upload task",
        "source_type": "video",
        "asset_name": "asset.jpg",
        "face_index": 0,
        "person_name": "Alice",
        "person_id_no": "320101199001010011",
        "person_phone": "13800000000",
        "similarity_score": 0.92,
        "illegal_type": "飙车炸街",
        "sssj_dm": "320000000000",
        "sssj_mc": "江苏省",
        "ssfj_dm": "320100000000",
        "ssfj_mc": "南京市",
        "zbpcs_dm": "320102",
        "zbpcs_mc": "鼓楼派出所",
        "dzmc": "示例地址",
        "rwdyid": "rw-1",
        "sjcsly": "source",
        "dispatch_status": "pending",
        "sms_status": "pending",
        "last_error": "",
        "draft_payload": {"rwdyid": "rw-1"},
        "recommended_payload": {"rwdyid": "rw-1"},
        "identity_payload": {},
        "sms_preview": "",
        "created_ts": 1,
        "updated_ts": 1,
    }

    monkeypatch.setattr(
        dispatch_routes,
        "get_dispatch_auth_status",
        lambda owner_key: {"authenticated": True, "status": "authenticated", "is_mock": True},
    )
    monkeypatch.setattr(dispatch_routes, "list_dispatch_queue_items", lambda owner_key, owner_ip, limit: [queue_item])
    monkeypatch.setattr(dispatch_routes, "list_dispatch_records", lambda owner_key, owner_ip, limit: [])
    monkeypatch.setattr(dispatch_routes, "list_dispatch_sms_records", lambda owner_key, owner_ip, limit: [])
    monkeypatch.setattr(dispatch_routes, "get_dispatch_queue_detail", lambda owner_key, owner_ip, queue_id: queue_item)
    monkeypatch.setattr(
        dispatch_routes,
        "preview_sms",
        lambda item, template="", mobile="", overrides=None: {"mobile": "13800000000", "content": "hello"},
    )

    auth_response = client.get("/dispatch/auth/status")
    assert auth_response.get_json()["auth"]["authenticated"] is True
    assert auth_response.get_json()["config"]["mock_mode"] is True

    queue_response = client.get("/dispatch/queue")
    queue_payload = queue_response.get_json()
    assert queue_payload["items"][0]["id"] == "queue-1"
    assert queue_payload["defaults"]["sms_mobile"] == ""

    preview_response = client.post("/dispatch/sms/preview", json={"queue_id": "queue-1"})
    assert preview_response.get_json()["preview"]["mobile"] == "13800000000"


def test_face_routes_return_mocked_payloads(client, monkeypatch):
    import modules.face.routes as face_routes

    monkeypatch.setattr(face_routes, "get_face_library_status", lambda: {"ready": True, "sql_enabled": False})
    monkeypatch.setattr(face_routes, "get_running_face_library_task", lambda: None)
    monkeypatch.setattr(
        face_routes,
        "list_persons",
        lambda page=1, page_size=12, keyword="": {"items": [{"id": "320101199001010011", "name": "Alice"}], "total": 1, "page": page, "page_size": page_size, "pages": 1},
    )

    status_response = client.get("/face/library/status")
    assert status_response.get_json()["library"]["ready"] is True

    persons_response = client.get("/face/library/persons?page=1&page_size=1&keyword=ali")
    assert persons_response.get_json()["items"][0]["name"] == "Alice"


def test_training_routes_return_mocked_payloads(client, monkeypatch):
    import modules.training.routes as train_routes

    monkeypatch.setattr(train_routes, "get_request_owner", lambda request: ("owner-key", "127.0.0.1"))
    monkeypatch.setattr(
        train_routes,
        "list_datasets",
        lambda limit=100: [
            {
                "id": "ds-1",
                "name": "demo dataset",
                "notes": "",
                "class_names": ["car"],
                "status": "draft",
                "image_count": 1,
                "labeled_count": 0,
                "reviewed_count": 0,
                "version_count": 0,
                "root_dir": "/tmp/ds-1",
                "created_ts": 1,
                "updated_ts": 1,
                "recent_assets": [],
            }
        ],
    )
    monkeypatch.setattr(train_routes, "attach_recent_assets", lambda items: items)
    monkeypatch.setattr(train_routes, "summarize_datasets", lambda items: {"dataset_count": len(items)})
    monkeypatch.setattr(
        train_routes,
        "list_train_job_snapshots",
        lambda owner_key, owner_ip, limit=20: [
            {
                "id": "train-1",
                "dataset_id": "ds-1",
                "dataset_name": "demo dataset",
                "status": "queued",
                "message": "",
                "base_model": "yolo26n.pt",
                "preset_key": "default",
                "epochs": 1,
                "imgsz": 640,
                "batch_size": 1,
                "confirmed_only": False,
                "run_dir": "/tmp/run",
                "log_path": "/tmp/run/train.log",
                "manifest_path": "/tmp/run/manifest.json",
                "artifact_dir": "/tmp/run/artifacts",
                "created_ts": 1,
                "start_ts": None,
                "end_ts": None,
            }
        ],
    )
    monkeypatch.setattr(
        train_routes,
        "list_managed_models",
        lambda: [
            {
                "name": "yolov8s-worldv2.pt",
                "display_name": "通用人车要素识别",
                "path": "/tmp/model.pt",
                "category": "production",
                "category_label": "在用模型",
                "lifecycle": "active",
                "lifecycle_label": "启用中",
                "usages": ["general_inference"],
                "usage_labels": ["通用巡检"],
                "note": "",
                "size_bytes": 0,
                "modified_ts": 1,
                "source_job_id": "",
                "dataset_id": "",
                "dataset_name": "",
                "base_model": "",
                "confirmed_only": False,
                "metrics": {},
                "metadata_path": "",
                "slot_refs": [],
                "slot_labels": [],
            }
        ],
    )
    monkeypatch.setattr(train_routes, "get_model_slot_views", lambda: [{"slot_key": "general", "label": "数据库巡检通用模型", "current_model": "", "current_path": "", "changed_ts": None, "history": [], "has_override": False}])
    monkeypatch.setattr(train_routes, "get_model_registry_options", lambda: [{"value": "general", "label": "general"}])

    datasets_response = client.get("/train/datasets")
    assert datasets_response.get_json()["summary"]["dataset_count"] == 1

    jobs_response = client.get("/train/jobs")
    assert jobs_response.get_json()["items"][0]["id"] == "train-1"

    models_response = client.get("/train/models")
    models_payload = models_response.get_json()
    assert models_payload["models"][0]["name"] == "yolov8s-worldv2.pt"
    assert models_payload["slots"][0]["slot_key"] == "general"
