SYSTEM_PROMPT = (
    "你是未成年人犯罪侦查部门的AI研判助手，专注于侵财犯罪（盗窃、抢劫、抢夺、诈骗、敲诈勒索）分析。"
    "你的职责包括：1) 分析未成年人侵财犯罪风险；2) 发现串并案线索；3) 提供法律依据和处置建议。"
    "回答时引用具体数据，使用结构化格式（标题、列表），给出明确的结论和建议。"
    "所有分析必须考虑未成年人保护原则：教育为主、惩罚为辅。"
)

QINCAI_TYPES = ["盗窃", "抢劫", "抢夺", "诈骗", "敲诈勒索"]


def build_person_analysis_prompt(person_data: dict) -> list[dict]:
    basic = person_data.get("basic", {})
    score = person_data.get("score", {})
    cases = person_data.get("cases", [])
    behaviors = person_data.get("behaviors", [])
    family = person_data.get("family", {})
    education = person_data.get("education", {})
    relations = person_data.get("relations", {})

    qincai_cases = [
        c for c in cases
        if any(t in (c.get("ajxx_ay") or c.get("ajxx_ajmc") or "") for t in QINCAI_TYPES)
    ]
    other_cases = [c for c in cases if c not in qincai_cases]

    context_parts = [f"## 人员基本信息\n- 姓名: {basic.get('xm', '--')}\n- 证件号: {basic.get('zjhm', '--')}"]

    if basic.get("csrq"):
        context_parts.append(f"- 出生日期: {basic['csrq']}")
    if basic.get("xb"):
        context_parts.append(f"- 性别: {basic['xb']}")

    context_parts.append(
        f"\n## 风险评分\n- 总分: {score.get('total_score', '--')}/100"
        f"\n- 风险等级: {score.get('risk_level', '--')}"
        f"\n- 案件维度: {score.get('dim_case', 0)}/30"
        f"\n- 行为维度: {score.get('dim_behavior', 0)}/25"
        f"\n- 家庭维度: {score.get('dim_family', 0)}/20"
        f"\n- 教育维度: {score.get('dim_education', 0)}/15"
        f"\n- 社交维度: {score.get('dim_social', 0)}/10"
    )

    if qincai_cases:
        lines = [f"\n## 侵财案件记录 ({len(qincai_cases)}起)"]
        for c in qincai_cases:
            lines.append(
                f"- [{c.get('ajxx_fasj', '--')}] {c.get('ajxx_ay', '')} "
                f"| {c.get('ajxx_ajmc', '')} | 办案单位: {c.get('ajxx_cbdw_mc', '')}"
            )
        context_parts.append("\n".join(lines))

    if other_cases:
        lines = [f"\n## 其他案件记录 ({len(other_cases)}起)"]
        for c in other_cases[:5]:
            lines.append(f"- [{c.get('ajxx_fasj', '--')}] {c.get('ajxx_ay', '')} | {c.get('ajxx_ajmc', '')}")
        context_parts.append("\n".join(lines))

    if behaviors:
        lines = [f"\n## 行为记录 ({len(behaviors)}条)"]
        for b in behaviors[:8]:
            lines.append(f"- [{b.get('wf_sj', '--')}] {b.get('wfxw_cn', '')} | {b.get('fsdd', '')}")
        context_parts.append("\n".join(lines))

    if family:
        context_parts.append(
            f"\n## 家庭信息\n- 监护人: {family.get('jhr1xm', '--')}"
            f"\n- 家庭状况: {family.get('jtqk', '--')}"
            f"\n- 困难类型: {family.get('knjtlx', '无')}"
            f"\n- 儿童类别: {family.get('etlb', '普通')}"
        )

    if education:
        context_parts.append(
            f"\n## 教育状态\n- 状态: {education.get('status', '--')}"
            f"\n- 学校: {education.get('yxx', '--')}"
        )

    co_suspects = (relations or {}).get("co_suspects", [])
    if co_suspects:
        lines = [f"\n## 关联人员 ({len(co_suspects)}人)"]
        for cs in co_suspects[:5]:
            lines.append(f"- {cs.get('xm', '--')} | 共犯{cs.get('case_count', 1)}次")
        context_parts.append("\n".join(lines))

    context = "\n".join(context_parts)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"请对以下未成年人进行侵财犯罪风险研判分析：\n\n{context}\n\n"
                "请从以下维度分析：\n"
                "1. 侵财犯罪风险评估（结合案件记录和行为模式）\n"
                "2. 犯罪成因分析（家庭、教育、社交因素）\n"
                "3. 团伙关联分析（是否存在侵财团伙迹象）\n"
                "4. 再犯风险预测\n"
                "5. 分级干预建议（具体可落地的措施）"
            ),
        },
    ]


def build_serial_case_prompt(cases: list[dict], similar_pairs: list[dict]) -> list[dict]:
    case_lines = []
    for i, c in enumerate(cases, 1):
        case_lines.append(
            f"{i}. [{c.get('ajbh', '')}] {c.get('ay', '')} | {c.get('ajmc', '')} "
            f"| 时间: {c.get('fasj', '--')} | 单位: {c.get('cbdw', '')}"
        )
    case_text = "\n".join(case_lines)

    pair_lines = []
    for p in similar_pairs[:15]:
        pair_lines.append(
            f"- 案件{p['i']+1} ↔ 案件{p['j']+1} (相似度: {p['score']:.3f})"
        )
    pair_text = "\n".join(pair_lines) if pair_lines else "未发现高相似度案件对"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"以下是近期未成年人侵财案件列表：\n\n{case_text}\n\n"
                f"AI向量分析发现的高相似度案件对：\n{pair_text}\n\n"
                "请分析：\n"
                "1. 哪些案件可能是同一团伙或同一人所为（串并案），给出理由\n"
                "2. 作案手法的共同特征\n"
                "3. 时空规律（作案时间、地点的关联）\n"
                "4. 侦查建议（合并侦查方向、重点关注对象）"
            ),
        },
    ]
