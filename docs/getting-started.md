# Getting Started

## Installation

```bash
cp .env.example .env        # Create config file
# Edit .env and set ANTHROPIC_API_KEY (or configure another provider)

cp -r data.example data     # Seed data directory (agents, skills, identity)
uv sync --all-extras        # Install dependencies
playwright install chromium  # Install browser for browse_web tool (one-time)
```

## Running

```bash
uv run assistant chat       # Interactive CLI
uv run assistant serve      # API server at :51430
uv run assistant ask "What time is it?"  # Single question
uv run pytest               # Run tests
```

### Authentication Commands

```bash
uv run assistant google-auth   # Authenticate Google Calendar (OAuth2)
uv run assistant youtube-auth  # Authenticate YouTube playlists (OAuth2)
uv run assistant whatsapp-pair # Pair WhatsApp by scanning QR code
```

## Minimal Configuration

The only required setting is an API key for at least one provider:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

Everything else has sensible defaults. See the [Configuration Reference](reference/configuration.md) for the full list.

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

## API Server

Run the assistant as a FastAPI server:

```bash
uv run assistant serve
```

Required for Telegram, WhatsApp, Slack, scheduler, webhooks, and file monitoring. Starts at `http://localhost:51430`.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/webhooks/{name}` | POST | Webhook triggers (if enabled) |
| `/hooks/townsquare/reply` | POST | Town Square agent-reply webhook |

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
