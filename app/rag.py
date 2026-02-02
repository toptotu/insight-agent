import json
import math
import os
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.config_store import ConfigStore


@dataclass
class Document:
    doc_id: str
    title: str
    source: str
    source_type: str
    content: str
    domain_id: str
    source_id: str

    def snippet(self, limit: int = 160) -> str:
        text = self.content.replace("\n", " ").strip()
        return text[:limit] + ("..." if len(text) > limit else "")


@dataclass
class RAGSource:
    source_id: str
    label: str
    path: str


@dataclass
class DomainConfig:
    domain_id: str
    name: str
    description: str
    rag_sources: List[RAGSource]
    default_agents: List[str]
    default_skills: List[str]
    origin: str = "builtin"


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    buffer: List[str] = []
    for ch in text:
        if ch.isalnum():
            buffer.append(ch.lower())
            continue
        if "\u4e00" <= ch <= "\u9fff":
            if buffer:
                tokens.append("".join(buffer))
                buffer = []
            tokens.append(ch)
            continue
        if buffer:
            tokens.append("".join(buffer))
            buffer = []
    if buffer:
        tokens.append("".join(buffer))
    return tokens


class SimpleRetriever:
    def __init__(self, documents: List[Document]) -> None:
        self.documents = documents
        self.doc_tokens: Dict[str, Counter] = {}
        self.doc_len: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self._build_index()

    def _build_index(self) -> None:
        df: Counter = Counter()
        for doc in self.documents:
            tokens = _tokenize(f"{doc.title} {doc.content}")
            tf = Counter(tokens)
            self.doc_tokens[doc.doc_id] = tf
            self.doc_len[doc.doc_id] = max(1, sum(tf.values()))
            for token in set(tokens):
                df[token] += 1
        total_docs = max(1, len(self.documents))
        for token, freq in df.items():
            self.idf[token] = math.log((1 + total_docs) / (1 + freq)) + 1.0

    def search(self, query: str, top_k: int = 5, min_score: float = 0.1) -> List[Tuple[float, Document]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        query_tf = Counter(query_tokens)
        scores: List[Tuple[float, Document]] = []
        for doc in self.documents:
            tf = self.doc_tokens.get(doc.doc_id, Counter())
            length = self.doc_len.get(doc.doc_id, 1)
            score = 0.0
            for token, q_count in query_tf.items():
                weight = self.idf.get(token, 0.0)
                score += (tf.get(token, 0) / length) * weight * q_count
            if score >= min_score:
                scores.append((score, doc))
        scores.sort(key=lambda item: item[0], reverse=True)
        return scores[: max(1, top_k)]


class RAGStore:
    def __init__(self, base_dir: str, config_store: Optional[ConfigStore] = None) -> None:
        self.base_dir = base_dir
        self.config_store = config_store
        self.domains: Dict[str, DomainConfig] = {}
        self._retrievers: Dict[str, SimpleRetriever] = {}
        self._documents: Dict[str, List[Document]] = {}
        self._load_domains()

    def _load_domains(self) -> None:
        config_path = os.path.join(self.base_dir, "data", "domains.json")
        with open(config_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        for domain_id, payload in raw.items():
            sources = [
                RAGSource(source_id=entry["id"], label=entry["label"], path=entry["path"])
                for entry in payload.get("rag_sources", [])
            ]
            self.domains[domain_id] = DomainConfig(
                domain_id=domain_id,
                name=payload.get("name", domain_id),
                description=payload.get("description", ""),
                rag_sources=sources,
                default_agents=payload.get("default_agents", []),
                default_skills=payload.get("default_skills", []),
                origin="builtin",
            )

    def list_domains(self) -> List[DomainConfig]:
        domains = list(self.domains.values())
        if self.config_store:
            for entry in self.config_store.list_domains():
                domains.append(
                    DomainConfig(
                        domain_id=entry["domain_id"],
                        name=entry["name"],
                        description=entry.get("description", ""),
                        rag_sources=[RAGSource(source_id="custom", label="自定义知识", path="")],
                        default_agents=[],
                        default_skills=[],
                        origin="custom",
                    )
                )
        return domains

    def get_domain(self, domain_id: str) -> Optional[DomainConfig]:
        domain = self.domains.get(domain_id)
        if domain:
            return domain
        if self.config_store:
            for entry in self.config_store.list_domains():
                if entry["domain_id"] == domain_id:
                    return DomainConfig(
                        domain_id=entry["domain_id"],
                        name=entry["name"],
                        description=entry.get("description", ""),
                        rag_sources=[RAGSource(source_id="custom", label="自定义知识", path="")],
                        default_agents=[],
                        default_skills=[],
                        origin="custom",
                    )
        return None

    def get_documents(self, domain_id: str) -> List[Document]:
        if domain_id in self._documents:
            return self._documents[domain_id]
        documents: List[Document] = []
        domain = self.domains.get(domain_id)
        if domain:
            for source in domain.rag_sources:
                path = os.path.join(self.base_dir, source.path)
                if not os.path.exists(path):
                    continue
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        payload = json.loads(line)
                        documents.append(
                            Document(
                                doc_id=payload.get("id", ""),
                                title=payload.get("title", ""),
                                source=payload.get("source", ""),
                                source_type=payload.get("source_type", source.source_id),
                                content=payload.get("content", ""),
                                domain_id=domain_id,
                                source_id=source.source_id,
                            )
                        )
        if self.config_store:
            for entry in self.config_store.list_documents(domain_id):
                documents.append(
                    Document(
                        doc_id=entry.get("doc_id", ""),
                        title=entry.get("title", ""),
                        source=entry.get("source", ""),
                        source_type=entry.get("source_type", "custom"),
                        content=entry.get("content", ""),
                        domain_id=domain_id,
                        source_id="custom",
                    )
                )
        if not documents:
            self._documents[domain_id] = []
            return []
        self._documents[domain_id] = documents
        return documents

    def get_retriever(self, domain_id: str) -> SimpleRetriever:
        if domain_id not in self._retrievers:
            documents = self.get_documents(domain_id)
            self._retrievers[domain_id] = SimpleRetriever(documents)
        return self._retrievers[domain_id]

    def invalidate(self, domain_id: str) -> None:
        if domain_id in self._retrievers:
            self._retrievers.pop(domain_id, None)
        if domain_id in self._documents:
            self._documents.pop(domain_id, None)
