import json
import math
import os
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.config_store import ConfigStore

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None


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


class FaissRetriever:
    def __init__(self, documents: List[Document], dim: int = 256) -> None:
        if np is None or faiss is None:
            raise RuntimeError("FAISS or numpy is not available")
        self.documents = documents
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.doc_lookup: List[Document] = []
        self._build_index()

    def _embed(self, text: str) -> "np.ndarray":
        tokens = _tokenize(text)
        vector = np.zeros(self.dim, dtype="float32")
        if not tokens:
            return vector.reshape(1, -1)
        for token in tokens:
            idx = abs(hash(token)) % self.dim
            vector[idx] += 1.0
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector.reshape(1, -1)

    def _build_index(self) -> None:
        for doc in self.documents:
            vector = self._embed(f"{doc.title} {doc.content}")
            self.index.add(vector)
            self.doc_lookup.append(doc)

    def search(self, query: str, top_k: int = 5, min_score: float = 0.1) -> List[Tuple[float, Document]]:
        if not query or self.index.ntotal == 0:
            return []
        query_vector = self._embed(query)
        scores, indices = self.index.search(query_vector, max(1, top_k))
        results: List[Tuple[float, Document]] = []
        for score, idx in zip(scores[0].tolist(), indices[0].tolist()):
            if idx < 0:
                continue
            if score < min_score:
                continue
            results.append((float(score), self.doc_lookup[idx]))
        return results


class RAGStore:
    def __init__(self, base_dir: str, config_store: Optional[ConfigStore] = None) -> None:
        self.base_dir = base_dir
        self.config_store = config_store
        self.domains: Dict[str, DomainConfig] = {}
        self._retrievers: Dict[str, object] = {}
        self._documents: Dict[str, List[Document]] = {}
        self._load_domains()
        self._use_faiss = self._should_use_faiss()

    def _should_use_faiss(self) -> bool:
        flag = os.getenv("USE_FAISS", "1").lower()
        if flag in {"0", "false", "no"}:
            return False
        return faiss is not None and np is not None

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
        domains: List[DomainConfig] = []
        custom_domains: Dict[str, Dict[str, object]] = {}
        disabled_ids: List[str] = []
        if self.config_store:
            custom_domains = {entry["domain_id"]: entry for entry in self.config_store.list_domains()}
            disabled_ids = self.config_store.get_disabled_ids("domain")
        for domain_id, domain in self.domains.items():
            if domain_id in disabled_ids:
                continue
            override = custom_domains.get(domain_id)
            if override:
                domains.append(
                    DomainConfig(
                        domain_id=domain_id,
                        name=str(override.get("name", domain.name)),
                        description=str(override.get("description", domain.description)),
                        rag_sources=domain.rag_sources,
                        default_agents=list(override.get("default_agents") or domain.default_agents),
                        default_skills=list(override.get("default_skills") or domain.default_skills),
                        origin="custom",
                    )
                )
            else:
                domains.append(domain)
        for entry in custom_domains.values():
            domain_id = entry["domain_id"]
            if domain_id in self.domains:
                continue
            if domain_id in disabled_ids:
                continue
            domains.append(
                DomainConfig(
                    domain_id=domain_id,
                    name=entry["name"],
                    description=entry.get("description", ""),
                    rag_sources=[RAGSource(source_id="custom", label="自定义知识", path="")],
                    default_agents=list(entry.get("default_agents") or []),
                    default_skills=list(entry.get("default_skills") or []),
                    origin="custom",
                )
            )
        return domains

    def get_domain(self, domain_id: str) -> Optional[DomainConfig]:
        if self.config_store:
            disabled_ids = self.config_store.get_disabled_ids("domain")
            if domain_id in disabled_ids:
                return None
        domain = self.domains.get(domain_id)
        if domain:
            if self.config_store:
                for entry in self.config_store.list_domains():
                    if entry["domain_id"] == domain_id:
                        return DomainConfig(
                            domain_id=entry["domain_id"],
                            name=entry.get("name", domain.name),
                            description=entry.get("description", domain.description),
                            rag_sources=domain.rag_sources,
                            default_agents=list(entry.get("default_agents") or domain.default_agents),
                            default_skills=list(entry.get("default_skills") or domain.default_skills),
                            origin="custom",
                        )
            return domain
        if self.config_store:
            for entry in self.config_store.list_domains():
                if entry["domain_id"] == domain_id:
                    return DomainConfig(
                        domain_id=entry["domain_id"],
                        name=entry["name"],
                        description=entry.get("description", ""),
                        rag_sources=[RAGSource(source_id="custom", label="自定义知识", path="")],
                        default_agents=list(entry.get("default_agents") or []),
                        default_skills=list(entry.get("default_skills") or []),
                        origin="custom",
                    )
        return None

    def get_documents(self, domain_id: str) -> List[Document]:
        if domain_id in self._documents:
            return self._documents[domain_id]
        documents_map: Dict[str, Document] = {}
        disabled_docs: List[str] = []
        if self.config_store:
            disabled_docs = self.config_store.get_disabled_ids("document")
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
                        doc_id = payload.get("id", "")
                        if doc_id in disabled_docs:
                            continue
                        documents_map[doc_id] = Document(
                            doc_id=doc_id,
                            title=payload.get("title", ""),
                            source=payload.get("source", ""),
                            source_type=payload.get("source_type", source.source_id),
                            content=payload.get("content", ""),
                            domain_id=domain_id,
                            source_id=source.source_id,
                        )
        if self.config_store:
            for entry in self.config_store.list_documents(domain_id):
                doc_id = entry.get("doc_id", "")
                if doc_id in disabled_docs:
                    continue
                documents_map[doc_id] = Document(
                    doc_id=doc_id,
                    title=entry.get("title", ""),
                    source=entry.get("source", ""),
                    source_type=entry.get("source_type", "custom"),
                    content=entry.get("content", ""),
                    domain_id=domain_id,
                    source_id="custom",
                )
        documents = list(documents_map.values())
        if not documents:
            self._documents[domain_id] = []
            return []
        self._documents[domain_id] = documents
        return documents

    def get_retriever(self, domain_id: str) -> object:
        if domain_id not in self._retrievers:
            documents = self.get_documents(domain_id)
            if self._use_faiss:
                dim = int(os.getenv("FAISS_DIM", "256"))
                self._retrievers[domain_id] = FaissRetriever(documents, dim=dim)
            else:
                self._retrievers[domain_id] = SimpleRetriever(documents)
        return self._retrievers[domain_id]

    def invalidate(self, domain_id: str) -> None:
        if domain_id in self._retrievers:
            self._retrievers.pop(domain_id, None)
        if domain_id in self._documents:
            self._documents.pop(domain_id, None)
