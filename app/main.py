import os
from dataclasses import asdict
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agents import load_agent_configs, run_agents
from app.llm import create_llm_client
from app.rag import RAGStore
from app.report import build_insight_summary
from app.schemas import InsightRequest
from app.skills import apply_skills, load_skill_configs
from app.store import TaskStore


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

rag_store = RAGStore(BASE_DIR)
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


@app.get("/ui/report/{task_id}", response_class=HTMLResponse)
def report_ui(request: Request, task_id: str) -> HTMLResponse:
    return templates.TemplateResponse("report.html", {"request": request, "task_id": task_id})


@app.get("/api/meta", response_class=JSONResponse)
def get_meta() -> JSONResponse:
    domains = [asdict(domain) for domain in rag_store.list_domains()]
    agents = [asdict(agent) for agent in load_agent_configs(BASE_DIR).values()]
    skills = [asdict(skill) for skill in load_skill_configs(BASE_DIR).values()]
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
    agent_results = run_agents(
        domain_id=domain.domain_id,
        objective=request_body.objective,
        agent_ids=agent_ids,
        rag_store=rag_store,
        llm=llm,
        top_k=rag_config.top_k,
        min_score=rag_config.min_score,
        base_dir=BASE_DIR,
    )
    agent_payload: List[Dict[str, object]] = [asdict(result) for result in agent_results]
    skill_outputs = apply_skills(skill_ids, agent_payload)
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


@app.get("/health", response_class=JSONResponse)
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
