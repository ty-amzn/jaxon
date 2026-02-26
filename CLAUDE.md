# AI Assistant — Project Guide

## Quick Start
```bash
cp .env.example .env   # set ANTHROPIC_API_KEY
cp -r data.example data # seed data directory (agents, skills, identity)
uv sync --all-extras
playwright install chromium   # browser tool (one-time)
uv run assistant chat   # interactive mode
uv run assistant serve  # API server at :51430
uv run pytest           # run tests
```

## Architecture
Single-user personal AI assistant with multi-provider LLM support (Claude, OpenAI, Gemini, Ollama, AWS Bedrock), streaming CLI (Rich + prompt_toolkit), tool use with permission gates, persistent memory, agent delegation, and first-run onboarding.

### Key Directories
- `src/assistant/` — all source code
- `data.example/` — template data directory (copy to `data/` on first run)
- `data/` — runtime data directory (gitignored, personal)
  - `memory/` — IDENTITY.md (personality), MEMORY.md (facts), daily logs
  - `skills/` — skill definitions (.md files)
  - `agents/` — agent definitions (.yaml files)
  - `threads/` — saved conversation threads
  - `workflows/` — workflow YAML definitions
  - `backups/` — config backup tarballs
  - `logs/` — audit.jsonl, app.log
  - `db/` — SQLite FTS5 search index, embeddings, scheduler

### Data Flow
User input → slash command dispatch OR → SessionManager → MemoryManager (system prompt + skills + identity) → LLMRouter → Claude/OpenAI/Gemini/Ollama/BedrockClient → Rich Live rendering → save to daily log + FTS5 + embeddings

### Config
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` — no prefix, read via `validation_alias`
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
1. Skills system — markdown files in `data/skills/`, auto-loaded into system prompt
2. Ollama integration — `llm/ollama.py`, OpenAI-compatible API client
3. LLM router — `llm/router.py`, routes between providers by complexity
4. Web search tool — `tools/web_search.py`, SearXNG integration
5. Vector search — `memory/embeddings.py`, Ollama embedding service
6. Conversation threading — `gateway/thread_store.py`, `/thread` command
7. Rich media support — `cli/media.py`, `@image:` syntax

## Phase 3 (Integrations) — COMPLETE
- Telegram bot (`telegram/bot.py`)
- WhatsApp bot (`whatsapp/bot.py`) — neonize linked-device QR pairing
- APScheduler automations (`scheduler/`)
- Watchdog file monitoring (`watchdog_monitor/monitor.py`)
- Notification dispatcher (`core/notifications.py`)

## Phase 4 (Workflows & Polish) — COMPLETE
1. Workflow engine — YAML-defined multi-step chains, approval gates
2. Webhook triggers — HMAC-SHA256 validation, maps to workflows
3. DND notifications — quiet hours with urgent bypass
4. Input sanitization — prompt injection and path traversal protection
5. Config backup/restore — `/backup` command

## Phase 5 (Agentic Features) — COMPLETE
1. Multi-provider LLM — OpenAI, Gemini, Bedrock via `llm/openai_compat.py`, `llm/openai_client.py`, `llm/gemini.py`, `llm/bedrock.py`
2. Configurable `max_tool_rounds` — `ASSISTANT_MAX_TOOL_ROUNDS`, per-agent override in YAML
3. Graceful summary on tool limit — final LLM call without tools to summarize progress
4. `/clear` command — clear session, history, memory, search, or all
5. Agentic memory — `tools/memory_tool.py`: `memory_search` (read), `memory_forget` (delete)
6. Agentic skill management — `tools/skill_tool.py`: `manage_skill` (create/edit/delete/list)
7. Personality/identity — `update_identity` tool, first-run onboarding flow
8. Approval prompt fix — pause Rich Live widget during permission prompts

## Phase 6 (Background Agents)
1. Background agent delegation — `agents/background.py`: `BackgroundTaskManager`, `current_delivery` ContextVar
2. `delegate_to_agent` now accepts `background=true` for fire-and-forget execution
3. `task_status` tool — check background task progress/results
4. `/tasks` command — list and inspect background tasks in CLI
5. Delivery callbacks — background results delivered async to CLI, Telegram, WhatsApp
6. Auto-approve permissions — background agents use `_auto_approve`, scoped by YAML `allowed_tools`
7. In-memory task store — bounded deque of 50 tasks, no persistence

## Phase 7 (Browser Tool)
1. Playwright browser tool — `tools/browser_tool.py`: `browse_web` with extract/screenshot/click/fill/evaluate actions
2. Singleton browser — lazy-initialized Chromium, pages created per-call for isolation
3. Permission-gated — extract/screenshot/evaluate auto-approved (NETWORK_READ), click/fill require approval (NETWORK_WRITE)
4. Browser shutdown wired into app lifespan (`core/events.py`)

## Phase 8 (YouTube & Reddit Tools)
1. YouTube tool — `tools/youtube_tool.py`: `youtube_search` with search/video_info/transcript actions via yt-dlp
2. Reddit tool — `tools/reddit_tool.py`: `reddit_search` with search/subreddit/post actions via public JSON API
3. Both gated by `youtube_enabled` / `reddit_enabled` config flags, classified as NETWORK_READ (auto-approved)

## User Documentation
- `docs/user-guide.md` — comprehensive user guide (all features)
- `docs/quick-reference.md` — command cheat sheet
