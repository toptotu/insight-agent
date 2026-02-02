# insight-agent

Multi-agent + Skill + RAG insight platform with a web UI. The platform runs on
Ubuntu 22.04 ECS and uses the Aliyun LLM API when configured. If no API key is
provided, the system runs in mock mode so the UI can still work end-to-end.

## Quick start

```bash
bash scripts/setup.sh
bash scripts/run.sh
```

Open http://localhost:8000 in your browser.

## UI pages

- `/ui/insight`: 洞察工作台
- `/ui/report/{task_id}`: PPT风格洞察报告
- `/ui/history`: 历史洞察列表
- `/ui/config`: 自定义Agent/Skill/RAG配置

The report page renders charts via Chart.js (CDN).

## Editing defaults and overrides

- Editing a built-in item creates an override in the database.
- Deleting a built-in item disables it (can be re-enabled from the list).
- Custom items are stored in `data/store.db`.

## Auto crawling sources

Configure crawlers in `/ui/config` under "信息源配置与自动爬取".
The service will fetch content on schedule and store it in the RAG store.

Environment knobs:

```bash
export CRAWLER_CHECK_INTERVAL=60
export CRAWLER_MAX_CHARS=5000
```

## Report templates

Use `/ui/config` to manage PPT report templates. The insight page can select a
template to control slide layout (summary, per-topic, closing, etc.).

## RAG file upload

Upload PDF/DOCX/PPTX files in `/ui/config` -> "RAG上传" and the content will be
ingested and indexed automatically.

## Environment variables

Copy `.env.example` to `.env` and set your Aliyun API key to enable LLM mode.
If `ALI_API_KEY` is not set, the platform uses mock responses.

```bash
export ALI_API_KEY=your_api_key_here
export ALI_API_BASE=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
export ALI_MODEL=qwen-plus
```

## Data and configuration

- `data/domains.json` defines domains and RAG sources.
- `data/agents.json` defines available agents.
- `data/skills.json` defines skills.
- `data/6g/*.jsonl` contains sample documents for the 6G domain.

Add new domains by extending `data/domains.json` and providing new JSONL files.

## Custom configuration

Use `/ui/config` to create custom domains, agents, skills, and RAG documents.
Custom data is stored in `data/store.db`.

## FAISS vector retrieval

The platform uses FAISS if available (default) and falls back to the
lightweight TF-like retriever if disabled.

```bash
export USE_FAISS=1
export FAISS_DIM=256
```
