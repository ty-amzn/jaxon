# AI Assistant — Project Guide

## Quick Start
```bash
cp .env.example .env   # set ANTHROPIC_API_KEY
uv sync --all-extras
uv run assistant chat   # interactive mode
uv run assistant serve  # API server at :8000
uv run pytest           # run tests
```

## Architecture
Single-user personal AI assistant with Claude API, streaming CLI (Rich + prompt_toolkit), tool use with permission gates, and persistent memory.

### Key Directories
- `src/assistant/` — all source code
- `data/memory/` — IDENTITY.md, MEMORY.md, daily logs
- `data/skills/` — skill definitions (.md files)
- `data/threads/` — saved conversation threads
- `data/workflows/` — workflow YAML definitions
- `data/backups/` — config backup tarballs
- `data/logs/` — audit.jsonl, app.log
- `data/db/` — SQLite FTS5 search index, embeddings

### Data Flow
User input → slash command dispatch OR → SessionManager → MemoryManager (system prompt + skills) → LLMRouter → ClaudeClient/OllamaClient → Rich Live rendering → save to daily log + FTS5 + embeddings

### Config
- `ANTHROPIC_API_KEY` — no prefix, read via `validation_alias`
- All other settings use `ASSISTANT_` prefix (e.g. `ASSISTANT_MODEL`, `ASSISTANT_DATA_DIR`)

## Phase 1 (Foundation) — COMPLETE
All 12 steps implemented:
1. Project skeleton + config (`core/config.py`, `pyproject.toml`)
2. Logging (`core/logging.py` — AuditLogger JSONL)
3. Memory system (`memory/` — identity, durable, daily_log, search via FTS5, manager facade)
4. LLM client (`llm/client.py` — streaming + tool-use loop, `llm/types.py`, `llm/context.py`)
5. Permission system (`gateway/permissions.py` — injected approval callback)
6. Tool system (`tools/` — registry, shell, file, HTTP; `llm/tools.py`)
7. Session manager (`gateway/session.py` — in-memory)
8. CLI (`cli/app.py` Click, `cli/chat.py` Rich Live + prompt_toolkit)
9. Slash commands (`cli/commands/` — help, status, memory, history, cancel, config, skills)
10. FastAPI server (`app.py`, `api/routes.py` /health, `core/events.py` lifespan)
11. Docker (`Dockerfile` uv-based, `docker-compose.yml` with healthcheck)
12. Tests (`tests/` — config, memory, session, permissions, commands, LLM types)

## Phase 2 (Local Intelligence & Skills) — COMPLETE
All 7 features implemented:

### 1. Skills System
- Markdown skill files in `data/skills/`
- Auto-loaded into system prompt
- `/skills` command to list/view/reload

### 2. Ollama Integration
- `llm/base.py` — Abstract BaseLLMClient interface
- `llm/ollama.py` — OpenAI-compatible API client
- Config: `OLLAMA_ENABLED`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`

### 3. LLM Router
- `llm/router.py` — Routes between Claude and Ollama
- Tool use → Claude, Complex → Claude, Simple → Ollama
- Config: `LOCAL_MODEL_THRESHOLD_TOKENS`

### 4. Web Search Tool
- `tools/web_search.py` — SearXNG integration
- Config: `WEB_SEARCH_ENABLED`, `SEARXNG_URL`

### 5. Vector Search
- `memory/embeddings.py` — Embedding service via Ollama
- Semantic similarity search over history
- Config: `VECTOR_SEARCH_ENABLED`, `EMBEDDING_MODEL`

### 6. Conversation Threading
- `gateway/thread_store.py` — JSON persistence
- `/thread` command: new, save, load, list, export, delete
- Threads stored in `data/threads/`

### 7. Rich Media Support
- `cli/media.py` — Image loading and encoding
- Syntax: `@image:/path/to/image.png`
- Config: `MAX_MEDIA_SIZE_MB`

## Phase 3 (Integrations) — COMPLETE
- Telegram bot integration (`telegram/bot.py`)
- APScheduler automations (`scheduler/` — jobs, manager, store, tool)
- Watchdog file monitoring (`watchdog_monitor/monitor.py`)
- Notification dispatcher (`core/notifications.py`)

## Phase 4 (Workflows & Polish) — COMPLETE
All features implemented:

### 1. Workflow Engine
- `scheduler/workflow.py` — WorkflowDefinition, WorkflowRunner, WorkflowManager
- YAML-defined multi-step chains in `data/workflows/`
- Step-by-step execution with approval gates
- `/workflow` command: list, run, reload

### 2. Webhook Triggers
- `gateway/webhooks.py` — FastAPI router for `POST /webhooks/{name}`
- HMAC-SHA256 signature validation
- Maps webhooks to workflows by name
- `/webhook` command: list, test
- Config: `WEBHOOK_ENABLED`, `WEBHOOK_SECRET`

### 3. DND Notifications
- Extended `NotificationDispatcher` with DND window support
- Messages queued during DND, urgent messages bypass
- Config: `DND_ENABLED`, `DND_START`, `DND_END`, `DND_ALLOW_URGENT`

### 4. Input Sanitization
- `tools/sanitize.py` — strips prompt injection patterns, sanitizes file paths
- Applied at `ToolRegistry.execute()` chokepoint before every handler

### 5. Config Backup/Restore
- `/backup` command: create, list, restore
- Tarballs stored in `data/backups/`

## User Documentation
- `docs/USER_GUIDE.md` — comprehensive user guide (all features)
- `docs/QUICK_REFERENCE.md` — command cheat sheet