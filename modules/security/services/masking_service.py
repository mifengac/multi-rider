from __future__ import annotations

from typing import Any


SENSITIVE_KEYS = {
    "sfzh",
    "id_number",
    "person_id_no",
    "zjhm",
    "phone",
    "person_phone",
    "mobile",
    "lxdh",
    "address",
    "dzmc",
    "hjd",
    "jzdz",
}


def mask_id_number(value: str) -> str:
    raw = str(value or "").strip()
    if len(raw) < 8:
        return "*" * len(raw) if raw else ""
    return raw[:4] + "*" * max(4, len(raw) - 8) + raw[-4:]


def mask_phone(value: str) -> str:
    raw = str(value or "").strip()
    if len(raw) < 7:
        return "*" * len(raw) if raw else ""
    return raw[:3] + "****" + raw[-4:]


def mask_address(value: str) -> str:
    raw = str(value or "").strip()
    if len(raw) <= 6:
        return raw[:1] + "***" if raw else ""
    return raw[:6] + "***"


def mask_value(key: str, value: Any) -> Any:
    if value is None:
        return value
    lower = str(key or "").lower()
    if lower in {"sfzh", "id_number", "person_id_no", "zjhm"}:
        return mask_id_number(str(value))
    if lower in {"phone", "person_phone", "mobile", "lxdh"}:
        return mask_phone(str(value))
    if lower in {"address", "dzmc", "hjd", "jzdz"}:
        return mask_address(str(value))
    return value


def mask_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: mask_value(key, mask_payload(value)) if str(key).lower() in SENSITIVE_KEYS else mask_payload(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [mask_payload(item) for item in payload]
    return payload

