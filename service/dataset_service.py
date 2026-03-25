import io
import os
import re
import time
import zipfile
from uuid import uuid4

from PIL import Image

from config import DATASETS_DIR
from db.sqlite import count_dataset_assets
from db.sqlite import get_dataset as get_saved_dataset
from db.sqlite import list_dataset_assets as list_saved_dataset_assets
from db.sqlite import list_datasets as list_saved_datasets
from db.sqlite import save_dataset, save_dataset_asset


DATASET_SUBDIRS = ("images", "labels", "splits", "exports")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def _clean_dataset_name(value: str) -> str:
    name = " ".join((value or "").strip().split())
    if not name:
        raise ValueError("数据集名称不能为空")
    if len(name) > 80:
        raise ValueError("数据集名称过长")
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
        raise ValueError("至少填写一个类别")
    if len(items) > 50:
        raise ValueError("类别数量过多")
    return items


def _clean_notes(value: str) -> str:
    notes = str(value or "").strip()
    if len(notes) > 500:
        raise ValueError("备注内容过长")
    return notes


def _new_dataset_id() -> str:
    return "ds_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]


def _ensure_dataset_dirs(root_dir: str) -> None:
    os.makedirs(root_dir, exist_ok=False)
    for subdir in DATASET_SUBDIRS:
        os.makedirs(os.path.join(root_dir, subdir), exist_ok=True)


def _require_dataset(dataset_id: str) -> dict:
    dataset = get_saved_dataset(dataset_id)
    if dataset is None:
        raise LookupError("数据集不存在")
    return dataset


def _safe_filename(name: str, fallback: str) -> str:
    base = os.path.basename((name or "").strip()) or fallback
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return cleaned or fallback


def _unique_asset_filename(directory: str, origin_name: str, used_names: set[str]) -> str:
    safe_name = _safe_filename(origin_name, "image.jpg")
    root, ext = os.path.splitext(safe_name)
    ext = ext.lower()
    if ext not in IMAGE_EXTS:
        ext = ".jpg"
    root = root or "image"

    candidate = root + ext
    index = 1
    while candidate.lower() in used_names or os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{root}_{index}{ext}"
        index += 1

    used_names.add(candidate.lower())
    return candidate


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


def list_dataset_assets(dataset_id: str, limit: int = 100) -> list[dict]:
    _require_dataset(dataset_id)
    return list_saved_dataset_assets(dataset_id, limit=limit)


def attach_recent_assets(items: list[dict], limit_per_dataset: int = 4) -> list[dict]:
    output: list[dict] = []
    for item in items:
        dataset = dict(item)
        dataset["recent_assets"] = list_saved_dataset_assets(dataset["id"], limit=limit_per_dataset)
        output.append(dataset)
    return output


def import_zip_to_dataset(dataset_id: str, upload_file) -> dict:
    dataset = _require_dataset(dataset_id)
    if upload_file is None or not getattr(upload_file, "filename", ""):
        raise ValueError("请选择 ZIP 文件")

    upload_name = os.path.basename(upload_file.filename or "")
    if os.path.splitext(upload_name)[1].lower() != ".zip":
        raise ValueError("仅支持 ZIP 文件")

    images_dir = os.path.join(dataset["root_dir"], "images")
    os.makedirs(images_dir, exist_ok=True)
    used_names = {entry.lower() for entry in os.listdir(images_dir)}

    try:
        upload_file.stream.seek(0)
    except Exception:
        pass

    imported = 0
    skipped = 0
    now = int(time.time())

    try:
        with zipfile.ZipFile(upload_file.stream) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue

                ext = os.path.splitext(member.filename)[1].lower()
                if ext not in IMAGE_EXTS:
                    skipped += 1
                    continue

                try:
                    payload = archive.read(member)
                except Exception:
                    skipped += 1
                    continue

                try:
                    with Image.open(io.BytesIO(payload)) as image:
                        image.load()
                        width, height = image.size
                except Exception:
                    skipped += 1
                    continue

                origin_name = os.path.basename(member.filename) or f"image_{imported + skipped + 1}{ext}"
                stored_name = _unique_asset_filename(images_dir, origin_name, used_names)
                full_path = os.path.join(images_dir, stored_name)
                with open(full_path, "wb") as fh:
                    fh.write(payload)

                save_dataset_asset(
                    {
                        "id": uuid4().hex,
                        "dataset_id": dataset_id,
                        "filename": stored_name,
                        "origin_name": origin_name,
                        "source_type": "zip",
                        "file_path": os.path.abspath(full_path),
                        "width": width,
                        "height": height,
                        "size_bytes": len(payload),
                        "created_ts": now + imported,
                    }
                )
                imported += 1
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"ZIP 文件无法读取: {exc}") from exc

    if imported == 0:
        raise ValueError("ZIP 中没有可导入的有效图片")

    dataset["image_count"] = count_dataset_assets(dataset_id)
    dataset["updated_ts"] = int(time.time())
    save_dataset(dataset)

    return {
        "dataset": dataset,
        "imported": imported,
        "skipped": skipped,
        "upload_name": upload_name,
        "recent_assets": list_saved_dataset_assets(dataset_id, limit=8),
    }


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
