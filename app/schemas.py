from typing import List, Optional

from pydantic import BaseModel, Field


class RAGConfig(BaseModel):
    top_k: int = Field(5, ge=1, le=20)
    min_score: float = Field(0.1, ge=0.0, le=10.0)
    enable_rerank: bool = False


class InsightRequest(BaseModel):
    domain_id: str
    objective: str = Field(..., min_length=1, max_length=500)
    agent_ids: List[str] = []
    skill_ids: List[str] = []
    rag_config: RAGConfig = RAGConfig()


class CreateDomainRequest(BaseModel):
    domain_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)


class CreateAgentRequest(BaseModel):
    agent_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    focus: str = Field("", max_length=200)
    description: str = Field("", max_length=500)
    default_query: str = Field("", max_length=300)
    skill_ids: List[str] = []
    domain_id: str = Field("", max_length=120)


class CreateSkillRequest(BaseModel):
    skill_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)


class CreateDocumentRequest(BaseModel):
    doc_id: Optional[str] = None
    domain_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    source: str = Field("", max_length=200)
    source_type: str = Field("custom", max_length=120)
    content: str = Field(..., min_length=1, max_length=5000)
