import json
import os
from dataclasses import asdict
from typing import Dict, List

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agents import load_agent_configs, run_agents
from app.config_store import ConfigStore
from app.auth_store import AuthStore
from app.crawler import CrawlerService
from app.file_ingest import SUPPORTED_EXTENSIONS, extract_text_from_upload
from app.llm import create_llm_client
from app.rag import RAGStore
from app.report import build_insight_summary, build_quick_html_report, build_report_sections
from app.report_templates import BUILTIN_REPORT_TEMPLATES
from app.quick_store import QuickReportStore
from app.schemas import (
    CreateAgentRequest,
    CreateCrawlerRequest,
    CreateDocumentRequest,
    CreateDomainRequest,
    CreateSkillRequest,
    CreateReportTemplateRequest,
    InsightRequest,
    UpdateAgentRequest,
    UpdateCrawlerRequest,
    UpdateDocumentRequest,
    UpdateDomainRequest,
    UpdateReportTemplateRequest,
    UpdateSkillRequest,
)
from app.skills import apply_skills, load_skill_configs
from app.store import TaskStore


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config_store = ConfigStore(BASE_DIR)
rag_store = RAGStore(BASE_DIR, config_store=config_store)
task_store = TaskStore(BASE_DIR)
crawler_service = CrawlerService(config_store, rag_store)
quick_store = QuickReportStore(BASE_DIR)
auth_store = AuthStore(BASE_DIR)

app = FastAPI(title="Insight Platform", version="0.1.0")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "app", "static")), name="static")
QUICK_REPORTS_DIR = os.path.join(BASE_DIR, "data", "quick_reports")
os.makedirs(QUICK_REPORTS_DIR, exist_ok=True)
app.mount(
    "/quick-reports-files",
    StaticFiles(directory=QUICK_REPORTS_DIR),
    name="quick_reports_files",
)

SESSION_COOKIE_NAME = "insight_session_id"
PUBLIC_PATH_PREFIXES = ("/login", "/change-password", "/health", "/static")


def _is_public_path(path: str) -> bool:
    return path.startswith(PUBLIC_PATH_PREFIXES)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if _is_public_path(path):
        return await call_next(request)
    session_id = request.cookies.get(SESSION_COOKIE_NAME, "")
    session = auth_store.get_session(session_id)
    if not session:
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return RedirectResponse(url="/login")
    user = auth_store.get_user(session["username"])
    if user and user.get("must_change_password") and not path.startswith("/change-password"):
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Password change required"}, status_code=403)
        return RedirectResponse(url="/change-password")
    request.state.user = user
    return await call_next(request)

INSIGHT_FLOW = [
    {
        "step": "任务定义",
        "description": "明确洞察目标与关注范围",
        "inputs": ["目标", "领域"],
        "outputs": ["洞察任务配置"],
    },
    {
        "step": "RAG检索",
        "description": "从多源材料召回证据",
        "inputs": ["标准/论文/白皮书等"],
        "outputs": ["证据候选集"],
    },
    {
        "step": "Agent洞察",
        "description": "各Agent生成分主题洞察",
        "inputs": ["证据候选集"],
        "outputs": ["Agent洞察结果"],
    },
    {
        "step": "Skill处理",
        "description": "趋势融合、对比、风险与验证能力识别",
        "inputs": ["Agent洞察结果"],
        "outputs": ["洞察能力产物"],
    },
    {
        "step": "汇总与报告",
        "description": "生成洞察总结与PPT报告",
        "inputs": ["洞察能力产物"],
        "outputs": ["洞察总结/报告"],
    },
]

ARTIFACT_DESCRIPTIONS = {
    "insight_summary": "洞察总结：面向目标的关键结论与趋势归纳。",
    "capability_report": "能力识别与验证报告：识别安全能力并给出验证方法与成熟度。",
    "evidence_chain": "证据链：每条洞察关联的标准/论文/白皮书证据。",
    "agent_results": "Agent洞察：各Agent基于证据的分主题分析。",
}


@app.on_event("startup")
def start_crawler_service() -> None:
    crawler_service.start()


@app.on_event("shutdown")
def stop_crawler_service() -> None:
    crawler_service.stop()


def _load_builtin_domains() -> Dict[str, Dict[str, object]]:
    path = os.path.join(BASE_DIR, "data", "domains.json")
    with open(path, "r", encoding="utf-8") as handle:
        return dict(json.load(handle))


def _load_builtin_agents() -> Dict[str, Dict[str, object]]:
    agents = load_agent_configs(BASE_DIR)
    return {agent_id: asdict(agent) for agent_id, agent in agents.items()}


def _load_builtin_skills() -> Dict[str, Dict[str, object]]:
    skills = load_skill_configs(BASE_DIR)
    return {skill_id: asdict(skill) for skill_id, skill in skills.items()}


def _load_builtin_documents(domain_id: str = "") -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    domains = _load_builtin_domains()
    for builtin_id, domain in domains.items():
        if domain_id and builtin_id != domain_id:
            continue
        for source in domain.get("rag_sources", []):
            path = os.path.join(BASE_DIR, source.get("path", ""))
            if not path or not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    payload = json.loads(line)
                    items.append(
                        {
                            "doc_id": payload.get("id", ""),
                            "domain_id": builtin_id,
                            "title": payload.get("title", ""),
                            "source": payload.get("source", ""),
                            "source_type": payload.get("source_type", source.get("id", "builtin")),
                            "content": payload.get("content", ""),
                            "origin": "builtin",
                        }
                    )
    return items


def _list_report_templates() -> List[Dict[str, object]]:
    builtin = {tpl["template_id"]: tpl for tpl in BUILTIN_REPORT_TEMPLATES}
    custom = {item["template_id"]: item for item in config_store.list_report_templates()}
    disabled = set(config_store.get_disabled_ids("report_template"))
    items: List[Dict[str, object]] = []
    for template_id, tpl in builtin.items():
        override = custom.get(template_id)
        entry = {
            **tpl,
            "origin": "builtin",
            "disabled": template_id in disabled,
        }
        if override:
            entry.update(override)
            entry["origin"] = "custom"
            entry["overrides_builtin"] = True
        items.append(entry)
    for template_id, tpl in custom.items():
        if template_id in builtin:
            continue
        items.append({**tpl, "origin": "custom", "disabled": template_id in disabled})
    return items


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login", response_class=HTMLResponse)
def login_action(request: Request, username: str = Form(...), password: str = Form(...)):
    user = auth_store.authenticate(username.strip(), password.strip())
    if not user:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "用户名或密码错误"}
        )
    session = auth_store.create_session(user["username"])
    redirect_url = "/change-password" if user.get("must_change_password") else "/"
    response = RedirectResponse(url=redirect_url, status_code=302)
    secure_cookie = os.getenv("AUTH_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session["session_id"],
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
        max_age=int(os.getenv("AUTH_SESSION_TTL", "28800")),
    )
    return response


@app.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("change_password.html", {"request": request, "error": ""})


@app.post("/change-password", response_class=HTMLResponse)
def change_password_action(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
):
    session_id = request.cookies.get(SESSION_COOKIE_NAME, "")
    session = auth_store.get_session(session_id)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    user = auth_store.authenticate(session["username"], current_password.strip())
    if not user:
        return templates.TemplateResponse(
            "change_password.html", {"request": request, "error": "原密码错误"}
        )
    if len(new_password.strip()) < 8:
        return templates.TemplateResponse(
            "change_password.html", {"request": request, "error": "新密码至少8位"}
        )
    auth_store.update_password(session["username"], new_password.strip())
    return RedirectResponse(url="/", status_code=302)


@app.get("/logout")
def logout(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME, "")
    if session_id:
        auth_store.delete_session(session_id)
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/ui/insight", response_class=HTMLResponse)
def insight_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("insight.html", {"request": request})


@app.get("/ui/history", response_class=HTMLResponse)
def history_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/ui/config", response_class=HTMLResponse)
def config_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("config.html", {"request": request})


@app.get("/ui/quick-insight", response_class=HTMLResponse)
def quick_insight_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("quick_insight.html", {"request": request})


@app.get("/ui/quick-reports", response_class=HTMLResponse)
def quick_reports_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("quick_reports.html", {"request": request})


@app.get("/ui/quick-report/{report_id}", response_class=HTMLResponse)
def quick_report_ui(request: Request, report_id: str) -> HTMLResponse:
    return templates.TemplateResponse(
        "quick_report.html", {"request": request, "report_id": report_id}
    )


@app.get("/ui/report/{task_id}", response_class=HTMLResponse)
def report_ui(request: Request, task_id: str) -> HTMLResponse:
    return templates.TemplateResponse("report.html", {"request": request, "task_id": task_id})


@app.get("/api/meta", response_class=JSONResponse)
def get_meta() -> JSONResponse:
    domains = [asdict(domain) for domain in rag_store.list_domains()]
    custom_agents = config_store.list_agents()
    custom_skills = config_store.list_skills()
    disabled_agents = config_store.get_disabled_ids("agent")
    disabled_skills = config_store.get_disabled_ids("skill")
    agents = [
        asdict(agent)
        for agent in load_agent_configs(BASE_DIR, custom_agents, disabled_agents).values()
    ]
    skills = [
        asdict(skill)
        for skill in load_skill_configs(BASE_DIR, custom_skills, disabled_skills).values()
    ]
    templates = [item for item in _list_report_templates() if not item.get("disabled")]
    return JSONResponse(
        {"domains": domains, "agents": agents, "skills": skills, "report_templates": templates}
    )


@app.post("/api/insights", response_class=JSONResponse)
def create_insight(request_body: InsightRequest) -> JSONResponse:
    domain = rag_store.get_domain(request_body.domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    agent_ids = request_body.agent_ids or domain.default_agents
    skill_ids = request_body.skill_ids or domain.default_skills
    rag_config = request_body.rag_config

    llm = create_llm_client()
    disabled_agents = config_store.get_disabled_ids("agent")
    disabled_skills = config_store.get_disabled_ids("skill")
    agent_catalog = load_agent_configs(BASE_DIR, config_store.list_agents(), disabled_agents)
    skill_catalog = load_skill_configs(BASE_DIR, config_store.list_skills(), disabled_skills)
    agent_ids = [agent_id for agent_id in agent_ids if agent_id not in disabled_agents]
    skill_ids = [skill_id for skill_id in skill_ids if skill_id not in disabled_skills]
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

    templates = _list_report_templates()
    template_id = request_body.report_template_id or "ppt-default"
    report_template = None
    for template in templates:
        if template.get("template_id") == template_id and not template.get("disabled"):
            report_template = template
            break
    if not report_template:
        report_template = templates[0] if templates else None
    report_sections = build_report_sections(
        request_body.objective,
        insight_summary,
        agent_payload,
        skill_outputs,
        report_template,
        llm,
    )

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
        "report_template": report_template,
        "report_sections": report_sections,
        "insight_flow": INSIGHT_FLOW,
        "artifact_descriptions": ARTIFACT_DESCRIPTIONS,
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


@app.delete("/api/tasks/{task_id}", response_class=JSONResponse)
def delete_task(task_id: str) -> JSONResponse:
    deleted = task_store.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse({"status": "deleted"})


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
            default_agents=request_body.default_agents,
            default_skills=request_body.default_skills,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(domain)


@app.get("/api/config/domains/all", response_class=JSONResponse)
def list_all_domains() -> JSONResponse:
    builtin = _load_builtin_domains()
    custom = {item["domain_id"]: item for item in config_store.list_domains()}
    disabled = set(config_store.get_disabled_ids("domain"))
    items: List[Dict[str, object]] = []
    for domain_id, payload in builtin.items():
        override = custom.get(domain_id)
        entry = {
            "domain_id": domain_id,
            "name": payload.get("name", domain_id),
            "description": payload.get("description", ""),
            "default_agents": payload.get("default_agents", []),
            "default_skills": payload.get("default_skills", []),
            "origin": "builtin",
            "disabled": domain_id in disabled,
        }
        if override:
            entry.update(
                {
                    "name": override.get("name", entry["name"]),
                    "description": override.get("description", entry["description"]),
                    "default_agents": override.get("default_agents", entry["default_agents"]),
                    "default_skills": override.get("default_skills", entry["default_skills"]),
                    "origin": "custom",
                    "overrides_builtin": True,
                }
            )
        items.append(entry)
    for domain_id, payload in custom.items():
        if domain_id in builtin:
            continue
        items.append(
            {
                "domain_id": domain_id,
                "name": payload.get("name", domain_id),
                "description": payload.get("description", ""),
                "default_agents": payload.get("default_agents", []),
                "default_skills": payload.get("default_skills", []),
                "origin": "custom",
                "disabled": domain_id in disabled,
            }
        )
    return JSONResponse({"items": items})


@app.put("/api/config/domains/{domain_id}", response_class=JSONResponse)
def update_domain(domain_id: str, request_body: UpdateDomainRequest) -> JSONResponse:
    custom_domains = {item["domain_id"]: item for item in config_store.list_domains()}
    builtin_domains = _load_builtin_domains()
    updates = request_body.dict(exclude_unset=True)
    if domain_id in custom_domains:
        updated = config_store.update_domain(domain_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Domain not found")
        rag_store.invalidate(domain_id)
        return JSONResponse(updated)
    if domain_id in builtin_domains:
        base = builtin_domains[domain_id]
        merged = {
            "name": base.get("name", domain_id),
            "description": base.get("description", ""),
            "default_agents": base.get("default_agents", []),
            "default_skills": base.get("default_skills", []),
        }
        merged.update(updates)
        domain = config_store.create_domain(
            name=merged["name"],
            description=merged["description"],
            domain_id=domain_id,
            default_agents=merged["default_agents"],
            default_skills=merged["default_skills"],
        )
        rag_store.invalidate(domain_id)
        return JSONResponse(domain)
    raise HTTPException(status_code=404, detail="Domain not found")


@app.delete("/api/config/domains/{domain_id}", response_class=JSONResponse)
def delete_domain(domain_id: str) -> JSONResponse:
    custom_domains = {item["domain_id"]: item for item in config_store.list_domains()}
    builtin_domains = _load_builtin_domains()
    if domain_id in custom_domains:
        config_store.delete_domain(domain_id)
        rag_store.invalidate(domain_id)
        return JSONResponse({"status": "deleted"})
    if domain_id in builtin_domains:
        config_store.disable_item("domain", domain_id)
        rag_store.invalidate(domain_id)
        return JSONResponse({"status": "disabled"})
    raise HTTPException(status_code=404, detail="Domain not found")


@app.post("/api/config/domains/{domain_id}/enable", response_class=JSONResponse)
def enable_domain(domain_id: str) -> JSONResponse:
    config_store.enable_item("domain", domain_id)
    rag_store.invalidate(domain_id)
    return JSONResponse({"status": "enabled"})


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


@app.get("/api/config/agents/all", response_class=JSONResponse)
def list_all_agents() -> JSONResponse:
    builtin = _load_builtin_agents()
    custom = {item["agent_id"]: item for item in config_store.list_agents()}
    disabled = set(config_store.get_disabled_ids("agent"))
    items: List[Dict[str, object]] = []
    for agent_id, payload in builtin.items():
        override = custom.get(agent_id)
        entry = {
            **payload,
            "origin": "builtin",
            "disabled": agent_id in disabled,
        }
        if override:
            entry.update(override)
            entry["origin"] = "custom"
            entry["overrides_builtin"] = True
        items.append(entry)
    for agent_id, payload in custom.items():
        if agent_id in builtin:
            continue
        items.append({**payload, "origin": "custom", "disabled": agent_id in disabled})
    return JSONResponse({"items": items})


@app.put("/api/config/agents/{agent_id}", response_class=JSONResponse)
def update_agent(agent_id: str, request_body: UpdateAgentRequest) -> JSONResponse:
    custom_agents = {item["agent_id"]: item for item in config_store.list_agents()}
    builtin_agents = _load_builtin_agents()
    updates = request_body.dict(exclude_unset=True)
    if agent_id in custom_agents:
        updated = config_store.update_agent(agent_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Agent not found")
        return JSONResponse(updated)
    if agent_id in builtin_agents:
        base = builtin_agents[agent_id]
        merged = {
            "name": base.get("name", agent_id),
            "focus": base.get("focus", ""),
            "description": base.get("description", ""),
            "default_query": base.get("default_query", ""),
            "skill_ids": base.get("skill_ids", []),
            "category": base.get("category", ""),
            "domain_id": base.get("domain_id", ""),
        }
        merged.update(updates)
        agent = config_store.create_agent(
            name=merged["name"],
            focus=merged["focus"],
            description=merged["description"],
            default_query=merged["default_query"],
            skill_ids=merged["skill_ids"],
            domain_id=merged["domain_id"],
            agent_id=agent_id,
            category=merged["category"],
        )
        return JSONResponse(agent)
    raise HTTPException(status_code=404, detail="Agent not found")


@app.delete("/api/config/agents/{agent_id}", response_class=JSONResponse)
def delete_agent(agent_id: str) -> JSONResponse:
    custom_agents = {item["agent_id"]: item for item in config_store.list_agents()}
    builtin_agents = _load_builtin_agents()
    if agent_id in custom_agents:
        config_store.delete_agent(agent_id)
        return JSONResponse({"status": "deleted"})
    if agent_id in builtin_agents:
        config_store.disable_item("agent", agent_id)
        return JSONResponse({"status": "disabled"})
    raise HTTPException(status_code=404, detail="Agent not found")


@app.post("/api/config/agents/{agent_id}/enable", response_class=JSONResponse)
def enable_agent(agent_id: str) -> JSONResponse:
    config_store.enable_item("agent", agent_id)
    return JSONResponse({"status": "enabled"})


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
            category=request_body.category,
            mode=request_body.mode,
            input_fields=request_body.input_fields,
            output_fields=request_body.output_fields,
            prompt_template=request_body.prompt_template,
            tags=request_body.tags,
            example_output=request_body.example_output,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(skill)


@app.get("/api/config/skills/all", response_class=JSONResponse)
def list_all_skills() -> JSONResponse:
    builtin = _load_builtin_skills()
    custom = {item["skill_id"]: item for item in config_store.list_skills()}
    disabled = set(config_store.get_disabled_ids("skill"))
    items: List[Dict[str, object]] = []
    for skill_id, payload in builtin.items():
        override = custom.get(skill_id)
        entry = {
            **payload,
            "origin": "builtin",
            "disabled": skill_id in disabled,
        }
        if override:
            entry.update(override)
            entry["origin"] = "custom"
            entry["overrides_builtin"] = True
        items.append(entry)
    for skill_id, payload in custom.items():
        if skill_id in builtin:
            continue
        items.append({**payload, "origin": "custom", "disabled": skill_id in disabled})
    return JSONResponse({"items": items})


@app.put("/api/config/skills/{skill_id}", response_class=JSONResponse)
def update_skill(skill_id: str, request_body: UpdateSkillRequest) -> JSONResponse:
    custom_skills = {item["skill_id"]: item for item in config_store.list_skills()}
    builtin_skills = _load_builtin_skills()
    updates = request_body.dict(exclude_unset=True)
    if skill_id in custom_skills:
        updated = config_store.update_skill(skill_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Skill not found")
        return JSONResponse(updated)
    if skill_id in builtin_skills:
        base = builtin_skills[skill_id]
        merged = {
            "name": base.get("name", skill_id),
            "description": base.get("description", ""),
            "category": base.get("category", ""),
            "mode": base.get("mode", "rule"),
            "input_fields": base.get("input_fields", []),
            "output_fields": base.get("output_fields", []),
            "prompt_template": base.get("prompt_template", ""),
            "tags": base.get("tags", []),
            "example_output": base.get("example_output", ""),
        }
        merged.update(updates)
        skill = config_store.create_skill(
            name=merged["name"],
            description=merged["description"],
            skill_id=skill_id,
            category=merged["category"],
            mode=merged["mode"],
            input_fields=merged["input_fields"],
            output_fields=merged["output_fields"],
            prompt_template=merged["prompt_template"],
            tags=merged["tags"],
            example_output=merged["example_output"],
        )
        return JSONResponse(skill)
    raise HTTPException(status_code=404, detail="Skill not found")


@app.delete("/api/config/skills/{skill_id}", response_class=JSONResponse)
def delete_skill(skill_id: str) -> JSONResponse:
    custom_skills = {item["skill_id"]: item for item in config_store.list_skills()}
    builtin_skills = _load_builtin_skills()
    if skill_id in custom_skills:
        config_store.delete_skill(skill_id)
        return JSONResponse({"status": "deleted"})
    if skill_id in builtin_skills:
        config_store.disable_item("skill", skill_id)
        return JSONResponse({"status": "disabled"})
    raise HTTPException(status_code=404, detail="Skill not found")


@app.post("/api/config/skills/{skill_id}/enable", response_class=JSONResponse)
def enable_skill(skill_id: str) -> JSONResponse:
    config_store.enable_item("skill", skill_id)
    return JSONResponse({"status": "enabled"})


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


@app.post("/api/config/documents/upload", response_class=JSONResponse)
def upload_document(
    domain_id: str = Form(...),
    source_type: str = Form("upload"),
    source: str = Form(""),
    title: str = Form(""),
    file: UploadFile = File(...),
) -> JSONResponse:
    if not rag_store.get_domain(domain_id):
        raise HTTPException(status_code=404, detail="Domain not found")
    filename = file.filename or "upload"
    ext = os.path.splitext(filename.lower())[1]
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    content = file.file.read()
    text, _ = extract_text_from_upload(content, filename)
    if not text:
        raise HTTPException(status_code=400, detail="No extractable text found")
    if not title:
        title = filename
    doc = config_store.create_document(
        domain_id=domain_id,
        title=title,
        source=source or filename,
        source_type=source_type,
        content=text[:5000],
    )
    rag_store.invalidate(domain_id)
    return JSONResponse(doc)


@app.get("/api/config/documents/all", response_class=JSONResponse)
def list_all_documents(domain_id: str = "") -> JSONResponse:
    domain_id = domain_id or ""
    builtin_docs = _load_builtin_documents(domain_id)
    custom_docs = {item["doc_id"]: item for item in config_store.list_documents(domain_id or None)}
    disabled = set(config_store.get_disabled_ids("document"))
    items: List[Dict[str, object]] = []
    for doc in builtin_docs:
        doc_id = doc["doc_id"]
        override = custom_docs.get(doc_id)
        entry = {**doc, "origin": "builtin", "disabled": doc_id in disabled}
        if override:
            entry.update(override)
            entry["origin"] = "custom"
            entry["overrides_builtin"] = True
        items.append(entry)
    for doc_id, doc in custom_docs.items():
        if any(doc_id == item["doc_id"] for item in builtin_docs):
            continue
        items.append({**doc, "origin": "custom", "disabled": doc_id in disabled})
    return JSONResponse({"items": items})


@app.put("/api/config/documents/{doc_id}", response_class=JSONResponse)
def update_document(doc_id: str, request_body: UpdateDocumentRequest) -> JSONResponse:
    custom_doc = config_store.get_document(doc_id)
    builtin_docs = {item["doc_id"]: item for item in _load_builtin_documents()}
    updates = request_body.dict(exclude_unset=True)
    if custom_doc:
        updated = config_store.update_document(doc_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Document not found")
        rag_store.invalidate(updated["domain_id"])
        return JSONResponse(updated)
    if doc_id in builtin_docs:
        base = builtin_docs[doc_id]
        merged = {
            "domain_id": base.get("domain_id", ""),
            "title": base.get("title", ""),
            "source": base.get("source", ""),
            "source_type": base.get("source_type", "custom"),
            "content": base.get("content", ""),
        }
        merged.update(updates)
        doc = config_store.create_document(
            domain_id=merged["domain_id"],
            title=merged["title"],
            source=merged["source"],
            source_type=merged["source_type"],
            content=merged["content"],
            doc_id=doc_id,
        )
        rag_store.invalidate(merged["domain_id"])
        return JSONResponse(doc)
    raise HTTPException(status_code=404, detail="Document not found")


@app.delete("/api/config/documents/{doc_id}", response_class=JSONResponse)
def delete_document(doc_id: str) -> JSONResponse:
    custom_doc = config_store.get_document(doc_id)
    builtin_docs = {item["doc_id"]: item for item in _load_builtin_documents()}
    if custom_doc:
        config_store.delete_document(doc_id)
        rag_store.invalidate(custom_doc["domain_id"])
        return JSONResponse({"status": "deleted"})
    if doc_id in builtin_docs:
        config_store.disable_item("document", doc_id)
        rag_store.invalidate(builtin_docs[doc_id]["domain_id"])
        return JSONResponse({"status": "disabled"})
    raise HTTPException(status_code=404, detail="Document not found")


@app.post("/api/config/documents/{doc_id}/enable", response_class=JSONResponse)
def enable_document(doc_id: str) -> JSONResponse:
    config_store.enable_item("document", doc_id)
    return JSONResponse({"status": "enabled"})


@app.get("/api/config/crawlers", response_class=JSONResponse)
def list_crawlers() -> JSONResponse:
    return JSONResponse({"items": config_store.list_crawlers()})


@app.post("/api/config/crawlers", response_class=JSONResponse)
def create_crawler(request_body: CreateCrawlerRequest) -> JSONResponse:
    try:
        crawler = config_store.create_crawler(
            domain_id=request_body.domain_id,
            name=request_body.name,
            url=request_body.url,
            source_type=request_body.source_type,
            description=request_body.description,
            interval_minutes=request_body.interval_minutes,
            enabled=request_body.enabled,
            source_id=request_body.source_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(crawler)


@app.put("/api/config/crawlers/{source_id}", response_class=JSONResponse)
def update_crawler(source_id: str, request_body: UpdateCrawlerRequest) -> JSONResponse:
    updates = request_body.dict(exclude_unset=True)
    crawler = config_store.update_crawler(source_id, updates)
    if not crawler:
        raise HTTPException(status_code=404, detail="Crawler not found")
    return JSONResponse(crawler)


@app.delete("/api/config/crawlers/{source_id}", response_class=JSONResponse)
def delete_crawler(source_id: str) -> JSONResponse:
    config_store.delete_crawler(source_id)
    return JSONResponse({"status": "deleted"})


@app.post("/api/config/crawlers/{source_id}/run", response_class=JSONResponse)
def run_crawler(source_id: str) -> JSONResponse:
    sources = {item["source_id"]: item for item in config_store.list_crawlers()}
    source = sources.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Crawler not found")
    result = crawler_service.run_source(source)
    return JSONResponse(result)


@app.post("/api/config/crawlers/run_all", response_class=JSONResponse)
def run_all_crawlers() -> JSONResponse:
    crawler_service.run_due_sources()
    return JSONResponse({"status": "ok"})


@app.post("/api/quick-insights", response_class=JSONResponse)
def create_quick_insight(payload: Dict[str, object]) -> JSONResponse:
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    llm = create_llm_client()
    max_tokens = int(os.getenv("QUICK_MAX_TOKENS", "8192"))
    max_bytes = int(os.getenv("QUICK_MAX_HTML_BYTES", "1000000"))
    html_content = build_quick_html_report(prompt, llm, max_tokens=max_tokens)
    html_bytes = html_content.encode("utf-8")
    if len(html_bytes) > max_bytes:
        html_content = html_bytes[:max_bytes].decode("utf-8", errors="ignore")
    summary = html_content[:200].replace("\n", " ")
    title = prompt[:80]
    report_payload = {
        "title": title,
        "objective": "",
        "prompt": prompt,
        "summary": summary,
        "html_content": html_content,
    }
    report_id = quick_store.create_report(report_payload, title=title)
    file_path = os.path.join(QUICK_REPORTS_DIR, f"{report_id}.html")
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(html_content)
    file_url = f"/quick-reports-files/{report_id}.html"
    report_payload.update({"report_id": report_id, "file_path": file_path, "file_url": file_url})
    quick_store.upsert_report(report_id, report_payload, title=title)
    return JSONResponse(report_payload)


@app.get("/api/quick-insights", response_class=JSONResponse)
def list_quick_insights(limit: int = 20) -> JSONResponse:
    limit = min(max(limit, 1), 200)
    items = quick_store.list_reports(limit=limit)
    return JSONResponse({"items": items})


@app.get("/api/quick-insights/{report_id}", response_class=JSONResponse)
def get_quick_insight(report_id: str) -> JSONResponse:
    payload = quick_store.get_report(report_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Report not found")
    file_path = payload.get("file_path") or os.path.join(QUICK_REPORTS_DIR, f"{report_id}.html")
    file_url = payload.get("file_url") or f"/quick-reports-files/{report_id}.html"
    html_content = payload.get("html_content", "")
    if html_content and not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(html_content)
    payload.update({"file_path": file_path, "file_url": file_url})
    if not payload.get("title"):
        payload["title"] = (payload.get("prompt", "") or "")[:80]
    return JSONResponse(payload)


@app.delete("/api/quick-insights/{report_id}", response_class=JSONResponse)
def delete_quick_insight(report_id: str) -> JSONResponse:
    report = quick_store.get_report(report_id)
    deleted = quick_store.delete_report(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")
    file_path = None
    if report:
        file_path = report.get("file_path")
    if not file_path:
        file_path = os.path.join(QUICK_REPORTS_DIR, f"{report_id}.html")
    if file_path:
        try:
            os.remove(file_path)
        except OSError:
            pass
    return JSONResponse({"status": "deleted"})


@app.put("/api/quick-insights/{report_id}", response_class=JSONResponse)
def update_quick_insight(report_id: str, payload: Dict[str, object]) -> JSONResponse:
    report = quick_store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    html_content = str(payload.get("html_content", report.get("html_content", ""))).strip()
    summary = str(payload.get("summary", "")).strip()
    if not summary and html_content:
        summary = html_content[:200].replace("\n", " ")
    if not summary:
        summary = str(report.get("summary", "")).strip()
    file_path = report.get("file_path") or os.path.join(QUICK_REPORTS_DIR, f"{report_id}.html")
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(html_content)
    file_url = report.get("file_url") or f"/quick-reports-files/{report_id}.html"
    title = report.get("title") or (report.get("prompt", "") or "")[:80]
    updated_payload = {
        **report,
        "title": title,
        "objective": report.get("objective", ""),
        "summary": summary,
        "html_content": html_content,
        "file_path": file_path,
        "file_url": file_url,
    }
    quick_store.update_report(report_id, updated_payload, title=title)
    return JSONResponse(updated_payload)


@app.get("/api/config/report-templates/all", response_class=JSONResponse)
def list_report_templates() -> JSONResponse:
    return JSONResponse({"items": _list_report_templates()})


@app.post("/api/config/report-templates", response_class=JSONResponse)
def create_report_template(request_body: CreateReportTemplateRequest) -> JSONResponse:
    try:
        template = config_store.create_report_template(
            name=request_body.name,
            description=request_body.description,
            sections=request_body.sections,
            template_id=request_body.template_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(template)


@app.put("/api/config/report-templates/{template_id}", response_class=JSONResponse)
def update_report_template(
    template_id: str, request_body: UpdateReportTemplateRequest
) -> JSONResponse:
    custom_templates = {item["template_id"]: item for item in config_store.list_report_templates()}
    builtin_templates = {tpl["template_id"]: tpl for tpl in BUILTIN_REPORT_TEMPLATES}
    updates = request_body.dict(exclude_unset=True)
    if template_id in custom_templates:
        updated = config_store.update_report_template(template_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Template not found")
        return JSONResponse(updated)
    if template_id in builtin_templates:
        base = builtin_templates[template_id]
        merged = {
            "name": base.get("name", template_id),
            "description": base.get("description", ""),
            "sections": base.get("sections", []),
        }
        merged.update(updates)
        template = config_store.create_report_template(
            name=merged["name"],
            description=merged["description"],
            sections=merged["sections"],
            template_id=template_id,
        )
        return JSONResponse(template)
    raise HTTPException(status_code=404, detail="Template not found")


@app.delete("/api/config/report-templates/{template_id}", response_class=JSONResponse)
def delete_report_template(template_id: str) -> JSONResponse:
    custom_templates = {item["template_id"]: item for item in config_store.list_report_templates()}
    builtin_templates = {tpl["template_id"]: tpl for tpl in BUILTIN_REPORT_TEMPLATES}
    if template_id in custom_templates:
        config_store.delete_report_template(template_id)
        return JSONResponse({"status": "deleted"})
    if template_id in builtin_templates:
        config_store.disable_item("report_template", template_id)
        return JSONResponse({"status": "disabled"})
    raise HTTPException(status_code=404, detail="Template not found")


@app.post("/api/config/report-templates/{template_id}/enable", response_class=JSONResponse)
def enable_report_template(template_id: str) -> JSONResponse:
    config_store.enable_item("report_template", template_id)
    return JSONResponse({"status": "enabled"})


@app.get("/health", response_class=JSONResponse)
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
