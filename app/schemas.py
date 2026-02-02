from typing import Any, Dict, List, Optional

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
    report_template_id: Optional[str] = None


class CreateDomainRequest(BaseModel):
    domain_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)
    default_agents: List[str] = []
    default_skills: List[str] = []


class UpdateDomainRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    default_agents: Optional[List[str]] = None
    default_skills: Optional[List[str]] = None


class CreateAgentRequest(BaseModel):
    agent_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    focus: str = Field("", max_length=200)
    description: str = Field("", max_length=500)
    default_query: str = Field("", max_length=300)
    skill_ids: List[str] = []
    category: str = Field("", max_length=100)
    domain_id: str = Field("", max_length=120)


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    focus: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    default_query: Optional[str] = Field(None, max_length=300)
    skill_ids: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=100)
    domain_id: Optional[str] = Field(None, max_length=120)


class CreateSkillRequest(BaseModel):
    skill_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)
    category: str = Field("", max_length=100)
    mode: str = Field("", max_length=50)
    input_fields: List[str] = []
    output_fields: List[str] = []
    prompt_template: str = Field("", max_length=2000)
    tags: List[str] = []
    example_output: str = Field("", max_length=1000)


class UpdateSkillRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    mode: Optional[str] = Field(None, max_length=50)
    input_fields: Optional[List[str]] = None
    output_fields: Optional[List[str]] = None
    prompt_template: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None
    example_output: Optional[str] = Field(None, max_length=1000)


class CreateDocumentRequest(BaseModel):
    doc_id: Optional[str] = None
    domain_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    source: str = Field("", max_length=200)
    source_type: str = Field("custom", max_length=120)
    content: str = Field(..., min_length=1, max_length=5000)


class UpdateDocumentRequest(BaseModel):
    domain_id: Optional[str] = Field(None, min_length=1, max_length=120)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    source: Optional[str] = Field(None, max_length=200)
    source_type: Optional[str] = Field(None, max_length=120)
    content: Optional[str] = Field(None, min_length=1, max_length=5000)


class CreateCrawlerRequest(BaseModel):
    source_id: Optional[str] = None
    domain_id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=1000)
    source_type: str = Field("crawler", max_length=120)
    description: str = Field("", max_length=500)
    interval_minutes: int = Field(1440, ge=1, le=10080)
    enabled: bool = True


class UpdateCrawlerRequest(BaseModel):
    domain_id: Optional[str] = Field(None, min_length=1, max_length=120)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[str] = Field(None, min_length=1, max_length=1000)
    source_type: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    interval_minutes: Optional[int] = Field(None, ge=1, le=10080)
    enabled: Optional[bool] = None


class CreateReportTemplateRequest(BaseModel):
    template_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)
    sections: List[Dict[str, Any]] = []


class UpdateReportTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    sections: Optional[List[Dict[str, Any]]] = None
