import os

from flask import Blueprint, jsonify, request, send_file, url_for

from config import logger
from service.dataset_service import (
    attach_recent_assets,
    create_dataset,
    import_zip_to_dataset,
    list_dataset_assets,
    list_datasets,
    summarize_datasets,
)


train_bp = Blueprint("train", __name__, url_prefix="/train")


def _serialize_asset(dataset_id: str, item: dict) -> dict:
    return {
        "id": item.get("id"),
        "filename": item.get("filename"),
        "origin_name": item.get("origin_name"),
        "source_type": item.get("source_type"),
        "width": item.get("width", 0),
        "height": item.get("height", 0),
        "size_bytes": item.get("size_bytes", 0),
        "asset_url": url_for("train.dataset_asset_file", dataset_id=dataset_id, asset_id=item.get("id")),
    }


def _serialize_dataset(item: dict) -> dict:
    dataset = {key: value for key, value in item.items() if key != "recent_assets"}
    dataset["recent_assets"] = [
        _serialize_asset(dataset["id"], asset)
        for asset in (item.get("recent_assets") or [])
    ]
    return dataset


def _datasets_payload() -> dict:
    items = attach_recent_assets(list_datasets())
    return {
        "ok": True,
        "items": [_serialize_dataset(item) for item in items],
        "summary": summarize_datasets(items),
    }


@train_bp.get("/datasets")
def dataset_list():
    return jsonify(_datasets_payload())


@train_bp.post("/datasets")
def dataset_create():
    payload = request.get_json(silent=True) or request.form or {}
    name = (payload.get("name", "") or "").strip()
    class_names = payload.get("class_names", "")
    notes = (payload.get("notes", "") or "").strip()

    try:
        dataset = create_dataset(name, class_names, notes)
        response = _datasets_payload()
        response["message"] = "数据集已创建"
        response["dataset_id"] = dataset["id"]
        return jsonify(response), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("failed to create dataset: %s", exc)
        return jsonify({"ok": False, "error": "创建数据集失败"}), 500


@train_bp.post("/datasets/<dataset_id>/import-zip")
def dataset_import_zip(dataset_id: str):
    upload_file = request.files.get("file")
    try:
        result = import_zip_to_dataset(dataset_id, upload_file)
        response = _datasets_payload()
        response.update(
            {
                "message": f"已导入 {result['imported']} 张图片，跳过 {result['skipped']} 项",
                "imported": result["imported"],
                "skipped": result["skipped"],
                "upload_name": result["upload_name"],
                "dataset_id": dataset_id,
            }
        )
        return jsonify(response)
    except LookupError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("failed to import zip into dataset %s: %s", dataset_id, exc)
        return jsonify({"ok": False, "error": "ZIP 导入失败"}), 500


@train_bp.get("/datasets/<dataset_id>/assets")
def dataset_asset_list(dataset_id: str):
    try:
        items = list_dataset_assets(dataset_id, limit=200)
    except LookupError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    return jsonify({"ok": True, "items": [_serialize_asset(dataset_id, item) for item in items]})


@train_bp.get("/datasets/<dataset_id>/assets/<asset_id>")
def dataset_asset_file(dataset_id: str, asset_id: str):
    try:
        items = list_dataset_assets(dataset_id, limit=5000)
    except LookupError:
        return "dataset not found", 404

    safe_asset_id = os.path.basename(asset_id)
    for item in items:
        if item.get("id") == safe_asset_id:
            path = item.get("file_path")
            if path and os.path.isfile(path):
                return send_file(path)
            break
    return "asset not found", 404
