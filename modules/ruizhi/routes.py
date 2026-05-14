from __future__ import annotations

import base64

from flask import Blueprint, jsonify, render_template, request

from shared.config.config import (
    RUIZHI_AUDIO_MODEL,
    RUIZHI_CHAT_MODEL,
    RUIZHI_EMBEDDING_MODEL,
    RUIZHI_RERANK_MODEL,
)
from modules.ruizhi.services import client as rz_client
from modules.ruizhi.services.chat_service import run_chat
from modules.ruizhi.services.prompt_guard import sanitize_payload
from modules.ruizhi.services.report_service import generate_report
from modules.ruizhi.services.store import (
    get_session,
    list_call_logs,
    list_kb_mappings,
    list_messages,
    list_sessions,
    save_kb_file,
    upsert_kb_mapping,
)
from modules.security.services.audit_service import current_user_from_request


ruizhi_bp = Blueprint("ruizhi", __name__, url_prefix="/ruizhi")


def _operator() -> dict:
    return current_user_from_request(request)


def _not_configured_response(exc: Exception):
    return jsonify({"ok": False, "configured": False, "error": str(exc)}), 400


@ruizhi_bp.get("/")
def ruizhi_page():
    return render_template("ruizhi/index.html")


@ruizhi_bp.get("/api/status")
def ruizhi_status():
    config = rz_client.get_ruizhi_config(mask_key=True)
    return jsonify(
        {
            "ok": True,
            "status": "ready" if config["configured"] else ("disabled" if not config["enabled"] else "missing_api_key"),
            "config": config,
            "defaults": {
                "chat_model": RUIZHI_CHAT_MODEL,
                "embedding_model": RUIZHI_EMBEDDING_MODEL,
                "rerank_model": RUIZHI_RERANK_MODEL,
                "audio_model": RUIZHI_AUDIO_MODEL,
            },
        }
    )


@ruizhi_bp.get("/api/models")
def ruizhi_models():
    try:
        result = rz_client.list_models(operator=_operator())
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.post("/api/chat")
def ruizhi_chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "message is required"}), 400
    try:
        result = run_chat(
            message=message,
            scenario_code=str(payload.get("scenario_code") or "general"),
            session_id=str(payload.get("session_id") or ""),
            context=payload.get("context") if isinstance(payload.get("context"), dict) else {},
            kb_names=[str(item).strip() for item in (payload.get("kb_names") or []) if str(item).strip()],
            model=str(payload.get("model") or "") or None,
            operator=_operator(),
        )
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.post("/api/chat/kb")
def ruizhi_kb_chat():
    payload = request.get_json(silent=True) or {}
    kb_names = [str(item).strip() for item in (payload.get("kb_names") or []) if str(item).strip()]
    if not kb_names:
        return jsonify({"ok": False, "error": "kb_names is required"}), 400
    payload["kb_names"] = kb_names
    request_payload = dict(payload)
    try:
        result = run_chat(
            message=str(request_payload.get("message") or "").strip(),
            scenario_code=str(request_payload.get("scenario_code") or "general"),
            session_id=str(request_payload.get("session_id") or ""),
            context=request_payload.get("context") if isinstance(request_payload.get("context"), dict) else {},
            kb_names=kb_names,
            model=str(request_payload.get("model") or "") or None,
            operator=_operator(),
        )
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.get("/api/sessions")
def ruizhi_sessions():
    return jsonify({"ok": True, "items": list_sessions(limit=int(request.args.get("limit") or 50))})


@ruizhi_bp.get("/api/sessions/<session_id>")
def ruizhi_session_detail(session_id: str):
    session = get_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "session not found"}), 404
    return jsonify({"ok": True, "session": session, "messages": list_messages(session_id)})


@ruizhi_bp.get("/api/kbs")
def ruizhi_kbs():
    local_items = list_kb_mappings()
    remote = None
    remote_error = ""
    try:
        if rz_client.get_ruizhi_config(mask_key=False)["configured"]:
            remote = rz_client.list_kbs(operator=_operator())
    except Exception as exc:
        remote_error = str(exc)
    return jsonify({"ok": True, "local_items": local_items, "remote": remote, "remote_error": remote_error})


@ruizhi_bp.post("/api/kbs")
def ruizhi_create_kb():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or payload.get("kb_name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    split_config = payload.get("split_config") if isinstance(payload.get("split_config"), dict) else {
        "split_type": 1,
        "chunk_max_len": 512,
        "chunk_overlap_len": 50,
        "embedding_threshold": 0.5,
        "zh_title_enhance": True,
    }
    request_body = {
        "name": name,
        "description": payload.get("description") or name,
        "split_config": split_config,
    }
    try:
        result = rz_client.create_kb(request_body, operator=_operator())
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    if result.get("ok"):
        upsert_kb_mapping(
            {
                "kb_name": name,
                "display_name": payload.get("display_name") or name,
                "description": payload.get("description") or "",
                "split_config": split_config,
                "created_by": _operator().get("username", ""),
            }
        )
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.post("/api/kbs/<kb_name>/files")
def ruizhi_add_kb_file(kb_name: str):
    file_item = request.files.get("file")
    if not file_item:
        return jsonify({"ok": False, "error": "file is required"}), 400
    try:
        upload_result = rz_client.upload_file(file_item, purpose=request.form.get("purpose", "kbs"), operator=_operator())
        if not upload_result.get("ok"):
            return jsonify(upload_result), 502
        file_payload = upload_result.get("data") or {}
        file_id = file_payload.get("id")
        if not file_id:
            return jsonify({"ok": False, "error": "upload succeeded but file id missing", "upload": file_payload}), 502
        add_result = rz_client.add_files_to_kb(kb_name, [file_id], callback=request.form.get("callback", ""), operator=_operator())
        save_kb_file(
            {
                "kb_name": kb_name,
                "file_id": file_id,
                "filename": file_payload.get("filename") or file_item.filename,
                "purpose": file_payload.get("purpose") or request.form.get("purpose", "kbs"),
                "bytes": file_payload.get("bytes") or 0,
                "parse_status": "accepted" if add_result.get("status_code") == 202 else ("submitted" if add_result.get("ok") else "failed"),
            }
        )
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify({"ok": bool(add_result.get("ok")), "upload": upload_result, "association": add_result}), (200 if add_result.get("ok") else 502)


@ruizhi_bp.post("/api/embeddings")
def ruizhi_embeddings():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("input") or payload.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "input is required"}), 400
    try:
        result = rz_client.create_embedding(
            str(sanitize_payload(text)),
            model=str(payload.get("model") or "") or None,
            dimensions=int(payload.get("dimensions") or 1024),
            operator=_operator(),
        )
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.post("/api/rerank")
def ruizhi_rerank():
    payload = request.get_json(silent=True) or {}
    query = str(payload.get("query") or "").strip()
    documents = payload.get("documents") or []
    if not query or not isinstance(documents, list) or not documents:
        return jsonify({"ok": False, "error": "query and documents are required"}), 400
    try:
        result = rz_client.rerank(
            str(sanitize_payload(query)),
            [str(sanitize_payload(item)) for item in documents],
            model=str(payload.get("model") or "") or None,
            top_k=int(payload.get("top_k") or 0) or None,
            operator=_operator(),
        )
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.post("/api/ocr")
def ruizhi_ocr():
    file_item = request.files.get("image") or request.files.get("file")
    if not file_item:
        return jsonify({"ok": False, "error": "image is required"}), 400
    engine = (request.form.get("engine") or "paddle").strip().lower()
    try:
        result = rz_client.ocr_deepseek(file_item, request.form, operator=_operator()) if engine == "deepseek" else rz_client.ocr_paddle(file_item, request.form, operator=_operator())
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.post("/api/audio/asr")
def ruizhi_asr():
    file_item = request.files.get("file") or request.files.get("audio")
    if not file_item:
        return jsonify({"ok": False, "error": "audio file is required"}), 400
    try:
        result = rz_client.asr_transcribe(
            file_item,
            language=request.form.get("language", "zh"),
            model=request.form.get("model", "") or RUIZHI_AUDIO_MODEL,
            operator=_operator(),
        )
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.post("/api/audio/tts")
def ruizhi_tts():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or payload.get("input") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text is required"}), 400
    try:
        result = rz_client.tts_speech(
            str(sanitize_payload(text)),
            model=str(payload.get("model") or "") or RUIZHI_AUDIO_MODEL,
            voice=str(payload.get("voice") or "female"),
            speed=float(payload.get("speed") or 1.0),
            operator=_operator(),
        )
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    if not result.get("ok"):
        return jsonify(result), 502
    data = result.get("data") or {}
    content = data.get("content") or b""
    return jsonify(
        {
            "ok": True,
            "content_type": data.get("content_type") or "audio/wav",
            "bytes": len(content),
            "audio_base64": base64.b64encode(content).decode("ascii") if content else "",
        }
    )


@ruizhi_bp.post("/api/reports/generate")
def ruizhi_generate_report():
    payload = request.get_json(silent=True) or {}
    try:
        result = generate_report(
            report_type=str(payload.get("report_type") or "clue"),
            source_payload=payload.get("source") if isinstance(payload.get("source"), dict) else {},
            operator=_operator(),
            model=str(payload.get("model") or "") or None,
        )
    except rz_client.RuizhiNotConfigured as exc:
        return _not_configured_response(exc)
    return jsonify(result), (200 if result.get("ok") else 502)


@ruizhi_bp.get("/api/call-logs")
def ruizhi_call_logs():
    return jsonify(
        {
            "ok": True,
            "items": list_call_logs(
                limit=int(request.args.get("limit") or 100),
                module_code=(request.args.get("module_code") or "").strip(),
            ),
        }
    )

