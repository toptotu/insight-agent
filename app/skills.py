import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.rag import _tokenize


@dataclass
class SkillConfig:
    skill_id: str
    name: str
    description: str
    category: str = ""
    mode: str = "rule"
    input_fields: List[str] = field(default_factory=list)
    output_fields: List[str] = field(default_factory=list)
    prompt_template: str = ""
    tags: List[str] = field(default_factory=list)
    example_output: str = ""
    origin: str = "builtin"


def load_skill_configs(
    base_dir: str,
    custom_skills: Optional[List[Dict[str, object]]] = None,
    disabled_ids: Optional[List[str]] = None,
) -> Dict[str, SkillConfig]:
    config_path = os.path.join(base_dir, "data", "skills.json")
    with open(config_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    skills: Dict[str, SkillConfig] = {}
    disabled = set(disabled_ids or [])
    for entry in raw:
        if entry.get("id") in disabled:
            continue
        skill = SkillConfig(
            skill_id=entry["id"],
            name=entry.get("name", entry["id"]),
            description=entry.get("description", ""),
            category=entry.get("category", ""),
            mode=entry.get("mode", "rule"),
            input_fields=list(entry.get("input_fields") or []),
            output_fields=list(entry.get("output_fields") or []),
            prompt_template=entry.get("prompt_template", ""),
            tags=list(entry.get("tags") or []),
            example_output=entry.get("example_output", ""),
            origin="builtin",
        )
        skills[skill.skill_id] = skill
    if custom_skills:
        for entry in custom_skills:
            if entry.get("skill_id") in disabled:
                continue
            skill = SkillConfig(
                skill_id=str(entry.get("skill_id", "")),
                name=str(entry.get("name", "")),
                description=str(entry.get("description", "")),
                category=str(entry.get("category", "")),
                mode=str(entry.get("mode", "custom")),
                input_fields=list(entry.get("input_fields") or []),
                output_fields=list(entry.get("output_fields") or []),
                prompt_template=str(entry.get("prompt_template", "")),
                tags=list(entry.get("tags") or []),
                example_output=str(entry.get("example_output", "")),
                origin="custom",
            )
            skills[skill.skill_id] = skill
    return skills


BUILTIN_SKILLS = {
    "evidence_chain",
    "source_collection",
    "comparison",
    "trend_synthesis",
    "proposal_focus",
    "risk_identification",
    "capability_verification",
    "verification_plan",
    "report_outline",
}


CAPABILITY_RULES = {
    "抗干扰安全验证": {
        "keywords": ["抗干扰", "干扰", "鲁棒", "射频"],
        "verification": ["射频干扰注入实验", "链路鲁棒性评估", "抗干扰性能对比测试"],
    },
    "零信任与身份验证": {
        "keywords": ["零信任", "身份", "认证", "授权"],
        "verification": ["持续身份验证流程测试", "动态授权策略验证"],
    },
    "隐私计算与数据保护": {
        "keywords": ["隐私", "联邦学习", "差分隐私", "安全多方计算"],
        "verification": ["隐私预算评估", "安全多方计算一致性验证"],
    },
    "端到端加密与可信传输": {
        "keywords": ["加密", "可信", "端到端", "密钥"],
        "verification": ["端到端加密链路验证", "密钥管理与轮换测试"],
    },
}


def apply_skills(
    skill_ids: List[str],
    agent_results: List[Dict[str, object]],
    skill_catalog: Optional[Dict[str, SkillConfig]] = None,
) -> Dict[str, object]:
    outputs: Dict[str, object] = {}
    if "evidence_chain" in skill_ids:
        outputs["evidence_chain"] = build_evidence_chain(agent_results)
    if "source_collection" in skill_ids:
        outputs["source_collection"] = build_source_collection(agent_results)
    if "comparison" in skill_ids:
        outputs["comparison"] = build_comparison(agent_results)
    if "trend_synthesis" in skill_ids:
        outputs["trend_synthesis"] = build_trend_synthesis(agent_results)
    if "proposal_focus" in skill_ids:
        outputs["proposal_focus"] = build_proposal_focus(agent_results)
    if "risk_identification" in skill_ids:
        outputs["risk_identification"] = identify_risks(agent_results)
    if "capability_verification" in skill_ids:
        outputs["capability_verification"] = build_capability_report(agent_results)
    if "verification_plan" in skill_ids:
        outputs["verification_plan"] = build_verification_plan(outputs.get("capability_verification"))
    if "report_outline" in skill_ids:
        outputs["report_outline"] = build_report_outline(agent_results)
    custom_skill_ids = [skill_id for skill_id in skill_ids if skill_id not in BUILTIN_SKILLS]
    if custom_skill_ids:
        custom_items = []
        for skill_id in custom_skill_ids:
            config = skill_catalog.get(skill_id) if skill_catalog else None
            custom_items.append(
                {
                    "skill_id": skill_id,
                    "name": config.name if config else skill_id,
                    "description": config.description if config else "",
                    "category": config.category if config else "",
                    "mode": config.mode if config else "custom",
                    "tags": config.tags if config else [],
                    "example_output": config.example_output if config else "",
                    "note": "自定义Skill已选择，建议结合人工或扩展逻辑使用。",
                }
            )
        outputs["custom_skills"] = custom_items
    return outputs


def build_evidence_chain(agent_results: List[Dict[str, object]]) -> Dict[str, List[Dict[str, str]]]:
    chain: Dict[str, List[Dict[str, str]]] = {}
    for result in agent_results:
        chain[result["agent_name"]] = result.get("evidence", [])
    return chain


def build_comparison(agent_results: List[Dict[str, object]]) -> Dict[str, object]:
    keyword_counter = Counter()
    for result in agent_results:
        tokens = _tokenize(str(result.get("summary", "")))
        keyword_counter.update(tokens)
    common_keywords = [word for word, count in keyword_counter.most_common(8) if count > 1]
    return {
        "common_keywords": common_keywords,
        "observation": "不同来源普遍关注的关键词集合。",
    }


def build_trend_synthesis(agent_results: List[Dict[str, object]]) -> Dict[str, object]:
    keyword_counter = Counter()
    for result in agent_results:
        tokens = _tokenize(str(result.get("summary", "")))
        keyword_counter.update(tokens)
    trending = [word for word, count in keyword_counter.most_common(12) if count > 1]
    return {
        "trending_keywords": trending,
        "insight": "多源洞察中的热点趋势关键词。",
    }


def build_proposal_focus(agent_results: List[Dict[str, object]]) -> Dict[str, object]:
    keywords = ["提案", "建议", "关注", "重点", "主张", "路线图", "里程碑"]
    focus_lines: List[str] = []
    for result in agent_results:
        summary = str(result.get("summary", ""))
        for line in summary.splitlines():
            clean = line.strip().lstrip("-*0123456789. ")
            if not clean:
                continue
            if any(key in clean for key in keywords):
                focus_lines.append(f"{result.get('agent_name')}: {clean}")
    if not focus_lines:
        for result in agent_results:
            summary = str(result.get("summary", ""))
            first_line = summary.splitlines()[0] if summary else ""
            if first_line:
                focus_lines.append(f"{result.get('agent_name')}: {first_line}")
    return {"proposal_focus": focus_lines[:8], "note": "关键提案关注点集合。"}


def build_source_collection(agent_results: List[Dict[str, object]]) -> Dict[str, object]:
    source_types = Counter()
    source_titles = []
    for result in agent_results:
        for item in result.get("evidence", []):
            source_types.update([item.get("source_type", "unknown")])
            source_titles.append(item.get("title", ""))
    recommended_sources = [
        "3GPP/ITU/ETSI标准",
        "行业会议(MWC/IEEE/ACM)",
        "顶会论文与期刊",
        "厂商白皮书/发布会",
        "产业联盟与政策报告",
    ]
    return {
        "source_type_counts": dict(source_types),
        "evidence_titles": [title for title in source_titles if title][:6],
        "recommended_sources": recommended_sources,
    }


def identify_risks(agent_results: List[Dict[str, object]]) -> List[str]:
    risk_terms = ["风险", "攻击", "漏洞", "威胁", "隐私", "不确定", "挑战"]
    combined = " ".join(str(result.get("summary", "")) for result in agent_results)
    risks = []
    for term in risk_terms:
        if term in combined and term not in risks:
            risks.append(f"关注到{term}相关描述，建议进一步验证。")
    if not risks:
        risks.append("未发现显性风险描述，仍需在验证阶段补充对抗测试。")
    return risks


def build_capability_report(agent_results: List[Dict[str, object]]) -> Dict[str, object]:
    combined_text = " ".join(str(result.get("summary", "")) for result in agent_results)
    evidence_map: Dict[str, List[str]] = defaultdict(list)
    for result in agent_results:
        for item in result.get("evidence", []):
            evidence_map[result["agent_name"]].append(item.get("title", ""))
    capabilities: List[Dict[str, object]] = []
    for capability, rule in CAPABILITY_RULES.items():
        if any(keyword in combined_text for keyword in rule["keywords"]):
            evidence_titles = []
            for titles in evidence_map.values():
                evidence_titles.extend(titles)
            unique_titles = list(dict.fromkeys([title for title in evidence_titles if title]))
            maturity = "高" if len(unique_titles) >= 3 else "中" if len(unique_titles) >= 1 else "低"
            capabilities.append(
                {
                    "name": capability,
                    "evidence_titles": unique_titles[:5],
                    "verification_methods": rule["verification"],
                    "maturity": maturity,
                }
            )
    if not capabilities:
        capabilities.append(
            {
                "name": "待补充能力识别",
                "evidence_titles": [],
                "verification_methods": ["补充安全需求梳理", "采集更多标准/论文证据"],
                "maturity": "低",
            }
        )
    return {
        "capabilities": capabilities,
        "summary": "基于洞察内容识别的安全验证能力清单。",
    }


def build_verification_plan(capability_report: Dict[str, object]) -> Dict[str, object]:
    if not capability_report or "capabilities" not in capability_report:
        return {"plan": ["补充能力识别后生成验证计划"]}
    plan = ["阶段1：梳理验证范围与数据源", "阶段2：构建实验环境与基准", "阶段3：执行验证并评估结果"]
    for capability in capability_report.get("capabilities", []):
        methods = capability.get("verification_methods", [])
        if methods:
            plan.append(f"针对{capability.get('name')}：{methods[0]}")
    return {"plan": plan[:6]}


def build_report_outline(agent_results: List[Dict[str, object]]) -> Dict[str, object]:
    outline = [
        "1. 洞察目标与背景",
        "2. 关键趋势与热点",
        "3. 多源证据对比",
        "4. 安全与验证能力识别",
        "5. 风险与建议",
        "6. 结论与下一步",
    ]
    agent_names = [result.get("agent_name") for result in agent_results]
    return {"outline": outline, "contributors": agent_names}
