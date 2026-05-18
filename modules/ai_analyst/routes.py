import json

from flask import Response, jsonify, request

from . import ai_analyst_bp
from shared.ai.ruizhi_client import chat, chat_with_kb, RuizhiApiError
from shared.config.config import RUIZHI_KB_NAME
from .services.prompt_builder import (
    SYSTEM_PROMPT,
    build_person_analysis_prompt,
    build_serial_case_prompt,
)
from .services.case_matcher import fetch_recent_qincai_cases, find_serial_candidates


def _sse_stream(gen):
    def generate():
        try:
            for chunk in gen:
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                if choices[0].get("finish_reason") == "stop":
                    break
        except RuizhiApiError as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")


def _sse_text(text: str):
    def generate():
        yield f"data: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")


@ai_analyst_bp.route("/chat", methods=["POST"])
def ai_chat():
    body = request.get_json(force=True)
    message = (body.get("message") or "").strip()
    history = body.get("history") or []
    mode = body.get("mode", "general")

    if not message:
        return jsonify({"error": "missing message"}), 400

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-20:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    try:
        if mode == "rag" and RUIZHI_KB_NAME:
            gen = chat_with_kb(messages, [RUIZHI_KB_NAME], stream=True)
        else:
            gen = chat(messages, stream=True)
        return _sse_stream(gen)
    except RuizhiApiError as e:
        return _sse_text(f"AI服务调用失败: {e}")


@ai_analyst_bp.route("/analyze/person", methods=["POST"])
def analyze_person():
    body = request.get_json(force=True)
    zjhm = (body.get("zjhm") or "").strip()
    if not zjhm:
        return jsonify({"error": "missing zjhm"}), 400

    from modules.profile.services.profile_assembler import assemble_profile

    person_data = assemble_profile(zjhm)
    if not person_data or not person_data.get("basic"):
        return _sse_text("未找到该人员信息，请确认证件号码是否正确。")

    messages = build_person_analysis_prompt(person_data)

    try:
        gen = chat(messages, stream=True, max_tokens=4096, temperature=0.5)
        return _sse_stream(gen)
    except RuizhiApiError as e:
        return _sse_text(f"AI分析失败: {e}")


@ai_analyst_bp.route("/analyze/serial", methods=["POST"])
def analyze_serial():
    body = request.get_json(force=True)
    months = body.get("months", 6)

    cases = fetch_recent_qincai_cases(months)
    if len(cases) < 2:
        return _sse_text(f"近{months}个月内侵财案件不足2起，无法进行串并分析。")

    similar_pairs = find_serial_candidates(cases)
    messages = build_serial_case_prompt(cases, similar_pairs)

    result_meta = {
        "case_count": len(cases),
        "pair_count": len(similar_pairs),
    }

    try:
        gen = chat(messages, stream=True, max_tokens=4096, temperature=0.3)

        def generate():
            yield f"data: {json.dumps({'meta': result_meta}, ensure_ascii=False)}\n\n"
            try:
                for chunk in gen:
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                    if choices[0].get("finish_reason") == "stop":
                        break
            except RuizhiApiError as e:
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return Response(generate(), mimetype="text/event-stream")
    except RuizhiApiError as e:
        return _sse_text(f"串并分析失败: {e}")
