import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List

from app.rag import _tokenize


@dataclass
class SkillConfig:
    skill_id: str
    name: str
    description: str


def load_skill_configs(base_dir: str) -> Dict[str, SkillConfig]:
    config_path = os.path.join(base_dir, "data", "skills.json")
    with open(config_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    skills: Dict[str, SkillConfig] = {}
    for entry in raw:
        skill = SkillConfig(
            skill_id=entry["id"],
            name=entry.get("name", entry["id"]),
            description=entry.get("description", ""),
        )
        skills[skill.skill_id] = skill
    return skills


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


def apply_skills(skill_ids: List[str], agent_results: List[Dict[str, object]]) -> Dict[str, object]:
    outputs: Dict[str, object] = {}
    if "evidence_chain" in skill_ids:
        outputs["evidence_chain"] = build_evidence_chain(agent_results)
    if "comparison" in skill_ids:
        outputs["comparison"] = build_comparison(agent_results)
    if "risk_identification" in skill_ids:
        outputs["risk_identification"] = identify_risks(agent_results)
    if "capability_verification" in skill_ids:
        outputs["capability_verification"] = build_capability_report(agent_results)
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
