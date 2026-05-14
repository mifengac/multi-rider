from __future__ import annotations

import hashlib
import re
from typing import Any

from shared.config.config import RUIZHI_MAX_INPUT_CHARS
from modules.security.services.masking_service import mask_payload


ID_RE = re.compile(r"(?<!\d)(\d{6})(\d{8})(\d{3}[\dXx])(?!\d)")
PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d)(\d{4})(\d{4})(?!\d)")


def digest_text(text: str) -> str:
    return hashlib.sha1(str(text or "").encode("utf-8")).hexdigest()


def redact_text(text: str) -> str:
    raw = str(text or "")
    raw = ID_RE.sub(lambda m: m.group(1)[:4] + "*" * 10 + m.group(3)[-2:], raw)
    raw = PHONE_RE.sub(lambda m: m.group(1) + "****" + m.group(3), raw)
    if len(raw) > RUIZHI_MAX_INPUT_CHARS:
        raw = raw[:RUIZHI_MAX_INPUT_CHARS] + "\n[内容过长，已截断]"
    return raw


def sanitize_payload(value: Any) -> Any:
    masked = mask_payload(value)
    if isinstance(masked, str):
        return redact_text(masked)
    if isinstance(masked, dict):
        return {key: sanitize_payload(item) for key, item in masked.items()}
    if isinstance(masked, list):
        return [sanitize_payload(item) for item in masked]
    return masked


def sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = []
    for item in messages or []:
        role = str(item.get("role") or "user").strip() or "user"
        content = item.get("content", "")
        sanitized.append({"role": role, "content": sanitize_payload(content)})
    return sanitized

