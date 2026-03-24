import os
import threading
from typing import Optional, Set

import requests
from PIL import Image

from config import MOBILECLIP_TS_PATH, MOBILECLIP2_TS_PATH, MODEL_REGISTRY, logger


ULTR_ERR = None
try:
    from ultralytics import YOLO
    from ultralytics.nn.modules import block as ultralytics_block
    from ultralytics.nn.modules import head as ultralytics_head
    from ultralytics.utils import downloads as ultralytics_downloads
except Exception as exc:
    YOLO = None
    ultralytics_block = None
    ultralytics_head = None
    ultralytics_downloads = None
    ULTR_ERR = str(exc)


_MODEL_CACHE: dict[str, object] = {}
_MODEL_LOCKS: dict[str, threading.Lock] = {}
_CACHE_LOCK = threading.Lock()

session = requests.Session()
session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/requests"}
)

_DOWNLOAD_PATCHED = False


def _patch_ultralytics_head_compat() -> None:
    """Provide aliases for legacy class names embedded in older model files."""
    if ultralytics_head is None:
        return

    alias_map = {
        "YOLOESegment26": ("Segment26", "YOLOESegment", "Segment"),
        "YOLOSegment26": ("Segment26", "Segment"),
        "YOLOEDetect26": ("YOLOEDetect", "Detect"),
        "YOLODetect26": ("Detect",),
    }

    for missing_name, candidates in alias_map.items():
        if hasattr(ultralytics_head, missing_name):
            continue
        for candidate in candidates:
            target = getattr(ultralytics_head, candidate, None)
            if target is not None:
                setattr(ultralytics_head, missing_name, target)
                logger.info(
                    "Applied ultralytics compatibility alias: %s -> %s",
                    missing_name,
                    candidate,
                )
                break


def _patch_ultralytics_block_compat() -> None:
    """Provide aliases for legacy block names embedded in older model files."""
    if ultralytics_block is None:
        return

    alias_map = {
        "Proto26": ("Proto",),
    }

    for missing_name, candidates in alias_map.items():
        if hasattr(ultralytics_block, missing_name):
            continue
        for candidate in candidates:
            target = getattr(ultralytics_block, candidate, None)
            if target is not None:
                setattr(ultralytics_block, missing_name, target)
                logger.info(
                    "Applied ultralytics compatibility alias: %s -> %s",
                    missing_name,
                    candidate,
                )
                break


def _patch_ultralytics_asset_downloads() -> None:
    """Resolve MobileCLIP TorchScript assets from local files before downloading."""
    global _DOWNLOAD_PATCHED
    if ultralytics_downloads is None or _DOWNLOAD_PATCHED:
        return

    original_attempt_download_asset = ultralytics_downloads.attempt_download_asset
    local_assets = {
        "mobileclip_blt.ts": MOBILECLIP_TS_PATH,
        "mobileclip2_b.ts": MOBILECLIP2_TS_PATH,
    }

    def _attempt_download_asset_offline_first(file, *args, **kwargs):
        asset_name = os.path.basename(str(file))
        local_path = local_assets.get(asset_name)
        if local_path and os.path.isfile(local_path):
            logger.info("Using local text-model asset: %s", local_path)
            return local_path
        return original_attempt_download_asset(file, *args, **kwargs)

    ultralytics_downloads.attempt_download_asset = _attempt_download_asset_offline_first
    _DOWNLOAD_PATCHED = True


def _normalize_names(names) -> list[str]:
    if isinstance(names, dict):
        return [str(names[index]) for index in sorted(names)]
    if isinstance(names, (list, tuple)):
        return [str(item) for item in names]
    return []


def _ensure_general_prompt_state(model, prompt_classes: list[str] | None) -> None:
    default_classes = tuple(getattr(model, "_codex_default_classes", ()))
    if not default_classes:
        default_classes = tuple(_normalize_names(getattr(model, "names", [])))
        model._codex_default_classes = default_classes

    desired_classes = tuple(prompt_classes or default_classes)
    if not desired_classes:
        return

    active_classes = tuple(getattr(model, "_codex_active_classes", ()))
    if active_classes != desired_classes:
        model.set_classes(list(desired_classes))
        model._codex_active_classes = desired_classes


def get_model(model_key: str):
    if model_key not in MODEL_REGISTRY:
        raise ValueError(f"unsupported model key: {model_key}")

    with _CACHE_LOCK:
        model = _MODEL_CACHE.get(model_key)
        if model is not None:
            return model

        if YOLO is None:
            raise RuntimeError(
                f"ultralytics import failed: {ULTR_ERR or 'not installed or missing dependencies'}"
            )

        _patch_ultralytics_asset_downloads()
        _patch_ultralytics_head_compat()
        _patch_ultralytics_block_compat()

        model_path = MODEL_REGISTRY[model_key]
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"model file not found: {model_path}")

        model = YOLO(model_path)
        if model_key == "general":
            default_classes = tuple(_normalize_names(getattr(model, "names", [])))
            model._codex_default_classes = default_classes
            model._codex_active_classes = default_classes

        _MODEL_CACHE[model_key] = model
        _MODEL_LOCKS.setdefault(model_key, threading.Lock())
        return model


def download_image_with_status(
    url: str, timeout=(6, 15)
) -> tuple[bytes | None, int | None, str | None]:
    try:
        resp = session.get(url, timeout=timeout, stream=True)
        code = resp.status_code
        content_type = resp.headers.get("Content-Type") if hasattr(resp, "headers") else None
        if 200 <= code < 300:
            return resp.content, code, content_type
        return None, code, content_type
    except requests.HTTPError as exc:
        try:
            return None, exc.response.status_code if exc.response is not None else None, None
        except Exception:
            return None, None, None
    except Exception:
        return None, None, None


def _predict_batch(
    images: list[Image.Image],
    model,
    conf_thresh: float,
    allowed_classes: Optional[Set[int]],
    imgsz: int,
    model_key: str,
    prompt_classes: list[str] | None = None,
) -> list[bool]:
    model_lock = _MODEL_LOCKS.setdefault(model_key, threading.Lock())
    with model_lock:
        if model_key == "general":
            _ensure_general_prompt_state(model, prompt_classes)

        results = model.predict(images, conf=min(conf_thresh, 0.25), imgsz=imgsz, verbose=False)

    output: list[bool] = []
    for result in results:
        try:
            boxes = result.boxes
            if boxes is None or boxes.conf is None:
                output.append(False)
                continue

            conf_list = boxes.conf.tolist()
            if allowed_classes is not None and hasattr(boxes, "cls") and boxes.cls is not None:
                cls_list = [int(item) for item in boxes.cls.tolist()]
                keep = any(
                    float(conf) >= conf_thresh and cls_id in allowed_classes
                    for conf, cls_id in zip(conf_list, cls_list)
                )
            else:
                keep = any(float(conf) >= conf_thresh for conf in conf_list)
            output.append(keep)
        except Exception:
            output.append(False)
    return output
