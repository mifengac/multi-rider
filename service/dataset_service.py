import os
import re
import time
from uuid import uuid4

from config import DATASETS_DIR
from db.sqlite import list_datasets as list_saved_datasets
from db.sqlite import save_dataset


DATASET_SUBDIRS = ("images", "labels", "splits", "exports")


def _clean_dataset_name(value: str) -> str:
    name = " ".join((value or "").strip().split())
    if not name:
        raise ValueError("dataset name is required")
    if len(name) > 80:
        raise ValueError("dataset name is too long")
    return name


def _parse_class_names(value) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[,;\n\r]+", str(value or ""))

    items: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        item = " ".join(str(raw_item or "").strip().split())
        if not item:
            continue
        normalized = item.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(item)

    if not items:
        raise ValueError("at least one class is required")
    if len(items) > 50:
        raise ValueError("too many classes")
    return items


def _clean_notes(value: str) -> str:
    notes = str(value or "").strip()
    if len(notes) > 500:
        raise ValueError("notes are too long")
    return notes


def _new_dataset_id() -> str:
    return "ds_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]


def _ensure_dataset_dirs(root_dir: str) -> None:
    os.makedirs(root_dir, exist_ok=False)
    for subdir in DATASET_SUBDIRS:
        os.makedirs(os.path.join(root_dir, subdir), exist_ok=True)


def create_dataset(name: str, class_names, notes: str = "") -> dict:
    dataset_name = _clean_dataset_name(name)
    dataset_classes = _parse_class_names(class_names)
    dataset_notes = _clean_notes(notes)
    dataset_id = _new_dataset_id()
    root_dir = os.path.join(DATASETS_DIR, dataset_id)
    now = int(time.time())

    _ensure_dataset_dirs(root_dir)

    dataset = {
        "id": dataset_id,
        "name": dataset_name,
        "notes": dataset_notes,
        "class_names": dataset_classes,
        "status": "draft",
        "image_count": 0,
        "labeled_count": 0,
        "reviewed_count": 0,
        "version_count": 0,
        "root_dir": root_dir,
        "created_ts": now,
        "updated_ts": now,
    }
    save_dataset(dataset)
    return dataset


def list_datasets(limit: int = 100) -> list[dict]:
    return list_saved_datasets(limit=limit)


def summarize_datasets(items: list[dict]) -> dict[str, int]:
    summary = {
        "dataset_count": len(items),
        "image_count": 0,
        "labeled_count": 0,
        "reviewed_count": 0,
        "version_count": 0,
    }
    for item in items:
        summary["image_count"] += int(item.get("image_count") or 0)
        summary["labeled_count"] += int(item.get("labeled_count") or 0)
        summary["reviewed_count"] += int(item.get("reviewed_count") or 0)
        summary["version_count"] += int(item.get("version_count") or 0)
    return summary
