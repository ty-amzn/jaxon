# AI Assistant — Quick Reference Card

## Slash Commands

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

## Image Syntax

```
What's in this? @image:/path/to/image.png
```

Supports: PNG, JPEG, GIF, WebP (max 10MB)

## Configuration (`.env`)

### Core
```bash
ANTHROPIC_API_KEY=your-key
ASSISTANT_MODEL=claude-sonnet-4-20250514
ASSISTANT_MAX_TOKENS=8192
ASSISTANT_DATA_DIR=./data
```

### Ollama (Local LLM)
```bash
ASSISTANT_OLLAMA_ENABLED=false
ASSISTANT_OLLAMA_BASE_URL=http://localhost:11434
ASSISTANT_OLLAMA_MODEL=llama3.2
ASSISTANT_LOCAL_MODEL_THRESHOLD_TOKENS=1000
```

### Search
```bash
ASSISTANT_WEB_SEARCH_ENABLED=false
ASSISTANT_SEARXNG_URL=http://localhost:8888
ASSISTANT_VECTOR_SEARCH_ENABLED=false
ASSISTANT_EMBEDDING_MODEL=nomic-embed-text
```

### Telegram
```bash
ASSISTANT_TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=your-token
ASSISTANT_TELEGRAM_ALLOWED_USER_IDS=[123456789]
```

### WhatsApp
```bash
ASSISTANT_WHATSAPP_ENABLED=false
ASSISTANT_WHATSAPP_ALLOWED_NUMBERS=[]     # E.164 format, e.g. ["+15551234567"]
ASSISTANT_WHATSAPP_SESSION_NAME=assistant
```

### Scheduler & Monitoring
```bash
ASSISTANT_SCHEDULER_ENABLED=false
ASSISTANT_SCHEDULER_TIMEZONE=UTC
ASSISTANT_WATCHDOG_ENABLED=false
ASSISTANT_WATCHDOG_PATHS=[]
```

### Webhooks & DND
```bash
ASSISTANT_WEBHOOK_ENABLED=false
ASSISTANT_WEBHOOK_SECRET=
ASSISTANT_DND_ENABLED=false
ASSISTANT_DND_START=23:00
ASSISTANT_DND_END=07:00
ASSISTANT_DND_ALLOW_URGENT=true
```

## Directory Structure

```
data/
├── memory/           # IDENTITY.md, MEMORY.md, daily/
├── skills/           # Skill definitions (.md)
├── threads/          # Saved threads (.json)
├── workflows/        # Workflow definitions (.yaml)
├── backups/          # Data backups (.tar.gz)
├── plugins/          # Plugin modules
├── agents/           # Agent definitions (.yaml)
├── db/               # search.db, embeddings.db, scheduler.db
└── logs/             # audit.jsonl, app.log
```

## Quick Start Profiles

### Minimal (Claude only)
```bash
ANTHROPIC_API_KEY=your-key
```

### Local-First (Ollama)
```bash
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_VECTOR_SEARCH_ENABLED=true
```

### Full Featured
```bash
ANTHROPIC_API_KEY=your-key
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_WEB_SEARCH_ENABLED=true
ASSISTANT_VECTOR_SEARCH_ENABLED=true
ASSISTANT_SCHEDULER_ENABLED=true
ASSISTANT_TELEGRAM_ENABLED=true
ASSISTANT_WHATSAPP_ENABLED=true
ASSISTANT_WEBHOOK_ENABLED=true
ASSISTANT_DND_ENABLED=true
```
