from typing import Dict, List

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
    lines.append("请输出：洞察总结(不超过8条)，并突出关键能力。")
    return "\n".join(lines)
