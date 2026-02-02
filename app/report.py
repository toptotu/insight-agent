from typing import Dict, List, Optional

from app.llm import BaseLLMClient


def build_insight_summary(
    objective: str, agent_results: List[Dict[str, object]], skill_outputs: Dict[str, object], llm: BaseLLMClient
) -> str:
    if llm.is_mock:
        lines = [f"洞察目标：{objective}", "综合洞察要点："]
        for result in agent_results:
            summary = str(result.get("summary", "")).strip()
            lines.append(f"- {result.get('agent_name')}: {summary.splitlines()[0] if summary else '暂无'}")
        if "risk_identification" in skill_outputs:
            risks = skill_outputs.get("risk_identification", [])
            if risks:
                lines.append("风险提示：")
                for risk in risks[:3]:
                    lines.append(f"- {risk}")
        if "custom_skills" in skill_outputs:
            lines.append("自定义Skill：")
            for skill in skill_outputs.get("custom_skills", []):
                lines.append(f"- {skill.get('name')}: {skill.get('description')}")
        return "\n".join(lines)
    prompt = _build_summary_prompt(objective, agent_results, skill_outputs)
    return llm.generate(prompt, max_tokens=480).text


def _build_summary_prompt(
    objective: str, agent_results: List[Dict[str, object]], skill_outputs: Dict[str, object]
) -> str:
    lines = [
        "你是技术洞察平台的汇总模型，请根据多Agent结果生成洞察总结。",
        f"洞察目标：{objective}",
        "Agent洞察：",
    ]
    for result in agent_results:
        lines.append(f"- {result.get('agent_name')}：{result.get('summary')}")
    if "risk_identification" in skill_outputs:
        lines.append(f"风险识别：{skill_outputs.get('risk_identification')}")
    if "custom_skills" in skill_outputs:
        lines.append(f"自定义Skill：{skill_outputs.get('custom_skills')}")
    if "trend_synthesis" in skill_outputs:
        lines.append(f"趋势融合：{skill_outputs.get('trend_synthesis')}")
    if "report_outline" in skill_outputs:
        lines.append(f"报告大纲：{skill_outputs.get('report_outline')}")
    if "verification_plan" in skill_outputs:
        lines.append(f"验证计划：{skill_outputs.get('verification_plan')}")
    lines.append("请输出：洞察总结(不超过8条)，并突出关键能力。")
    return "\n".join(lines)


def build_report_sections(
    objective: str,
    insight_summary: str,
    agent_results: List[Dict[str, object]],
    skill_outputs: Dict[str, object],
    template: Optional[Dict[str, object]],
    llm: BaseLLMClient,
) -> List[Dict[str, object]]:
    if not template:
        return []
    sections = []
    trending = (
        skill_outputs.get("trend_synthesis", {}).get("trending_keywords", [])
        if isinstance(skill_outputs.get("trend_synthesis"), dict)
        else []
    )
    topics = template.get("topics") or trending[:3] or ["6G架构", "关键技术", "新场景业务"]

    for section in template.get("sections", []):
        section_type = section.get("type")
        if section_type == "summary":
            bullets = _summary_to_bullets(insight_summary)
            if section.get("use_llm") and not llm.is_mock:
                bullets = _llm_section_bullets(
                    llm, objective, section.get("instruction", ""), agent_results, bullets
                )
            sections.append(
                {
                    "title": section.get("title", "洞察摘要"),
                    "type": "summary",
                    "bullets": bullets,
                    "instruction": section.get("instruction", ""),
                }
            )
        elif section_type == "tech":
            per_topic = bool(section.get("per_topic", True))
            if per_topic:
                for topic in topics:
                    bullets = _topic_bullets(topic, agent_results)
                    if section.get("use_llm") and not llm.is_mock:
                        bullets = _llm_section_bullets(
                            llm,
                            objective,
                            section.get("instruction", ""),
                            agent_results,
                            bullets,
                            topic=topic,
                        )
                    viewpoint = f"启示：优先验证{topic}相关安全能力与标准对齐。"
                    sections.append(
                        {
                            "title": f"{section.get('title', '技术洞察')} - {topic}",
                            "type": "tech",
                            "topic": topic,
                            "bullets": bullets,
                            "viewpoint": viewpoint,
                            "instruction": section.get("instruction", ""),
                        }
                    )
            else:
                bullets = []
                for topic in topics:
                    bullets.extend(_topic_bullets(topic, agent_results))
                if section.get("use_llm") and not llm.is_mock:
                    bullets = _llm_section_bullets(
                        llm, objective, section.get("instruction", ""), agent_results, bullets
                    )
                sections.append(
                    {
                        "title": section.get("title", "技术洞察"),
                        "type": "tech",
                        "topic": ",".join(topics),
                        "bullets": bullets[:6],
                        "viewpoint": "启示：建议针对关键技术统一规划验证路径。",
                        "instruction": section.get("instruction", ""),
                    }
                )
        elif section_type == "closing":
            capability = skill_outputs.get("capability_verification", {})
            verification_plan = skill_outputs.get("verification_plan", {})
            bullets = _closing_bullets(capability, verification_plan)
            if section.get("use_llm") and not llm.is_mock:
                bullets = _llm_section_bullets(
                    llm, objective, section.get("instruction", ""), agent_results, bullets
                )
            sections.append(
                {
                    "title": section.get("title", "洞察总结与验证能力"),
                    "type": "closing",
                    "bullets": bullets,
                    "instruction": section.get("instruction", ""),
                }
            )
        else:
            sections.append(
                {
                    "title": section.get("title", "自定义板块"),
                    "type": section_type or "custom",
                    "bullets": section.get("bullets", []),
                    "instruction": section.get("instruction", ""),
                }
            )
    return sections


def _summary_to_bullets(summary: str) -> List[str]:
    if not summary:
        return []
    lines = []
    for line in summary.splitlines():
        line = line.strip().lstrip("-*0123456789. ")
        if line:
            lines.append(line)
    return lines[:8]


def _topic_bullets(topic: str, agent_results: List[Dict[str, object]]) -> List[str]:
    bullets: List[str] = []
    for result in agent_results:
        summary = str(result.get("summary", ""))
        if topic in summary:
            first_line = summary.splitlines()[0]
            bullets.append(f"{result.get('agent_name')}: {first_line}")
    if not bullets:
        bullets.append(f"围绕{topic}的标准、论文与产业材料需要补充验证。")
    return bullets[:4]


def _closing_bullets(
    capability_report: Dict[str, object], verification_plan: Dict[str, object]
) -> List[str]:
    bullets: List[str] = []
    for cap in capability_report.get("capabilities", [])[:5]:
        bullets.append(f"{cap.get('name')} (成熟度: {cap.get('maturity')})")
    plan = verification_plan.get("plan") if isinstance(verification_plan, dict) else None
    if plan:
        bullets.extend(plan[:3])
    return bullets


def _llm_section_bullets(
    llm: BaseLLMClient,
    objective: str,
    instruction: str,
    agent_results: List[Dict[str, object]],
    fallback: List[str],
    topic: str = "",
) -> List[str]:
    prompt_lines = [
        "你是洞察报告生成器，请输出要点列表。",
        f"洞察目标：{objective}",
    ]
    if topic:
        prompt_lines.append(f"当前主题：{topic}")
    if instruction:
        prompt_lines.append(f"输出要求：{instruction}")
    prompt_lines.append("参考信息：")
    for result in agent_results:
        prompt_lines.append(f"- {result.get('agent_name')}: {result.get('summary')}")
    prompt_lines.append("请输出3-5条要点，每条以'-'开头。")
    try:
        text = llm.generate("\n".join(prompt_lines), max_tokens=220).text
        lines = []
        for line in text.splitlines():
            line = line.strip().lstrip("-*0123456789. ")
            if line:
                lines.append(line)
        return lines[:5] if lines else fallback
    except Exception:
        return fallback
