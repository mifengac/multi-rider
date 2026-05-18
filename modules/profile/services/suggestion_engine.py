def generate_suggestions(profile: dict) -> list[str]:
    suggestions = []

    score_info = profile.get("score") or {}
    total_score = score_info.get("total_score", 0)
    education = profile.get("education") or {}
    family = profile.get("family") or {}
    relations = profile.get("relations") or {}
    co_suspects = relations.get("co_suspects") or []

    edu_status = education.get("status", "")
    if total_score >= 60 and edu_status in ("dropout", "lost"):
        suggestions.append("建议联合教育部门劝返复学，每周走访")

    if edu_status == "truant":
        suggestions.append("建议联系学校班主任，关注到校情况")

    dim_family = score_info.get("dim_family", 0)
    if dim_family >= 15:
        suggestions.append("家庭监护严重缺失，建议联系民政部门介入")
    elif dim_family >= 10:
        suggestions.append("监护能力不足，建议定期走访监护人，告知近期违法情况")

    knjtlx = family.get("knjtlx") or ""
    if "低保" in knjtlx or "边缘" in knjtlx:
        suggestions.append("经济困难家庭，建议协调帮扶资源")

    if len(co_suspects) >= 3:
        names = "、".join([c.get("xm", "?") for c in co_suspects[:3]])
        suggestions.append(f"存在{len(co_suspects)}人团伙关联（{names}），注意聚集预警")

    if total_score >= 80:
        suggestions.append("极高风险，建议纳入重点监控、每周走访")
    elif total_score >= 60:
        suggestions.append("高风险，建议每两周走访一次")

    hotels = profile.get("hotels") or []
    for h in hotels[:3]:
        tfrxm = h.get("tfrxm")
        if not tfrxm:
            suggestions.append("近期无监护人陪同入住旅馆，建议约谈旅馆并通知监护人")
            break

    if not suggestions:
        suggestions.append("当前风险较低，纳入常规管理")

    return suggestions[:6]
