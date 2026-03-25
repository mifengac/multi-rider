from flask import Blueprint, jsonify, request

from config import logger
from service.dataset_service import create_dataset, list_datasets, summarize_datasets


train_bp = Blueprint("train", __name__, url_prefix="/train")


@train_bp.get("/datasets")
def dataset_list():
    items = list_datasets()
    return jsonify({"ok": True, "items": items, "summary": summarize_datasets(items)})


@train_bp.post("/datasets")
def dataset_create():
    payload = request.get_json(silent=True) or request.form or {}
    name = (payload.get("name", "") or "").strip()
    class_names = payload.get("class_names", "")
    notes = (payload.get("notes", "") or "").strip()

    try:
        dataset = create_dataset(name, class_names, notes)
        items = list_datasets()
        return (
            jsonify(
                {
                    "ok": True,
                    "dataset": dataset,
                    "items": items,
                    "summary": summarize_datasets(items),
                }
            ),
            201,
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("failed to create dataset: %s", exc)
        return jsonify({"ok": False, "error": "failed to create dataset"}), 500
