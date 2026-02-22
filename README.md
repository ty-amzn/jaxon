# AI Assistant

A self-hosted personal AI assistant built on Claude, with a streaming CLI, tool use, persistent memory, local LLM routing, Telegram integration, scheduled automations, workflow engine, and more.

## Features

- **Streaming CLI** — Rich-rendered chat with prompt_toolkit input
- **Tool use with permission gates** — Shell, file, HTTP, web search tools with approval prompts for destructive actions
- **Persistent memory** — Identity, durable memory, daily logs, full-text search (FTS5), vector search
- **Skills** — Markdown-defined prompt extensions auto-loaded into context
- **Conversation threading** — Save, load, and export named conversations
- **Image support** — Send images to vision-capable models with `@image:` syntax
- **Ollama integration** — Smart routing between Claude and local models for privacy/cost savings
- **Web search** — SearXNG-powered web search tool
- **Telegram bot** — Chat with your assistant from Telegram
- **WhatsApp bot** — Chat with your assistant from WhatsApp via linked-device QR code pairing (neonize)
- **Scheduler** — Cron, interval, and one-shot reminders with SQLite persistence
- **File monitoring** — Watchdog-based directory monitoring with notifications
- **Workflow engine** — Multi-step YAML-defined automation chains with approval gates
- **Webhooks** — Trigger workflows from external services with HMAC validation
- **Do Not Disturb** — Suppress notifications during configurable quiet hours
- **Backups** — One-command data snapshots and restore
- **Input sanitization** — Automatic prompt injection and path traversal protection
- **Plugins & agents** — Extensible plugin system and agent delegation
- **API server** — FastAPI backend powering Telegram, scheduler, and webhooks
- **Docker ready** — Single-command deployment with health checks

## Quick Start

### Local Development

```bash
git clone https://github.com/ty-amzn/ai-assistant.git
cd ai-assistant

cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

uv sync --all-extras
uv run assistant chat
```

### Docker

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

docker compose up -d
```

The API server starts at `http://localhost:8000`. Data persists in the `./data` volume mount.

## Deployment

### Docker Compose (Recommended)

The included `docker-compose.yml` provides a production-ready setup:

```yaml
services:
  assistant:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"]
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
- Exposes port 8000 for the API, webhooks, and Telegram webhook mode
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
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    depends_on:
      - ollama
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"]
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
        proxy_pass http://127.0.0.1:8000;
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
| `ANTHROPIC_API_KEY` | — | **Required.** Anthropic API key |
| `ASSISTANT_MODEL` | `claude-sonnet-4-20250514` | Claude model |
| `ASSISTANT_DATA_DIR` | `./data` | Persistent data directory |
| `ASSISTANT_HOST` | `127.0.0.1` | API server bind address |
| `ASSISTANT_PORT` | `8000` | API server port |
| `ASSISTANT_OLLAMA_ENABLED` | `false` | Enable local LLM routing |
| `ASSISTANT_TELEGRAM_ENABLED` | `false` | Enable Telegram bot |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token |
| `ASSISTANT_WHATSAPP_ENABLED` | `false` | Enable WhatsApp bot |
| `ASSISTANT_WHATSAPP_ALLOWED_NUMBERS` | `[]` | Allowed phone numbers (E.164) |
| `ASSISTANT_SCHEDULER_ENABLED` | `false` | Enable scheduled jobs |
| `ASSISTANT_WEBHOOK_ENABLED` | `false` | Enable webhook endpoints |
| `ASSISTANT_DND_ENABLED` | `false` | Enable Do Not Disturb |

## Usage

### Interactive CLI

```bash
uv run assistant chat
```

Type messages to chat. Use `/help` to see all slash commands.

### API Server

```bash
uv run assistant serve
```

Required for Telegram, scheduler, webhooks, and file monitoring. Starts at `http://localhost:8000`.

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
curl -X POST http://localhost:8000/webhooks/health-check \
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
├── llm/                # Claude client, Ollama client, router
├── memory/             # Identity, durable memory, search, embeddings, skills
├── tools/              # Shell, file, HTTP, web search, sanitization
├── scheduler/          # APScheduler, job store, workflows
├── telegram/           # Telegram bot and handlers
├── whatsapp/           # WhatsApp bot and handlers (neonize)
├── watchdog_monitor/   # File system monitoring
├── plugins/            # Plugin system
└── agents/             # Agent delegation
```

## Documentation

- **[User Guide](docs/USER_GUIDE.md)** — comprehensive feature documentation
- **[Quick Reference](docs/QUICK_REFERENCE.md)** — command cheat sheet

## Development

```bash
uv sync --all-extras    # Install with dev dependencies
uv run pytest           # Run tests (131 tests)
uv run pytest -v        # Verbose output
```

## License

Private project.
