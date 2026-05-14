from __future__ import annotations

from typing import Any

from shared.config.config import RUIZHI_CHAT_MODEL
from modules.ruizhi.services.client import chat_completions, ensure_configured, kb_chat
from modules.ruizhi.services.prompt_guard import digest_text, sanitize_messages, sanitize_payload
from modules.ruizhi.services.store import create_session, get_session, list_messages, save_message


SYSTEM_PROMPTS = {
    "general": "你是公安内网未成年人违法犯罪防控系统的AI辅助研判助手。只提供辅助建议，关键处置必须由民警确认。",
    "profile": "你负责解释一人一档画像，输出近期活动变化、风险点和待核查问题。不要编造画像中不存在的信息。",
    "risk": "你负责解释风险评分明细，说明加分、减分、提级和排除项依据。不得直接改变风险等级。",
    "dispatch": "你负责草拟核查指令和短信内容，必须保持克制、规范，并提醒发送前人工确认。",
    "report": "你负责生成线索研判报告草稿，结构清晰，区分事实、推断和待核实事项。",
}


def _extract_assistant_text(payload: dict[str, Any]) -> tuple[str, list[Any]]:
    data = payload.get("data") if payload.get("ok") else payload.get("data")
    if not isinstance(data, dict):
        return "", []
    choices = data.get("choices") or []
    docs_refs = []
    assistant_text = ""
    for choice in choices:
        message = (choice or {}).get("message") or {}
        if message.get("role") == "docs":
            docs_refs.append(message.get("content"))
        elif not assistant_text:
            assistant_text = message.get("content") or ""
    return assistant_text, docs_refs


def build_context_prompt(scenario_code: str, context: dict[str, Any] | None = None) -> str:
    base = SYSTEM_PROMPTS.get(scenario_code or "general", SYSTEM_PROMPTS["general"])
    if not context:
        return base
    safe_context = sanitize_payload(context)
    return base + "\n\n以下为系统提供的结构化上下文，请只基于上下文和已接入知识库回答：\n" + str(safe_context)


def run_chat(
    *,
    message: str,
    scenario_code: str = "general",
    session_id: str = "",
    context: dict[str, Any] | None = None,
    kb_names: list[str] | None = None,
    model: str | None = None,
    operator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_configured()
    operator = operator or {}
    scenario = scenario_code or "general"
    if not session_id:
        title = (message or "AI 研判会话").strip().replace("\n", " ")[:40]
        session = create_session(title=title, scenario_code=scenario, created_by=operator.get("username") or operator.get("user_id") or "")
        session_id = session["id"]
    else:
        session = get_session(session_id)
        if not session:
            session = create_session(title="AI 研判会话", scenario_code=scenario, created_by=operator.get("username") or "")
            session_id = session["id"]

    user_text = sanitize_payload(message)
    save_message(session_id=session_id, role="user", content_text=user_text, content_digest=digest_text(str(user_text)))
    history = list_messages(session_id, limit=20)
    messages = [{"role": "system", "content": build_context_prompt(scenario, context)}]
    for item in history:
        if item.get("role") in {"user", "assistant"}:
            messages.append({"role": item["role"], "content": item.get("content_text", "")})
    messages = sanitize_messages(messages)

    if kb_names:
        result = kb_chat(messages, kb_names=kb_names, model=model or RUIZHI_CHAT_MODEL, operator=operator)
    else:
        result = chat_completions(messages, model=model or RUIZHI_CHAT_MODEL, operator=operator)
    if not result.get("ok"):
        return {"ok": False, "session_id": session_id, "error": result.get("error"), "raw": result.get("data")}
    assistant_text, docs_refs = _extract_assistant_text(result)
    save_message(
        session_id=session_id,
        role="assistant",
        content_text=assistant_text,
        content_digest=digest_text(assistant_text),
        model_name=model or RUIZHI_CHAT_MODEL,
        docs_ref=docs_refs,
    )
    return {
        "ok": True,
        "session_id": session_id,
        "message": assistant_text,
        "docs_refs": docs_refs,
        "raw": result.get("data"),
    }
