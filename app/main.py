import os
from dataclasses import asdict
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agents import load_agent_configs, run_agents
from app.config_store import ConfigStore
from app.llm import create_llm_client
from app.rag import RAGStore
from app.report import build_insight_summary
from app.schemas import (
    CreateAgentRequest,
    CreateDocumentRequest,
    CreateDomainRequest,
    CreateSkillRequest,
    InsightRequest,
)
from app.skills import apply_skills, load_skill_configs
from app.store import TaskStore


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config_store = ConfigStore(BASE_DIR)
rag_store = RAGStore(BASE_DIR, config_store=config_store)
task_store = TaskStore(BASE_DIR)

app = FastAPI(title="Insight Platform", version="0.1.0")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "app", "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/ui/insight", response_class=HTMLResponse)
def insight_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("insight.html", {"request": request})


@app.get("/ui/history", response_class=HTMLResponse)
def history_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/ui/config", response_class=HTMLResponse)
def config_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("config.html", {"request": request})


@app.get("/ui/report/{task_id}", response_class=HTMLResponse)
def report_ui(request: Request, task_id: str) -> HTMLResponse:
    return templates.TemplateResponse("report.html", {"request": request, "task_id": task_id})


@app.get("/api/meta", response_class=JSONResponse)
def get_meta() -> JSONResponse:
    domains = [asdict(domain) for domain in rag_store.list_domains()]
    custom_agents = config_store.list_agents()
    custom_skills = config_store.list_skills()
    agents = [asdict(agent) for agent in load_agent_configs(BASE_DIR, custom_agents).values()]
    skills = [asdict(skill) for skill in load_skill_configs(BASE_DIR, custom_skills).values()]
    return JSONResponse({"domains": domains, "agents": agents, "skills": skills})


@app.post("/api/insights", response_class=JSONResponse)
def create_insight(request_body: InsightRequest) -> JSONResponse:
    domain = rag_store.get_domain(request_body.domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    agent_ids = request_body.agent_ids or domain.default_agents
    skill_ids = request_body.skill_ids or domain.default_skills
    rag_config = request_body.rag_config

    llm = create_llm_client()
    agent_catalog = load_agent_configs(BASE_DIR, config_store.list_agents())
    skill_catalog = load_skill_configs(BASE_DIR, config_store.list_skills())
    if not agent_ids:
        agent_ids = [
            agent_id
            for agent_id, config in agent_catalog.items()
            if not config.domain_id or config.domain_id == domain.domain_id
        ]
    agent_results = run_agents(
        domain_id=domain.domain_id,
        objective=request_body.objective,
        agent_ids=agent_ids,
        rag_store=rag_store,
        llm=llm,
        top_k=rag_config.top_k,
        min_score=rag_config.min_score,
        agent_catalog=agent_catalog,
    )
    agent_payload: List[Dict[str, object]] = [asdict(result) for result in agent_results]
    skill_outputs = apply_skills(skill_ids, agent_payload, skill_catalog)
    insight_summary = build_insight_summary(
        request_body.objective, agent_payload, skill_outputs, llm
    )
    capability_report = skill_outputs.get("capability_verification", {})

    response_payload = {
        "domain": asdict(domain),
        "objective": request_body.objective,
        "agent_ids": agent_ids,
        "skill_ids": skill_ids,
        "rag_config": rag_config.dict(),
        "insight_summary": insight_summary,
        "agent_results": agent_payload,
        "skill_outputs": skill_outputs,
        "capability_report": capability_report,
        "llm_mode": "aliyun" if not llm.is_mock else "mock",
    }
    task_id = task_store.create_task(response_payload)
    response_payload["task_id"] = task_id
    response_payload["status"] = "completed"
    return JSONResponse(response_payload)


@app.get("/api/insights/{task_id}", response_class=JSONResponse)
def get_insight(task_id: str) -> JSONResponse:
    payload = task_store.get_task(task_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(payload)


@app.get("/api/tasks", response_class=JSONResponse)
def list_tasks(limit: int = 20) -> JSONResponse:
    limit = min(max(limit, 1), 200)
    items = task_store.list_tasks(limit=limit)
    return JSONResponse({"items": items})


@app.get("/api/config/domains", response_class=JSONResponse)
def list_custom_domains() -> JSONResponse:
    return JSONResponse({"items": config_store.list_domains()})


@app.post("/api/config/domains", response_class=JSONResponse)
def create_custom_domain(request_body: CreateDomainRequest) -> JSONResponse:
    try:
        domain = config_store.create_domain(
            name=request_body.name,
            description=request_body.description,
            domain_id=request_body.domain_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(domain)


@app.get("/api/config/agents", response_class=JSONResponse)
def list_custom_agents() -> JSONResponse:
    return JSONResponse({"items": config_store.list_agents()})


@app.post("/api/config/agents", response_class=JSONResponse)
def create_custom_agent(request_body: CreateAgentRequest) -> JSONResponse:
    try:
        agent = config_store.create_agent(
            name=request_body.name,
            focus=request_body.focus,
            description=request_body.description,
            default_query=request_body.default_query,
            skill_ids=request_body.skill_ids,
            domain_id=request_body.domain_id,
            agent_id=request_body.agent_id,
            category=request_body.category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(agent)


@app.get("/api/config/skills", response_class=JSONResponse)
def list_custom_skills() -> JSONResponse:
    return JSONResponse({"items": config_store.list_skills()})


@app.post("/api/config/skills", response_class=JSONResponse)
def create_custom_skill(request_body: CreateSkillRequest) -> JSONResponse:
    try:
        skill = config_store.create_skill(
            name=request_body.name,
            description=request_body.description,
            skill_id=request_body.skill_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(skill)


@app.get("/api/config/documents", response_class=JSONResponse)
def list_custom_documents(domain_id: str = "") -> JSONResponse:
    domain_id = domain_id or None
    return JSONResponse({"items": config_store.list_documents(domain_id)})


@app.post("/api/config/documents", response_class=JSONResponse)
def create_custom_document(request_body: CreateDocumentRequest) -> JSONResponse:
    if not rag_store.get_domain(request_body.domain_id):
        raise HTTPException(status_code=404, detail="Domain not found")
    try:
        doc = config_store.create_document(
            domain_id=request_body.domain_id,
            title=request_body.title,
            source=request_body.source,
            source_type=request_body.source_type,
            content=request_body.content,
            doc_id=request_body.doc_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rag_store.invalidate(request_body.domain_id)
    return JSONResponse(doc)


@app.get("/health", response_class=JSONResponse)
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
