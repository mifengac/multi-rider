from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import quote

import requests

from shared.config.config import (
    RUIZHI_API_KEY,
    RUIZHI_AUDIO_MODEL,
    RUIZHI_BASE_URL,
    RUIZHI_CHAT_MODEL,
    RUIZHI_EMBEDDING_MODEL,
    RUIZHI_ENABLED,
    RUIZHI_PROJECT,
    RUIZHI_PROJECT_HEADER,
    RUIZHI_RERANK_MODEL,
    RUIZHI_TIMEOUT_SECONDS,
    RUIZHI_VERIFY_SSL,
)
from modules.ruizhi.services.prompt_guard import digest_text
from modules.ruizhi.services.store import save_call_log


class RuizhiNotConfigured(RuntimeError):
    pass


def get_ruizhi_config(mask_key: bool = True) -> dict[str, Any]:
    api_key = RUIZHI_API_KEY or ""
    return {
        "enabled": bool(RUIZHI_ENABLED),
        "configured": bool(RUIZHI_ENABLED and api_key),
        "base_url": RUIZHI_BASE_URL,
        "api_key": (api_key[:6] + "..." + api_key[-4:]) if mask_key and len(api_key) > 12 else (bool(api_key) if mask_key else api_key),
        "project": RUIZHI_PROJECT,
        "project_header": RUIZHI_PROJECT_HEADER,
        "verify_ssl": RUIZHI_VERIFY_SSL,
        "timeout_seconds": RUIZHI_TIMEOUT_SECONDS,
    }


def ensure_configured() -> None:
    if not RUIZHI_ENABLED:
        raise RuizhiNotConfigured("锐智 AI 服务未启用，请配置 RUIZHI_ENABLED=true")
    if not RUIZHI_API_KEY:
        raise RuizhiNotConfigured("锐智 AI API Key 未配置，请配置 RUIZHI_API_KEY")


def _headers(content_type: str = "application/json") -> dict[str, str]:
    ensure_configured()
    headers = {"Authorization": f"Bearer {RUIZHI_API_KEY}"}
    if content_type:
        headers["Content-Type"] = content_type
    if RUIZHI_PROJECT and RUIZHI_PROJECT_HEADER:
        headers[RUIZHI_PROJECT_HEADER] = RUIZHI_PROJECT
    return headers


def _operator_payload(operator: dict[str, Any] | None) -> dict[str, str]:
    operator = operator or {}
    return {
        "operator_id": str(operator.get("user_id") or ""),
        "operator_name": str(operator.get("display_name") or operator.get("username") or ""),
    }


def _request(
    method: str,
    path: str,
    *,
    module_code: str,
    operation: str,
    model_name: str = "",
    operator: dict[str, Any] | None = None,
    json_body: Any = None,
    files: Any = None,
    data: Any = None,
    content_type: str = "application/json",
    expected_binary: bool = False,
) -> dict[str, Any]:
    ensure_configured()
    url = RUIZHI_BASE_URL + path
    start = time.perf_counter()
    status_code = 0
    success = False
    error_msg = ""
    response_payload: Any = None
    try:
        headers = _headers("" if files else content_type)
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json_body,
            files=files,
            data=data,
            timeout=RUIZHI_TIMEOUT_SECONDS,
            verify=RUIZHI_VERIFY_SSL,
        )
        status_code = resp.status_code
        success = 200 <= resp.status_code < 300
        if expected_binary:
            response_payload = {
                "content_type": resp.headers.get("Content-Type", ""),
                "bytes": len(resp.content or b""),
                "content": resp.content,
            }
        else:
            try:
                response_payload = resp.json()
            except Exception:
                response_payload = {"text": resp.text}
        if not success:
            error_msg = str(response_payload)[:1000]
    except Exception as exc:
        error_msg = str(exc)
        response_payload = {"error": error_msg}
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    digest_source = json.dumps(json_body if json_body is not None else data or {}, ensure_ascii=False, default=str)
    response_digest_source = (
        f"binary:{response_payload.get('bytes')}" if isinstance(response_payload, dict) and response_payload.get("content") is not None
        else json.dumps(response_payload, ensure_ascii=False, default=str)
    )
    save_call_log(
        {
            "module_code": module_code,
            "operation": operation,
            "model_name": model_name,
            "request_digest": digest_text(digest_source),
            "response_digest": digest_text(response_digest_source),
            "status_code": status_code,
            "success": success,
            "elapsed_ms": elapsed_ms,
            "error_msg": error_msg,
            **_operator_payload(operator),
        }
    )
    if not success:
        return {"ok": False, "status_code": status_code, "error": error_msg or "ruizhi request failed", "data": response_payload}
    return {"ok": True, "status_code": status_code, "data": response_payload, "elapsed_ms": elapsed_ms}


def list_models(operator: dict[str, Any] | None = None) -> dict[str, Any]:
    return _request("GET", "/models", module_code="models", operation="models.list", operator=operator)


def chat_completions(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    operator: dict[str, Any] | None = None,
    stream: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_name = model or RUIZHI_CHAT_MODEL
    payload = {"model": model_name, "messages": messages, "stream": bool(stream)}
    if extra:
        payload.update(extra)
    return _request(
        "POST",
        "/chat/completions",
        module_code="chat",
        operation="chat.completions",
        model_name=model_name,
        operator=operator,
        json_body=payload,
    )


def kb_chat(
    messages: list[dict[str, Any]],
    kb_names: list[str],
    *,
    model: str | None = None,
    operator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    full_messages = list(messages or [])
    for kb_name in kb_names:
        if kb_name:
            full_messages.append({"role": "run", "content": "@" + kb_name})
    return chat_completions(full_messages, model=model, operator=operator)


def create_embedding(
    text: str,
    *,
    model: str | None = None,
    dimensions: int = 1024,
    operator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_name = model or RUIZHI_EMBEDDING_MODEL
    return _request(
        "POST",
        "/embeddings",
        module_code="embedding",
        operation="embeddings.create",
        model_name=model_name,
        operator=operator,
        json_body={"model": model_name, "input": text, "dimensions": dimensions, "encoding_format": "float"},
    )


def rerank(
    query: str,
    documents: list[str],
    *,
    model: str | None = None,
    top_k: int | None = None,
    operator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_name = model or RUIZHI_RERANK_MODEL
    payload: dict[str, Any] = {"model": model_name, "query": query, "documents": documents}
    if top_k:
        payload["top_k"] = top_k
    return _request(
        "POST",
        "/rerank",
        module_code="rerank",
        operation="rerank",
        model_name=model_name,
        operator=operator,
        json_body=payload,
    )


def list_kbs(operator: dict[str, Any] | None = None) -> dict[str, Any]:
    return _request("GET", "/kbs", module_code="kb", operation="kbs.list", operator=operator)


def create_kb(payload: dict[str, Any], operator: dict[str, Any] | None = None) -> dict[str, Any]:
    return _request("POST", "/kbs", module_code="kb", operation="kbs.create", operator=operator, json_body=payload)


def get_kb(kb_name: str, operator: dict[str, Any] | None = None) -> dict[str, Any]:
    return _request("GET", f"/kbs/{quote(kb_name)}", module_code="kb", operation="kbs.retrieve", operator=operator)


def add_files_to_kb(kb_name: str, file_ids: list[str], callback: str = "", operator: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"file_ids": file_ids}
    if callback:
        payload["callback"] = callback
    return _request("POST", f"/kbs/{quote(kb_name)}/files", module_code="kb", operation="kbs.files.add", operator=operator, json_body=payload)


def upload_file(file_storage, purpose: str = "kbs", operator: dict[str, Any] | None = None) -> dict[str, Any]:
    files = {"file": (file_storage.filename, file_storage.stream, file_storage.mimetype or "application/octet-stream")}
    return _request(
        "POST",
        "/files",
        module_code="files",
        operation="files.create",
        operator=operator,
        files=files,
        data={"purpose": purpose},
    )


def ocr_paddle(file_storage, form: dict[str, Any], operator: dict[str, Any] | None = None) -> dict[str, Any]:
    files = {"image": (file_storage.filename, file_storage.stream, file_storage.mimetype or "application/octet-stream")}
    data = {
        "use_angle_cls": str(form.get("use_angle_cls", "true")).lower(),
        "lang": form.get("lang", "ch"),
        "det_db_thresh": form.get("det_db_thresh", "0.3"),
        "det_db_box_thresh": form.get("det_db_box_thresh", "0.5"),
        "det_db_unclip_ratio": form.get("det_db_unclip_ratio", "1.6"),
    }
    return _request("POST", "/tools/ocr/paddle", module_code="ocr", operation="ocr.paddle", operator=operator, files=files, data=data)


def ocr_deepseek(file_storage, form: dict[str, Any], operator: dict[str, Any] | None = None) -> dict[str, Any]:
    files = {"image": (file_storage.filename, file_storage.stream, file_storage.mimetype or "application/octet-stream")}
    data = {
        "task_type": form.get("task_type", "free_ocr"),
        "resolution": form.get("resolution", "base"),
    }
    return _request("POST", "/tools/ocr/deepseek", module_code="ocr", operation="ocr.deepseek", operator=operator, files=files, data=data)


def asr_transcribe(file_storage, *, language: str = "zh", model: str = "", operator: dict[str, Any] | None = None) -> dict[str, Any]:
    model_name = model or RUIZHI_AUDIO_MODEL
    files = {"file": (file_storage.filename, file_storage.stream, file_storage.mimetype or "application/octet-stream")}
    return _request(
        "POST",
        "/audio/transcriptions",
        module_code="audio",
        operation="audio.transcriptions",
        model_name=model_name,
        operator=operator,
        files=files,
        data={"model": model_name, "language": language},
    )


def tts_speech(
    text: str,
    *,
    model: str = "",
    voice: str = "female",
    speed: float = 1.0,
    operator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_name = model or RUIZHI_AUDIO_MODEL
    return _request(
        "POST",
        "/audio/speech",
        module_code="audio",
        operation="audio.speech",
        model_name=model_name,
        operator=operator,
        json_body={"model": model_name, "input": text, "voice": voice, "response_format": "wav", "speed": speed},
        expected_binary=True,
    )
