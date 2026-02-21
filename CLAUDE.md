# AI Assistant — Project Guide

## Quick Start
```bash
cp .env.example .env   # set ANTHROPIC_API_KEY
uv sync --all-extras
uv run assistant chat   # interactive mode
uv run assistant serve  # API server at :8000
uv run pytest           # 29 tests
```

## Architecture
Single-user personal AI assistant with Claude API, streaming CLI (Rich + prompt_toolkit), tool use with permission gates, and persistent memory.

### Key Directories
- `src/assistant/` — all source code
- `data/memory/` — IDENTITY.md, MEMORY.md, daily logs
- `data/logs/` — audit.jsonl, app.log
- `data/db/` — SQLite FTS5 search index

### Data Flow
User input → slash command dispatch OR → SessionManager → MemoryManager (system prompt) → ClaudeClient.stream_with_tool_loop() → Rich Live rendering → save to daily log + FTS5

### Config
- `ANTHROPIC_API_KEY` — no prefix, read via `validation_alias`
- All other settings use `ASSISTANT_` prefix (e.g. `ASSISTANT_MODEL`, `ASSISTANT_DATA_DIR`)

## Phase 1 (Foundation) — COMPLETE
All 12 steps implemented, 29 tests passing:
1. Project skeleton + config (`core/config.py`, `pyproject.toml`)
2. Logging (`core/logging.py` — AuditLogger JSONL)
3. Memory system (`memory/` — identity, durable, daily_log, search via FTS5, manager facade)
4. LLM client (`llm/client.py` — streaming + tool-use loop, `llm/types.py`, `llm/context.py`)
5. Permission system (`gateway/permissions.py` — injected approval callback)
6. Tool system (`tools/` — registry, shell, file, HTTP; `llm/tools.py`)
7. Session manager (`gateway/session.py` — in-memory)
8. CLI (`cli/app.py` Click, `cli/chat.py` Rich Live + prompt_toolkit)
9. Slash commands (`cli/commands/` — help, status, memory, history, cancel, config, skills stub)
10. FastAPI server (`app.py`, `api/routes.py` /health, `core/events.py` lifespan)
11. Docker (`Dockerfile` uv-based, `docker-compose.yml` with healthcheck)
12. Tests (`tests/` — config, memory, session, permissions, commands, LLM types)

## Future Phases (NOT STARTED)
- **Phase 2**: Skills system — custom workflows, skill files in `data/skills/`
- **Phase 3**: Telegram integration, APScheduler automations, watchdog file monitoring
