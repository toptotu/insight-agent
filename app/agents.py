import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.llm import BaseLLMClient
from app.rag import Document, RAGStore


@dataclass
class AgentConfig:
    agent_id: str
    name: str
    focus: str
    description: str
    default_query: str
    skill_ids: List[str]
    domain_id: str = ""
    origin: str = "builtin"
    category: str = ""


@dataclass
class AgentResult:
    agent_id: str
    agent_name: str
    focus: str
    summary: str
    evidence: List[Dict[str, str]]


def load_agent_configs(
    base_dir: str,
    custom_agents: Optional[List[Dict[str, object]]] = None,
    disabled_ids: Optional[List[str]] = None,
) -> Dict[str, AgentConfig]:
    config_path = os.path.join(base_dir, "data", "agents.json")
    with open(config_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    agents: Dict[str, AgentConfig] = {}
    disabled = set(disabled_ids or [])
    for entry in raw:
        if entry.get("id") in disabled:
            continue
        agent = AgentConfig(
            agent_id=entry["id"],
            name=entry.get("name", entry["id"]),
            focus=entry.get("focus", ""),
            description=entry.get("description", ""),
            default_query=entry.get("default_query", ""),
            skill_ids=entry.get("skill_ids", []),
            domain_id=entry.get("domain_id", ""),
            origin="builtin",
            category=entry.get("category", ""),
        )
        agents[agent.agent_id] = agent
    if custom_agents:
        for entry in custom_agents:
            if entry.get("agent_id") in disabled:
                continue
            agent = AgentConfig(
                agent_id=str(entry.get("agent_id", "")),
                name=str(entry.get("name", "")),
                focus=str(entry.get("focus", "")),
                description=str(entry.get("description", "")),
                default_query=str(entry.get("default_query", "")),
                skill_ids=list(entry.get("skill_ids") or []),
                domain_id=str(entry.get("domain_id", "")),
                origin="custom",
                category=str(entry.get("category", "")),
            )
            agents[agent.agent_id] = agent
    return agents


class InsightAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def run(
        self,
        domain_id: str,
        objective: str,
        rag_store: RAGStore,
        llm: BaseLLMClient,
        top_k: int,
        min_score: float,
    ) -> AgentResult:
        query = f"{objective} {self.config.default_query} {self.config.focus}".strip()
        retriever = rag_store.get_retriever(domain_id)
        hits = retriever.search(query, top_k=top_k, min_score=min_score)
        evidence = [
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "source": doc.source,
                "source_type": doc.source_type,
                "snippet": doc.snippet(),
                "score": f"{score:.3f}",
            }
            for score, doc in hits
        ]
        if llm.is_mock:
            summary = _fallback_summary(self.config, objective, hits)
        else:
            prompt = _build_agent_prompt(self.config, objective, hits)
            summary = llm.generate(prompt, max_tokens=420).text
        return AgentResult(
            agent_id=self.config.agent_id,
            agent_name=self.config.name,
            focus=self.config.focus,
            summary=summary,
            evidence=evidence,
        )


def _build_agent_prompt(config: AgentConfig, objective: str, hits: List[Tuple[float, Document]]) -> str:
    lines = [
        "你是技术洞察平台中的Agent，请基于检索到的证据输出洞察要点。",
        f"洞察目标：{objective}",
        f"Agent关注点：{config.focus}",
        "输出要求：列出3-5条关键洞察，每条包含证据来源。",
        "证据：",
    ]
    for score, doc in hits:
        lines.append(
            f"- 标题：{doc.title} | 来源：{doc.source} | 摘要：{doc.snippet(120)} | 分数：{score:.3f}"
        )
    return "\n".join(lines)


def _fallback_summary(config: AgentConfig, objective: str, hits: List[Tuple[float, Document]]) -> str:
    if not hits:
        return f"未检索到与“{objective}”相关的{config.name}证据。"
    lines = [f"{config.name}基于证据形成的要点："]
    for score, doc in hits[:3]:
        lines.append(f"- {doc.title}（{doc.source}）：{doc.snippet(120)}")
    return "\n".join(lines)


def run_agents(
    domain_id: str,
    objective: str,
    agent_ids: List[str],
    rag_store: RAGStore,
    llm: BaseLLMClient,
    top_k: int,
    min_score: float,
    agent_catalog: Dict[str, AgentConfig],
) -> List[AgentResult]:
    results: List[AgentResult] = []
    for agent_id in agent_ids:
        config = agent_catalog.get(agent_id)
        if not config:
            continue
        if config.domain_id and config.domain_id != domain_id:
            continue
        agent = InsightAgent(config)
        results.append(agent.run(domain_id, objective, rag_store, llm, top_k, min_score))
    return results
