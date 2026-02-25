# AI Assistant

A self-hosted personal AI assistant with multi-provider LLM support, streaming CLI, tool use, persistent memory, agent delegation, Telegram/WhatsApp integration, scheduled automations, and a workflow engine.

## Features

- **Multi-provider LLM support** — Claude, OpenAI, Gemini, and Ollama with smart routing
- **Streaming CLI** — Rich-rendered chat with prompt_toolkit input
- **First-run onboarding** — Guided setup for name, personality, and communication style
- **Tool use with permission gates** — Shell, file, HTTP, web search, memory, and skill tools with approval prompts
- **Persistent memory** — Identity, durable memory, daily logs, full-text search (FTS5), vector search
- **Agentic memory management** — The assistant can search, recall, and forget memories via tool calls
- **Agentic skill management** — Create, edit, and delete skills through conversation
- **Customizable personality** — Update the assistant's identity and communication style via chat
- **Skills** — Markdown-defined prompt extensions auto-loaded into context
- **Agent delegation** — YAML-defined sub-agents (researcher, coder, etc.) with scoped tools
- **Conversation threading** — Save, load, and export named conversations
- **Image support** — Send images to vision-capable models with `@image:` syntax
- **Web search** — SearXNG-powered web search tool
- **YouTube** — Search videos, get metadata, and extract transcripts via yt-dlp
- **Reddit** — Search posts, browse subreddits, and read discussions via public API
- **Telegram bot** — Chat with your assistant from Telegram
- **WhatsApp bot** — Chat via WhatsApp linked-device QR code pairing (neonize)
- **Scheduler** — Cron, interval, and one-shot reminders with SQLite persistence
- **File monitoring** — Watchdog-based directory monitoring with notifications
- **Workflow engine** — Multi-step YAML-defined automation chains with approval gates
- **Webhooks** — Trigger workflows from external services with HMAC validation
- **Do Not Disturb** — Suppress notifications during configurable quiet hours
- **Backups** — One-command data snapshots and restore
- **Input sanitization** — Automatic prompt injection and path traversal protection
- **Plugins** — Extensible plugin system for custom tools and skills
- **API server** — FastAPI backend powering Telegram, scheduler, and webhooks
- **Docker ready** — Single-command deployment with health checks

## Quick Start

### Local Development

```bash
git clone https://github.com/ty-amzn/ai-assistant.git
cd ai-assistant

cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY (or configure another provider)

uv sync --all-extras
uv run assistant chat
```

On first launch, the assistant will ask for your name and preferred communication style.

### Docker

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

docker compose up -d
```

The API server starts at `http://localhost:51430`. Data persists in the `./data` volume mount.

## Deployment

### Docker Compose (Recommended)

The included `docker-compose.yml` provides a production-ready setup:

```yaml
services:
  assistant:
    build: .
    ports:
      - "51430:51430"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:51430/health').raise_for_status()"]
      interval: 30s
      timeout: 5s
      retries: 3
```

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f assistant

# Rebuild after code changes
docker compose up -d --build

# Stop
docker compose down
```

The container:
- Exposes port 51430 for the API, webhooks, and Telegram webhook mode
- Mounts `./data` for persistent storage (memory, threads, databases, logs)
- Restarts automatically unless explicitly stopped
- Includes a health check that polls `/health` every 30 seconds

### Docker with Ollama

To run with a local LLM alongside the assistant:

```yaml
# docker-compose.yml
services:
  assistant:
    build: .
    ports:
      - "51430:51430"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    depends_on:
      - ollama
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:51430/health').raise_for_status()"]
      interval: 30s
      timeout: 5s
      retries: 3

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

```bash
# .env
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_OLLAMA_BASE_URL=http://ollama:11434
ASSISTANT_OLLAMA_MODEL=llama3.2

# Pull the model after starting
docker compose exec ollama ollama pull llama3.2
```

### Docker with SearXNG

Add web search capabilities:

```yaml
services:
  # ... assistant and ollama services above ...

  searxng:
    image: searxng/searxng
    ports:
      - "8888:8080"
    volumes:
      - ./searxng:/etc/searxng
    restart: unless-stopped
```

```bash
# .env
ASSISTANT_WEB_SEARCH_ENABLED=true
ASSISTANT_SEARXNG_URL=http://searxng:8080
```

### Manual Deployment

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/ty-amzn/ai-assistant.git
cd ai-assistant
uv sync --all-extras

# Configure
cp .env.example .env
# Edit .env with your settings

# Run the API server (required for Telegram, scheduler, webhooks)
uv run assistant serve --host 0.0.0.0

# Or run the interactive CLI
uv run assistant chat
```

### Reverse Proxy (nginx)

For production deployments behind a reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name assistant.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:51430;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Environment Variables

See the [Configuration Reference](docs/USER_GUIDE.md#configuration-reference) for the full list. Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `ASSISTANT_MODEL` | `claude-sonnet-4-20250514` | Claude model |
| `ASSISTANT_DEFAULT_PROVIDER` | `claude` | LLM provider (claude/openai/gemini/ollama) |
| `ASSISTANT_MAX_TOOL_ROUNDS` | `10` | Max tool calls per response |
| `ASSISTANT_DATA_DIR` | `./data` | Persistent data directory |
| `ASSISTANT_HOST` | `127.0.0.1` | API server bind address |
| `ASSISTANT_PORT` | `51430` | API server port |
| `ASSISTANT_OLLAMA_ENABLED` | `false` | Enable local LLM routing |
| `ASSISTANT_AGENTS_ENABLED` | `false` | Enable agent delegation |
| `ASSISTANT_TELEGRAM_ENABLED` | `false` | Enable Telegram bot |
| `ASSISTANT_WHATSAPP_ENABLED` | `false` | Enable WhatsApp bot |
| `ASSISTANT_SCHEDULER_ENABLED` | `false` | Enable scheduled jobs |
| `ASSISTANT_WEBHOOK_ENABLED` | `false` | Enable webhook endpoints |
| `ASSISTANT_YOUTUBE_ENABLED` | `false` | Enable YouTube search/transcripts |
| `ASSISTANT_REDDIT_ENABLED` | `false` | Enable Reddit search/browsing |

## Usage

### Interactive CLI

```bash
uv run assistant chat
```

Type messages to chat. Use `/help` to see all slash commands.

### Personalizing Your Assistant

On first run, you'll be asked for your name and preferred communication style. You can change these anytime:

```
You: Be more casual and use humor
You: Call me by my first name
You: Switch to a formal, concise tone
```

The assistant uses the `update_identity` tool to persist personality changes to `IDENTITY.md`.

### Agentic Memory

The assistant can search and manage its own memory:

```
You: What did we discuss about authentication last week?
You: Forget about the old project notes
You: Remember that I prefer Python over JavaScript
```

### Agentic Skills

Create and manage skills through conversation:

```
You: Create a skill for summarizing emails
You: Edit the code-review skill to include accessibility checks
You: Delete the old summarizer skill
```

### API Server

```bash
uv run assistant serve
```

Required for Telegram, scheduler, webhooks, and file monitoring. Starts at `http://localhost:51430`.

### Agent Delegation

Define specialized agents in `data/agents/` as YAML files:

```yaml
# data/agents/researcher.yaml
name: researcher
description: Research agent — searches the web and reads files
system_prompt: |
  You are a research assistant. Search thoroughly and cite sources.
allowed_tools:
  - web_search
  - http_request
  - read_file
  - memory_search
max_tool_rounds: 50
```

The main assistant can delegate tasks to agents automatically when `ASSISTANT_AGENTS_ENABLED=true`.

### Example Workflows

**Create a skill:**
```bash
cat > data/skills/summarize.md << 'EOF'
# Summarizer
When asked to summarize, produce:
1. A one-sentence TL;DR
2. Key points as bullet points
3. Action items if any
EOF
```

**Define a workflow:**
```bash
cat > data/workflows/health-check.yaml << 'EOF'
name: health-check
description: Check system health
trigger: webhook
steps:
  - name: disk-usage
    tool: shell_exec
    args:
      command: "df -h / | tail -1"
  - name: uptime
    tool: shell_exec
    args:
      command: "uptime"
EOF
```

**Trigger via webhook:**
```bash
curl -X POST http://localhost:51430/webhooks/health-check \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Back up your data:**
```
/backup create before-upgrade
```

## Project Structure

```
src/assistant/
├── cli/                # CLI app, chat interface, slash commands
├── core/               # Config, logging, events, notifications
├── gateway/            # Sessions, permissions, threads, webhooks
├── llm/                # Claude, OpenAI, Gemini, Ollama clients + router
├── memory/             # Identity, durable memory, search, embeddings, skills
├── tools/              # Shell, file, HTTP, web search, memory, skill tools
├── scheduler/          # APScheduler, job store, workflows
├── telegram/           # Telegram bot and handlers
├── whatsapp/           # WhatsApp bot and handlers (neonize)
├── watchdog_monitor/   # File system monitoring
├── plugins/            # Plugin system
└── agents/             # Agent delegation and orchestration
```

## Documentation

- **[User Guide](docs/USER_GUIDE.md)** — comprehensive feature documentation
- **[Quick Reference](docs/QUICK_REFERENCE.md)** — command cheat sheet

## Development

```bash
uv sync --all-extras    # Install with dev dependencies
uv run pytest           # Run tests (138 tests)
uv run pytest -v        # Verbose output
```

## License

Private project.
