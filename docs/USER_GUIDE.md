# AI Assistant — User Guide

A personal AI assistant with multi-provider LLM support, streaming CLI, tool use, persistent memory, agent delegation, automations, and more.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [First-Run Onboarding](#first-run-onboarding)
3. [Chat Interface](#chat-interface)
4. [Slash Commands](#slash-commands)
5. [Personality & Identity](#personality--identity)
6. [Memory System](#memory-system)
7. [Agentic Memory](#agentic-memory)
8. [Skills](#skills)
9. [Agentic Skill Management](#agentic-skill-management)
10. [Agents](#agents)
11. [Plugins](#plugins)
12. [Conversation Threading](#conversation-threading)
13. [Image Support](#image-support)
14. [Tools](#tools)
15. [Multi-Provider LLM Support](#multi-provider-llm-support)
16. [Ollama & Local LLMs](#ollama--local-llms)
17. [Web Search](#web-search)
18. [Vector Search](#vector-search)
19. [Telegram Bot](#telegram-bot)
20. [WhatsApp Bot](#whatsapp-bot)
21. [Scheduler](#scheduler)
22. [File Monitoring](#file-monitoring)
23. [Workflows](#workflows)
24. [Webhooks](#webhooks)
25. [Do Not Disturb](#do-not-disturb)
26. [Backups](#backups)
27. [Security](#security)
28. [API Server](#api-server)
29. [Docker](#docker)
30. [Configuration Reference](#configuration-reference)
31. [Directory Structure](#directory-structure)
32. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation

```bash
cp .env.example .env        # Create config file
# Edit .env and set ANTHROPIC_API_KEY (or configure another provider)

uv sync --all-extras        # Install dependencies
```

### Running

```bash
uv run assistant chat       # Interactive CLI
uv run assistant serve      # API server at :51430
uv run pytest               # Run tests
```

### Minimal Configuration

The only required setting is an API key for at least one provider:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

Everything else has sensible defaults.

---

## First-Run Onboarding

On first launch (when `IDENTITY.md` doesn't exist), the assistant runs an interactive setup:

1. **Name** — "What should I call you?" — saved to durable memory (`MEMORY.md`)
2. **Communication style** — "How would you like me to communicate?" — saved to identity (`IDENTITY.md`)

```
Welcome! Let's set up your assistant.

What should I call you? Alex

How would you like me to communicate?
Examples: "casual and witty", "formal and concise", "friendly with emoji"
Press Enter to skip and use defaults.
Style: casual and brief

Nice to meet you, Alex!
Setup complete. You can change these anytime by chatting.
```

You can skip either prompt by pressing Enter to use defaults. Both settings can be changed later through conversation.

---

## Chat Interface

The CLI uses Rich for rendering and prompt_toolkit for input. Messages stream in real-time as the assistant responds.

```
$ uv run assistant chat
AI Assistant - Type /help for commands, Ctrl+C to exit

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
| `/thread export <fmt>` | Export thread (json/markdown) |
| `/thread delete <id>` | Delete a thread |
| `/clear session` | Clear current session messages |
| `/clear history` | Delete all daily log files |
| `/clear memory` | Wipe durable memory (MEMORY.md) |
| `/clear search` | Clear FTS5 index and embeddings |
| `/clear all` | All of the above |
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
| `/backup restore <name>` | Restore from backup |
| `/plugins` | Manage plugins |
| `/agents` | List available agents |

All `/clear` subcommands prompt for confirmation before executing.

---

## Personality & Identity

The assistant's personality is defined in `data/memory/IDENTITY.md` and loaded into every conversation's system prompt.

### Changing Through Chat

Just tell the assistant how you want it to behave:

```
You: Be more casual and use humor
You: Talk like a friendly colleague, not a robot
You: Be formal and extremely concise
You: Your name is Jarvis
```

The assistant uses the `update_identity` tool to read the current identity, modify it based on your request, and save it. Write operations require your approval.

### Manual Editing

You can also edit `data/memory/IDENTITY.md` directly. Changes take effect on the next message.

---

## Memory System

The assistant has persistent memory across sessions.

### Identity

`data/memory/IDENTITY.md` defines the assistant's personality and role. Set up during onboarding or updated via chat.

### Durable Memory

`data/memory/MEMORY.md` stores long-term facts and preferences (your name, preferences, key facts). The assistant can update this during conversation, or you can manage it manually:

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

### Clearing Data

Use the `/clear` command to reset specific data:

```
/clear session    # Reset current conversation
/clear history    # Delete all daily logs
/clear memory     # Wipe MEMORY.md
/clear search     # Clear search index and embeddings
/clear all        # Everything
```

---

## Agentic Memory

The assistant can search, recall, and forget its own memories through LLM-callable tools.

### Searching

The assistant automatically uses `memory_search` when you ask about past conversations:

```
You: What did we discuss about authentication last week?
You: Have I mentioned any deadlines?
You: What do you know about me?
```

The tool searches across durable memory, FTS5 history, and daily logs.

### Forgetting

Ask the assistant to forget specific information:

```
You: Forget about the old project notes
You: Delete all memories about the test data
You: Forget everything (wipe all memory)
```

The `memory_forget` tool handles deletion. It requires your approval since it's a destructive action. When forgetting a topic, it removes matching lines from MEMORY.md and matching rows from the search index.

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

## Agentic Skill Management

The assistant can create, edit, and delete skills through conversation using the `manage_skill` tool.

### Examples

```
You: Create a skill for summarizing emails — include TL;DR, key points, and action items
You: Edit the code-review skill to also check for accessibility issues
You: What skills do I have?
You: Delete the old summarizer skill
```

Create and edit operations require approval. The skill files are saved to `data/skills/` and reloaded automatically.

---

## Agents

Agents are specialized sub-assistants that can be delegated tasks. Each agent has its own system prompt, tool whitelist, and tool-round budget.

### Configuration

Enable agents:

```bash
ASSISTANT_AGENTS_ENABLED=true
```

### Defining Agents

Create YAML files in `data/agents/`:

```yaml
# data/agents/researcher.yaml
name: researcher
description: Research agent — searches the web and reads files to gather information.
system_prompt: |
  You are a research assistant. Your job is to gather information and provide
  comprehensive, well-sourced answers.
allowed_tools:
  - web_search
  - http_request
  - read_file
  - memory_search
max_tool_rounds: 50
```

### Agent Fields

| Field | Description |
|-------|-------------|
| `name` | Unique identifier |
| `description` | What the agent does |
| `system_prompt` | Agent-specific instructions |
| `allowed_tools` | Whitelist of tools (empty = all tools) |
| `denied_tools` | Blacklist of tools (used when allowed_tools is empty) |
| `model` | LLM model override (`provider/model` syntax) |
| `max_tool_rounds` | Max tool calls per task (default: 5) |

### Per-Agent Model Override

Each agent can run on a different LLM by setting the `model` field using `provider/model` syntax:

```yaml
# data/agents/researcher.yaml
name: researcher
description: Research agent
system_prompt: ...
allowed_tools:
  - web_search
  - http_request
  - read_file
model: openai/gpt-4o        # ← runs on OpenAI instead of the default provider
max_tool_rounds: 8
```

Supported provider prefixes:

| Prefix | Provider | Example |
|--------|----------|---------|
| `claude/` | Anthropic Claude | `claude/claude-sonnet-4-5-20250514` |
| `openai/` | OpenAI | `openai/gpt-4o` |
| `gemini/` | Google Gemini | `gemini/gemini-2.0-flash` |
| `ollama/` | Ollama (local) | `ollama/llama3` |

If `model` is empty or omitted, the agent uses the default provider. If you omit the `provider/` prefix, the configured default provider is used with the given model name.

### How It Works

The main assistant can delegate tasks to agents using the `delegate_to_agent` or `delegate_parallel` tools. Agents run in isolated contexts with scoped tools and cannot delegate to other agents.

### Built-in Agents

- **researcher** — Web search and file reading (max 8 tool rounds)
- **coder** — Read, write, and execute code (max 10 tool rounds)

### Agentic Agent Management

The assistant can create, edit, and delete agents through conversation using the `manage_agent` tool — no need to hand-edit YAML.

#### Examples

```
You: Create an agent called "summarizer" that summarizes long documents.
     Give it read_file and web_search, use openai/gpt-4o-mini, max 8 tool rounds.

You: Edit the researcher agent to also have access to shell_exec

You: What agents do I have?

You: Delete the old summarizer agent
```

Create and edit operations require approval. The YAML files are saved to `data/agents/` and reloaded automatically.

### CLI Commands

```
/agents              # List all agents
/agents reload       # Reload agent definitions
```

---

## Plugins

Plugins extend the assistant with custom tools, skills, and lifecycle hooks — all without modifying source code. Drop a Python file into `data/plugins/` and it's live on the next start.

### Configuration

```bash
ASSISTANT_PLUGINS_ENABLED=true
```

### Writing a Plugin

Create a `.py` file in `data/plugins/`. Each plugin must:

1. Define a class that extends `BasePlugin` (or implements the `Plugin` protocol)
2. Export a `create_plugin()` factory function

Here's a minimal plugin that adds a tool:

```python
# data/plugins/my_plugin.py
from assistant.plugins.types import BasePlugin, PluginManifest, PluginToolDef

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__(PluginManifest(
            name="my-plugin",
            version="1.0.0",
            description="My custom plugin",
            author="Me",
        ))

    def get_tools(self) -> list[PluginToolDef]:
        async def greet(params: dict) -> str:
            return f"Hello, {params['name']}!"

        return [PluginToolDef(
            name="greet",
            description="Greet someone by name",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            handler=greet,
            permission_category="read",   # auto-approved
        )]

def create_plugin() -> MyPlugin:
    return MyPlugin()
```

Plugin packages (directories with `__init__.py`) are also supported. Files starting with `_` are ignored.

### Plugin API

Plugins can contribute three things:

**Tools** — registered with the LLM tool system and permission gates:

```python
def get_tools(self) -> list[PluginToolDef]:
    return [PluginToolDef(
        name="tool_name",
        description="What it does",
        input_schema={...},                # JSON Schema
        handler=async_callable,            # async (dict) -> str
        permission_category="read",        # read | write | delete | network_read | network_write
    )]
```

**Skills** — markdown injected into the system prompt:

```python
def get_skills(self) -> list[PluginSkillDef]:
    return [PluginSkillDef(
        name="my-skill",
        content="When asked about X, do Y...",
    )]
```

**Hooks** — async callbacks at key lifecycle points:

```python
def get_hooks(self) -> dict[HookType, Any]:
    async def on_pre_message(message: str, session_id: str = "") -> str:
        # Modify or inspect messages before they reach the LLM
        return message

    return {HookType.PRE_MESSAGE: on_pre_message}
```

Available hooks:

| Hook | Fires when | Signature |
|------|-----------|-----------|
| `PRE_MESSAGE` | Before user message is processed | `(message, session_id) -> str` |
| `POST_MESSAGE` | After response is generated | `(message, response, session_id) -> None` |
| `PRE_TOOL_CALL` | Before a tool executes | `(tool_name, params) -> None` |
| `POST_TOOL_CALL` | After a tool completes | `(tool_name, params, result) -> None` |
| `SESSION_START` | Chat session begins | `() -> None` |
| `SESSION_END` | Chat session ends | `() -> None` |

### Lifecycle

Plugins go through these stages:

1. **Discovery** — `data/plugins/` is scanned for `.py` files and packages
2. **Load** — `create_plugin()` is called, plugin is validated
3. **Initialize** — `plugin.initialize(context)` receives `PluginContext` with `data_dir` and `settings`
4. **Start** — `plugin.start()` is called (set up connections, background tasks, etc.)
5. **Stop** — `plugin.stop()` is called on shutdown (clean up resources)

Errors in any plugin are isolated — a broken plugin won't crash the assistant.

### CLI Commands

```
/plugins              # List all loaded plugins
/plugins info <name>  # Show details (tools, skills, hooks)
/plugins reload <name> # Hot-reload a plugin without restart
```

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
| `memory_search` | Search conversation history and memory | Auto-approved |
| `memory_forget` | Delete memories by topic or all | Requires approval (delete) |
| `update_identity` | Read/update assistant personality | Read auto-approved; write requires approval |
| `manage_skill` | Create/edit/delete/list skills | List auto-approved; changes require approval |
| `manage_agent` | Create/edit/delete/list/reload agents | List/reload auto-approved; changes require approval |
| `schedule_reminder` | Create scheduled reminders | Requires approval |
| `run_workflow` | Execute a workflow | Requires approval |
| `delegate_to_agent` | Delegate task to an agent | Auto-approved (if agents enabled) |
| `delegate_parallel` | Run multiple agents in parallel | Auto-approved (if agents enabled) |

### Permission System

Tools are classified by action category:
- **read** / **network_read** — auto-approved
- **write** / **network_write** / **delete** — require user confirmation

When a tool requires approval, you'll see a permission prompt:

```
┌─ Permission Required ─┐
│ Write: /tmp/output.txt │
│ Category: write        │
└────────────────────────┘
Approve? [y/N]
```

### Tool Round Limit

The assistant has a configurable maximum number of tool calls per response (`ASSISTANT_MAX_TOOL_ROUNDS`, default 10). When the limit is reached, the assistant automatically summarizes what it accomplished and what remains. Agents can override this with their own `max_tool_rounds` in their YAML definition.

---

## Multi-Provider LLM Support

The assistant supports multiple LLM providers. Configure your preferred default:

```bash
ASSISTANT_DEFAULT_PROVIDER=claude   # claude | openai | gemini | ollama
```

### OpenAI

```bash
OPENAI_API_KEY=sk-...
ASSISTANT_OPENAI_ENABLED=true
ASSISTANT_OPENAI_MODEL=gpt-4o
```

### Google Gemini

```bash
GEMINI_API_KEY=your-key
ASSISTANT_GEMINI_ENABLED=true
ASSISTANT_GEMINI_MODEL=gemini-2.0-flash
```

### Smart Routing

When Ollama is enabled alongside a cloud provider, the router automatically selects the best provider:

| Condition | Provider |
|-----------|----------|
| Tool use required | Default cloud provider |
| Long/complex messages (>threshold tokens) | Default cloud provider |
| Provider unavailable | Fallback to next available |
| Simple queries | Ollama (if enabled) |

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

### Routing Threshold

Adjust `ASSISTANT_LOCAL_MODEL_THRESHOLD_TOKENS` to control when Ollama is used (lower = more Ollama, higher = more cloud provider).

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
ASSISTANT_TELEGRAM_ALLOWED_USER_IDS=123456789,987654321
ASSISTANT_TELEGRAM_WEBHOOK_URL=                   # Optional, for webhook mode
```

### Usage

Message your bot on Telegram. Only users in the allowed list can interact with it. The Telegram bot shares sessions with the scheduler and watchdog, so notifications from those systems are delivered to your Telegram chat.

---

## WhatsApp Bot

Chat with the assistant from WhatsApp using linked-device QR code pairing. No Meta Business account needed.

### How It Works

The WhatsApp integration uses [neonize](https://github.com/krypton-byte/neonize), a Python library built on whatsmeow (Go). It connects as a linked device — the same mechanism used by WhatsApp Web/Desktop.

### Configuration

```bash
ASSISTANT_WHATSAPP_ENABLED=true
ASSISTANT_WHATSAPP_ALLOWED_NUMBERS=+15551234567,+442071234567
ASSISTANT_WHATSAPP_SESSION_NAME=assistant
```

### First-Time Setup

1. Start the API server: `uv run assistant serve`
2. A QR code will be displayed in the terminal
3. On your phone, open WhatsApp > Settings > Linked Devices > Link a Device
4. Scan the QR code
5. Send a message from an allowed number

The session persists in `data/whatsapp_auth/`, so you only need to scan the QR code once.

### Access Control

- Set `ASSISTANT_WHATSAPP_ALLOWED_NUMBERS` to a comma-separated list of E.164 numbers
- If the list is empty, all incoming messages are accepted
- Messages from unauthorized numbers are silently ignored

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
ASSISTANT_WATCHDOG_PATHS=/path/to/watch,/another/path
ASSISTANT_WATCHDOG_DEBOUNCE_SECONDS=2.0
ASSISTANT_WATCHDOG_ANALYZE=false    # Set true to analyze changes with the assistant
```

### CLI Commands

```
/watch                   # Show status
/watch add <path>        # Watch a directory
/watch remove <path>     # Stop watching
```

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

- Steps run sequentially; each step's output is available to the next
- Steps with `requires_approval: true` pause for user confirmation
- Execution stops on the first error

### CLI Commands

```
/workflow list           # List all workflows
/workflow run <name>     # Run a workflow
/workflow reload         # Reload YAML definitions
```

---

## Webhooks

Trigger workflows from external services via HTTP.

### Configuration

```bash
ASSISTANT_WEBHOOK_ENABLED=true
ASSISTANT_WEBHOOK_SECRET=your-hmac-secret   # Optional
```

### Endpoints

Each workflow is accessible at `POST /webhooks/{workflow-name}`. The JSON request body is passed as context to the workflow.

### HMAC Validation

If `ASSISTANT_WEBHOOK_SECRET` is set, requests must include an `X-Hub-Signature-256` header (compatible with GitHub webhook signatures).

### CLI Commands

```
/webhook list            # List webhook endpoints
/webhook test <name>     # Test a webhook
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

During the DND window, non-urgent notifications are queued and delivered when the window ends. Urgent notifications bypass DND when `allow_urgent` is enabled.

---

## Backups

Create and restore snapshots of all assistant data.

### CLI Commands

```
/backup create [name]     # Create (default name: "backup")
/backup list              # List available backups
/backup restore <name>    # Restore from backup
```

Backups are `.tar.gz` files in `data/backups/`. They include all data: memory, threads, skills, databases, and logs.

---

## Security

### Input Sanitization

All tool inputs are automatically sanitized before execution:

- **Prompt injection patterns** are stripped — system prompt markers, role-play attempts, and instruction overrides
- **File paths** are sanitized to prevent directory traversal
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

The server also manages the lifecycle of Telegram bot, WhatsApp bot, scheduler, watchdog, and workflow systems.

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
| `ASSISTANT_PORT` | `51430` | API server port |
| `ASSISTANT_LOG_LEVEL` | `INFO` | Logging level |
| `ASSISTANT_MAX_CONTEXT_MESSAGES` | `50` | Max messages in context |
| `ASSISTANT_MAX_TOOL_ROUNDS` | `10` | Max tool calls per LLM response |
| `ASSISTANT_AUTO_APPROVE_READS` | `true` | Auto-approve read operations |
| `ASSISTANT_DEFAULT_PROVIDER` | `claude` | Default LLM provider |

### OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | `""` | OpenAI API key (no prefix) |
| `ASSISTANT_OPENAI_ENABLED` | `false` | Enable OpenAI provider |
| `ASSISTANT_OPENAI_MODEL` | `gpt-4o` | OpenAI model |

### Google Gemini

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | `""` | Gemini API key (no prefix) |
| `ASSISTANT_GEMINI_ENABLED` | `false` | Enable Gemini provider |
| `ASSISTANT_GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model |

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
| `ASSISTANT_TELEGRAM_ALLOWED_USER_IDS` | `""` | Comma-separated Telegram user IDs |
| `ASSISTANT_TELEGRAM_WEBHOOK_URL` | `""` | Webhook URL for bot |

### WhatsApp

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WHATSAPP_ENABLED` | `false` | Enable WhatsApp bot |
| `ASSISTANT_WHATSAPP_ALLOWED_NUMBERS` | `""` | Comma-separated E.164 numbers |
| `ASSISTANT_WHATSAPP_SESSION_NAME` | `assistant` | Session name |

### Scheduler

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_SCHEDULER_ENABLED` | `false` | Enable scheduler |
| `ASSISTANT_SCHEDULER_TIMEZONE` | `UTC` | Scheduler timezone |

### File Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WATCHDOG_ENABLED` | `false` | Enable file monitoring |
| `ASSISTANT_WATCHDOG_PATHS` | `""` | Comma-separated paths to watch |
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
| `ASSISTANT_PLUGINS_ENABLED` | `false` | Enable plugin system |
| `ASSISTANT_AGENTS_ENABLED` | `false` | Enable agent delegation |

---

## Directory Structure

```
data/
├── memory/
│   ├── IDENTITY.md         # Assistant identity/personality
│   ├── MEMORY.md           # Durable memory (facts, preferences)
│   └── daily/              # Daily conversation logs
├── skills/                 # Skill definitions (.md)
├── threads/                # Saved conversation threads (.json)
├── workflows/              # Workflow definitions (.yaml)
├── agents/                 # Agent definitions (.yaml)
├── backups/                # Data backup tarballs (.tar.gz)
├── plugins/                # Plugin modules
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
2. The API server must be running
3. Check that the workflow name in the URL matches a loaded workflow
4. If using HMAC, verify the signature is correct

### Telegram Bot Not Responding

1. Check `ASSISTANT_TELEGRAM_ENABLED=true` and `TELEGRAM_BOT_TOKEN` is set
2. Verify your user ID is in `ASSISTANT_TELEGRAM_ALLOWED_USER_IDS`
3. The bot requires the API server: `uv run assistant serve`

### WhatsApp Bot Not Responding

1. Check `ASSISTANT_WHATSAPP_ENABLED=true`
2. Verify allowed numbers are in E.164 format
3. Re-scan QR code if session expired

### Permission Prompt Not Visible

If the `Approve? [y/N]` prompt doesn't appear during tool calls, this may be a Rich Live rendering issue. The prompt should pause the streaming display — if it doesn't, check that you're running the latest version.

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
ASSISTANT_DEFAULT_PROVIDER=ollama
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
ASSISTANT_TELEGRAM_ALLOWED_USER_IDS=your-id
ASSISTANT_AGENTS_ENABLED=true
ASSISTANT_WEBHOOK_ENABLED=true
ASSISTANT_DND_ENABLED=true
```
