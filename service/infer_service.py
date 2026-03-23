import os
import threading
from typing import Optional, Set

import requests
from PIL import Image

from config import MODEL_REGISTRY


ULTR_ERR = None
try:
    from ultralytics import YOLO
except Exception as exc:
    YOLO = None
    ULTR_ERR = str(exc)


_MODEL_CACHE: dict[str, object] = {}
_MODEL_LOCKS: dict[str, threading.Lock] = {}
_CACHE_LOCK = threading.Lock()

session = requests.Session()
session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/requests"}
)


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
