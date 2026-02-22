# AI Assistant — User Guide

A personal AI assistant with Claude API, streaming CLI, tool use, persistent memory, local LLM support, automations, and more.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Chat Interface](#chat-interface)
3. [Slash Commands](#slash-commands)
4. [Memory System](#memory-system)
5. [Skills](#skills)
6. [Conversation Threading](#conversation-threading)
7. [Image Support](#image-support)
8. [Tools](#tools)
9. [Ollama & Local LLMs](#ollama--local-llms)
10. [Web Search](#web-search)
11. [Vector Search](#vector-search)
12. [Telegram Bot](#telegram-bot)
13. [WhatsApp Bot](#whatsapp-bot)
14. [Scheduler](#scheduler)
14. [File Monitoring](#file-monitoring)
15. [Workflows](#workflows)
16. [Webhooks](#webhooks)
17. [Do Not Disturb](#do-not-disturb)
18. [Backups](#backups)
19. [Security](#security)
20. [API Server](#api-server)
21. [Docker](#docker)
22. [Configuration Reference](#configuration-reference)
23. [Directory Structure](#directory-structure)
24. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation

```bash
cp .env.example .env        # Create config file
# Edit .env and set ANTHROPIC_API_KEY

uv sync --all-extras        # Install dependencies
```

### Running

```bash
uv run assistant chat       # Interactive CLI
uv run assistant serve      # API server at :8000
uv run pytest               # Run tests
```

### Minimal Configuration

The only required setting is your API key:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

Everything else has sensible defaults.

---

## Chat Interface

The CLI uses Rich for rendering and prompt_toolkit for input. Messages stream in real-time as the assistant responds.

```
$ uv run assistant chat
Assistant ready. Type /help for commands.

You: Hello! What can you do?
Assistant: I can help with a wide range of tasks...
```

### Keyboard Shortcuts

- **Enter** — Send message
- **Ctrl+C** — Cancel current response
- **Ctrl+D** — Exit

---

## Slash Commands

Type `/help` in the chat to see all available commands.

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show session status |
| `/memory` | View or update durable memory |
| `/history <query>` | Search conversation history |
| `/cancel` | Cancel current operation |
| `/config` | View current configuration |
| `/skills` | List available skills |
| `/skills <name>` | Show skill details |
| `/skills reload` | Reload skills from disk |
| `/thread` | Show current thread status |
| `/thread new <name>` | Create new thread |
| `/thread save` | Save current conversation |
| `/thread load <name>` | Load a saved thread |
| `/thread list` | List all saved threads |
| `/thread export <fmt>` | Export thread (json or markdown) |
| `/thread delete <id>` | Delete a thread |
| `/schedule list` | List scheduled jobs |
| `/schedule remove <id>` | Remove a scheduled job |
| `/watch` | Manage filesystem monitoring |
| `/workflow list` | List all workflows |
| `/workflow run <name>` | Run a workflow |
| `/workflow reload` | Reload workflow definitions |
| `/webhook list` | List webhook endpoints |
| `/webhook test <name>` | Test a webhook endpoint |
| `/backup create [name]` | Create a data backup |
| `/backup list` | List available backups |
| `/backup restore <name>` | Restore from a backup |
| `/plugins` | Manage plugins |
| `/agents` | List available agents |

---

## Memory System

The assistant has persistent memory across sessions.

### Identity

`data/memory/IDENTITY.md` defines who the assistant is. Edit this file to customize its personality and role.

### Durable Memory

`data/memory/MEMORY.md` stores long-term facts and preferences. The assistant can update this during conversation, or you can manage it manually:

```
/memory                  # View current memory
/memory append <text>    # Add to memory
```

### Daily Logs

Conversations are automatically logged to `data/memory/daily/` with one file per day, providing a full history of interactions.

### Full-Text Search

All messages are indexed in a SQLite FTS5 database for fast keyword search:

```
/history authentication   # Search past conversations
```

---

## Skills

Skills are markdown files that inject specialized instructions into the assistant's system prompt.

### Creating a Skill

Create a `.md` file in `data/skills/`:

```markdown
# Code Review

When asked to review code, follow this approach:

## 1. Security Review
- Check for SQL injection
- Look for XSS vulnerabilities

## 2. Performance
- Identify N+1 queries
- Check for unnecessary allocations
```

### Managing Skills

```
/skills              # List all skills
/skills code-review  # View a specific skill
/skills reload       # Reload after adding/editing files
```

Skills are loaded automatically at startup and injected into every conversation.

---

## Conversation Threading

Save, load, and export conversation threads for organized multi-session work.

### Workflow

```
/thread new api-design    # Start a named thread
# ... have a conversation ...
/thread save              # Save it

# Later...
/thread list              # See all threads
/thread load api-design   # Resume where you left off
```

### Exporting

```
/thread export json       # Machine-readable export
/thread export markdown   # Human-readable export
```

Threads are stored as JSON files in `data/threads/`.

---

## Image Support

Send images to vision-capable models using the `@image:` syntax.

### Usage

```
What's in this image? @image:/path/to/screenshot.png

Compare these designs:
@image:/path/design-v1.png
@image:/path/design-v2.png
```

### Supported Formats

PNG, JPEG, GIF, WebP — up to 10 MB per image (configurable via `ASSISTANT_MAX_MEDIA_SIZE_MB`).

### Requirements

Works with Claude (Sonnet/Opus) and vision-capable Ollama models (e.g., `llava`).

---

## Tools

The assistant can execute actions through a permission-gated tool system.

### Built-in Tools

| Tool | Description | Permission |
|------|-------------|------------|
| `shell_exec` | Execute shell commands | Read commands auto-approved; writes require approval |
| `read_file` | Read file contents | Auto-approved |
| `write_file` | Write/create files | Requires approval |
| `http_request` | Make HTTP requests | GET auto-approved; others require approval |
| `web_search` | Search the web | Auto-approved (if enabled) |
| `schedule_reminder` | Create scheduled reminders | Requires approval |
| `run_workflow` | Execute a workflow | Requires approval |

### Permission System

Tools are classified by action category:
- **read** / **network_read** — auto-approved
- **write** / **network_write** / **delete** — require user confirmation

When a tool requires approval, you'll be prompted before execution.

---

## Ollama & Local LLMs

Run queries through local models for privacy and cost savings.

### Setup

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3.2`
3. Start Ollama: `ollama serve`

### Configuration

```bash
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_OLLAMA_BASE_URL=http://localhost:11434
ASSISTANT_OLLAMA_MODEL=llama3.2
```

### Smart Routing

When both Claude and Ollama are configured, the router automatically selects the best provider:

| Condition | Provider |
|-----------|----------|
| Tool use required | Claude |
| Long/complex messages (>1000 tokens) | Claude |
| Ollama unavailable | Claude (fallback) |
| Simple queries | Ollama |

Adjust the threshold with `ASSISTANT_LOCAL_MODEL_THRESHOLD_TOKENS` (lower = more Ollama, higher = more Claude).

---

## Web Search

Search the web using a self-hosted SearXNG instance.

### Setup

1. Deploy SearXNG: https://github.com/searxng/searxng
2. Enable the JSON API in SearXNG settings

### Configuration

```bash
ASSISTANT_WEB_SEARCH_ENABLED=true
ASSISTANT_SEARXNG_URL=http://localhost:8888
```

### Usage

Once enabled, the assistant automatically uses web search when relevant:

```
You: What's the latest news about Rust?
Assistant: [Uses web_search tool]
I found several recent articles...
```

The `web_search` tool accepts a `query` parameter and optional `num_results` (default 5, max 10).

---

## Vector Search

Semantic similarity search over conversation history using embeddings.

### Setup

Requires Ollama with an embedding model:

```bash
ollama pull nomic-embed-text
```

### Configuration

```bash
ASSISTANT_VECTOR_SEARCH_ENABLED=true
ASSISTANT_EMBEDDING_MODEL=nomic-embed-text
```

### How It Works

Every message is embedded and stored in `data/db/embeddings.db`. When you ask about past topics, the system finds semantically related conversations — not just keyword matches.

```
You: What did we discuss about authentication last week?
```

---

## Telegram Bot

Interact with the assistant through Telegram.

### Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Get the bot token

### Configuration

```bash
ASSISTANT_TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your-bot-token
ASSISTANT_TELEGRAM_ALLOWED_USER_IDS=[123456789]  # Your Telegram user ID
ASSISTANT_TELEGRAM_WEBHOOK_URL=                   # Optional, for webhook mode
```

### Usage

Message your bot on Telegram. Only users in the `allowed_user_ids` list can interact with it.

The Telegram bot shares sessions with the scheduler and watchdog, so notifications from those systems are delivered to your Telegram chat.

---

## WhatsApp Bot

Chat with the assistant from WhatsApp using linked-device QR code pairing. No Meta Business account needed.

### How It Works

The WhatsApp integration uses [neonize](https://github.com/krypton-byte/neonize), a Python library built on whatsmeow (Go). It connects as a linked device — the same mechanism used by WhatsApp Web/Desktop.

### Configuration

```bash
ASSISTANT_WHATSAPP_ENABLED=true
ASSISTANT_WHATSAPP_ALLOWED_NUMBERS=["+15551234567"]  # E.164 format
ASSISTANT_WHATSAPP_SESSION_NAME=assistant             # Optional, default: assistant
```

### First-Time Setup

1. Start the API server: `uv run assistant serve`
2. A QR code will be displayed in the terminal
3. On your phone, open WhatsApp > Settings > Linked Devices > Link a Device
4. Scan the QR code
5. Send a message to yourself (or the linked number) from an allowed number

The session persists in `data/whatsapp_auth/`, so you only need to scan the QR code once.

### Access Control

- Set `ASSISTANT_WHATSAPP_ALLOWED_NUMBERS` to a list of phone numbers in E.164 format (e.g. `+15551234567`)
- If the list is empty, all incoming messages are accepted
- Messages from unauthorized numbers are silently ignored

### Notifications

When allowed numbers are configured, they are automatically registered as notification sinks. Scheduled reminders, file monitoring alerts, and workflow notifications will be delivered to your WhatsApp.

---

## Scheduler

Schedule reminders and automated tasks using natural language or the API.

### Configuration

```bash
ASSISTANT_SCHEDULER_ENABLED=true
ASSISTANT_SCHEDULER_TIMEZONE=UTC
```

### Natural Language Reminders

Just ask the assistant:

```
You: Remind me at 9am tomorrow to review the PRs
Assistant: [Uses schedule_reminder tool]
I've set a reminder for 9:00 AM tomorrow.
```

### Managing Jobs

```
/schedule list           # See all scheduled jobs
/schedule remove <id>    # Remove a job
```

### Trigger Types

- **date** — One-time at a specific datetime
- **cron** — Recurring on a cron schedule
- **interval** — Recurring at fixed intervals

Jobs persist across restarts in `data/db/scheduler.db`.

---

## File Monitoring

Watch directories for changes and get notified.

### Configuration

```bash
ASSISTANT_WATCHDOG_ENABLED=true
ASSISTANT_WATCHDOG_PATHS=["/path/to/watch"]
ASSISTANT_WATCHDOG_DEBOUNCE_SECONDS=2.0
ASSISTANT_WATCHDOG_ANALYZE=false    # Set true to analyze changes with the assistant
```

### CLI Commands

```
/watch                   # Show status
/watch add <path>        # Watch a directory
/watch remove <path>     # Stop watching
```

When files change, notifications are sent through the dispatcher (CLI, Telegram, etc.).

---

## Workflows

Multi-step automation chains defined in YAML.

### Creating a Workflow

Create a `.yaml` file in `data/workflows/`:

```yaml
name: daily-summary
description: Generate and send a daily summary
trigger: manual        # "manual", "webhook", or "schedule"
enabled: true
steps:
  - name: gather-data
    tool: shell_exec
    args:
      command: "cat /tmp/today-notes.txt"

  - name: review-results
    tool: read_file
    args:
      path: "/tmp/review.md"
    requires_approval: true
```

### Step Execution

- Steps run sequentially; each step's output is available to the next via `previous_output` in the context
- Steps with `requires_approval: true` pause for user confirmation
- Execution stops on the first error

### CLI Commands

```
/workflow list           # List all workflows
/workflow run <name>     # Run a workflow
/workflow reload         # Reload YAML definitions
```

### Available Tools in Workflows

Any registered tool can be used as a step: `shell_exec`, `read_file`, `write_file`, `http_request`, `web_search`, etc.

---

## Webhooks

Trigger workflows from external services via HTTP.

### Configuration

```bash
ASSISTANT_WEBHOOK_ENABLED=true
ASSISTANT_WEBHOOK_SECRET=your-hmac-secret   # Optional
```

### Endpoints

Each workflow is accessible at:

```
POST /webhooks/{workflow-name}
```

The JSON request body is passed as context to the workflow.

### HMAC Validation

If `ASSISTANT_WEBHOOK_SECRET` is set, requests must include an `X-Hub-Signature-256` header:

```
X-Hub-Signature-256: sha256=<hmac-hex-digest-of-body>
```

This is compatible with GitHub webhook signatures.

### Example

```bash
# Start the API server
uv run assistant serve

# Trigger a workflow
curl -X POST http://localhost:8000/webhooks/daily-summary \
  -H "Content-Type: application/json" \
  -d '{"event": "push", "repo": "my-project"}'
```

### CLI Commands

```
/webhook list            # List webhook endpoints
/webhook test <name>     # Test a webhook (server must be running)
```

---

## Do Not Disturb

Suppress non-urgent notifications during specified hours.

### Configuration

```bash
ASSISTANT_DND_ENABLED=true
ASSISTANT_DND_START=23:00       # HH:MM
ASSISTANT_DND_END=07:00
ASSISTANT_DND_ALLOW_URGENT=true
```

### Behavior

- During the DND window, non-urgent notifications are queued
- Urgent notifications bypass DND when `allow_urgent` is enabled
- Queued messages are delivered when the next notification is sent outside the DND window

This affects all notification channels: CLI alerts, Telegram messages, scheduler reminders, watchdog alerts, and webhook triggers.

---

## Backups

Create and restore snapshots of all assistant data.

### CLI Commands

```
/backup create [name]     # Create (default name: "backup")
/backup list              # List available backups
/backup restore <name>    # Restore from backup
```

### Details

- Backups are `.tar.gz` files in `data/backups/`
- Include all data: memory, threads, skills, databases, logs
- Exclude the backups directory itself to avoid recursion
- Filenames include timestamps: `mybackup-20260221_143000.tar.gz`

---

## Security

### Input Sanitization

All tool inputs are automatically sanitized before execution:

- **Prompt injection patterns** are stripped — system prompt markers (`<|system|>`), role-play attempts ("ignore previous instructions", "you are now"), and instruction overrides
- **File paths** are sanitized to prevent directory traversal (`../` sequences removed, paths confined to workspace)
- Applied at a single chokepoint (`ToolRegistry.execute()`) so all tools benefit automatically

### Permission Gates

Every tool call goes through the permission system. Destructive or sensitive operations require explicit user approval before execution.

### Audit Logging

All tool calls (approved, denied, and errors) are logged to `data/logs/audit.jsonl` with timestamps, inputs, outputs, and duration.

---

## API Server

Run the assistant as a FastAPI server:

```bash
uv run assistant serve
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/webhooks/{name}` | POST | Webhook triggers (if enabled) |

The server also manages the lifecycle of Telegram bot, scheduler, watchdog, and workflow systems.

### Configuration

```bash
ASSISTANT_HOST=127.0.0.1
ASSISTANT_PORT=8000
```

---

## Docker

```bash
docker compose up -d
```

The `docker-compose.yml` includes a health check and mounts `data/` for persistence.

---

## Configuration Reference

All settings can be set in `.env`. Settings use the `ASSISTANT_` prefix unless noted.

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | `""` | Anthropic API key (no prefix) |
| `ASSISTANT_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `ASSISTANT_MAX_TOKENS` | `8192` | Max response tokens |
| `ASSISTANT_DATA_DIR` | `./data` | Data directory path |
| `ASSISTANT_HOST` | `127.0.0.1` | API server host |
| `ASSISTANT_PORT` | `8000` | API server port |
| `ASSISTANT_LOG_LEVEL` | `INFO` | Logging level |
| `ASSISTANT_MAX_CONTEXT_MESSAGES` | `50` | Max messages in context |
| `ASSISTANT_AUTO_APPROVE_READS` | `true` | Auto-approve read operations |

### Ollama

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_OLLAMA_ENABLED` | `false` | Enable local LLM |
| `ASSISTANT_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `ASSISTANT_OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `ASSISTANT_LOCAL_MODEL_THRESHOLD_TOKENS` | `1000` | Routing threshold |

### Search

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WEB_SEARCH_ENABLED` | `false` | Enable web search |
| `ASSISTANT_SEARXNG_URL` | `http://localhost:8888` | SearXNG instance URL |
| `ASSISTANT_VECTOR_SEARCH_ENABLED` | `false` | Enable vector search |
| `ASSISTANT_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |

### Media

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_MAX_MEDIA_SIZE_MB` | `10` | Max image size |

### Telegram

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_TELEGRAM_ENABLED` | `false` | Enable Telegram bot |
| `TELEGRAM_BOT_TOKEN` | `""` | Bot token (no prefix) |
| `ASSISTANT_TELEGRAM_ALLOWED_USER_IDS` | `[]` | Allowed Telegram user IDs |
| `ASSISTANT_TELEGRAM_WEBHOOK_URL` | `""` | Webhook URL for bot |

### Scheduler

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_SCHEDULER_ENABLED` | `false` | Enable scheduler |
| `ASSISTANT_SCHEDULER_TIMEZONE` | `UTC` | Scheduler timezone |

### File Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WATCHDOG_ENABLED` | `false` | Enable file monitoring |
| `ASSISTANT_WATCHDOG_PATHS` | `[]` | Paths to watch |
| `ASSISTANT_WATCHDOG_DEBOUNCE_SECONDS` | `2.0` | Debounce interval |
| `ASSISTANT_WATCHDOG_ANALYZE` | `false` | Analyze changes with AI |

### Webhooks

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WEBHOOK_ENABLED` | `false` | Enable webhooks |
| `ASSISTANT_WEBHOOK_SECRET` | `""` | HMAC-SHA256 secret |

### Do Not Disturb

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_DND_ENABLED` | `false` | Enable DND |
| `ASSISTANT_DND_START` | `23:00` | DND start (HH:MM) |
| `ASSISTANT_DND_END` | `07:00` | DND end (HH:MM) |
| `ASSISTANT_DND_ALLOW_URGENT` | `true` | Allow urgent during DND |

### Plugins & Agents

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_PLUGINS_ENABLED` | `false` | Enable plugins |
| `ASSISTANT_AGENTS_ENABLED` | `false` | Enable agents |

---

## Directory Structure

```
data/
├── memory/
│   ├── IDENTITY.md         # Assistant identity/personality
│   ├── MEMORY.md           # Durable memory
│   └── daily/              # Daily conversation logs
├── skills/                 # Skill definitions (.md)
├── threads/                # Saved conversation threads (.json)
├── workflows/              # Workflow definitions (.yaml)
├── backups/                # Data backup tarballs (.tar.gz)
├── plugins/                # Plugin modules
├── agents/                 # Agent definitions (.yaml)
├── db/
│   ├── search.db           # FTS5 full-text search index
│   ├── embeddings.db       # Vector embeddings
│   └── scheduler.db        # Scheduled job persistence
└── logs/
    ├── audit.jsonl         # Tool call audit log
    └── app.log             # Application log
```

---

## Troubleshooting

### Ollama Not Connecting

1. Check if running: `curl http://localhost:11434/api/tags`
2. Verify model is pulled: `ollama list`
3. Check `ASSISTANT_OLLAMA_BASE_URL`

### Web Search Not Working

1. Verify SearXNG: `curl http://localhost:8888/search?q=test&format=json`
2. Ensure JSON API is enabled in SearXNG settings
3. Check `ASSISTANT_WEB_SEARCH_ENABLED=true`

### Vector Search Errors

1. Ollama must be running (embeddings use Ollama)
2. Pull the model: `ollama pull nomic-embed-text`
3. Ensure `data/db/` is writable

### Images Not Loading

1. Use absolute file paths
2. Verify format is supported (PNG, JPEG, GIF, WebP)
3. Check file is under the size limit

### Threads Not Saving

1. Check `data/threads/` exists and is writable

### Scheduler Not Running

1. Verify `ASSISTANT_SCHEDULER_ENABLED=true`
2. The scheduler requires the API server: `uv run assistant serve`

### Webhooks Not Responding

1. Verify `ASSISTANT_WEBHOOK_ENABLED=true`
2. The API server must be running: `uv run assistant serve`
3. Check that the workflow name in the URL matches a loaded workflow
4. If using HMAC, verify the signature is correct

### Telegram Bot Not Responding

1. Check `ASSISTANT_TELEGRAM_ENABLED=true` and `TELEGRAM_BOT_TOKEN` is set
2. Verify your user ID is in `ASSISTANT_TELEGRAM_ALLOWED_USER_IDS`
3. The bot requires the API server: `uv run assistant serve`

---

## Quick Start Profiles

### Minimal (Claude Only)

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### Local-First (Privacy)

```bash
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_OLLAMA_MODEL=llama3.2
ASSISTANT_VECTOR_SEARCH_ENABLED=true
# Claude used only for complex reasoning and tool use
```

### Full Featured

```bash
ANTHROPIC_API_KEY=sk-ant-...
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_WEB_SEARCH_ENABLED=true
ASSISTANT_VECTOR_SEARCH_ENABLED=true
ASSISTANT_SCHEDULER_ENABLED=true
ASSISTANT_TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your-token
ASSISTANT_TELEGRAM_ALLOWED_USER_IDS=[your-id]
ASSISTANT_WEBHOOK_ENABLED=true
ASSISTANT_DND_ENABLED=true
```
