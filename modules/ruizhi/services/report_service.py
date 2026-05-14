from __future__ import annotations

from typing import Any

from modules.ruizhi.services.chat_service import run_chat


def generate_report(
    *,
    report_type: str,
    source_payload: dict[str, Any],
    operator: dict[str, Any] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    if report_type == "statistics":
        prompt = "请基于以下态势统计数据生成日报/周报/月报文字解读，突出指标变化、异常点、处置建议和待补数据。"
        scenario = "report"
    else:
        prompt = "请基于以下线索数据生成线索研判报告草稿，包含基础信息、风险依据、同行关系、处置建议和待核查问题。"
        scenario = "report"
    return run_chat(
        message=prompt,
        scenario_code=scenario,
        context={"report_type": report_type, "source": source_payload},
        model=model,
        operator=operator,
    )

