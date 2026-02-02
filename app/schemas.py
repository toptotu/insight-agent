from typing import List

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
