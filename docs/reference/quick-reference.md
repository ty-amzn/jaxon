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
| `/clear session` | Clear current session messages |
| `/clear history` | Delete all daily log files |
| `/clear memory` | Wipe durable memory |
| `/clear search` | Clear search index and embeddings |
| `/clear all` | Clear everything |
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
| `/agents reload` | Reload agent definitions |
| `/tasks` | List background agent tasks |
| `/tasks result <id>` | Show result of a background task |

## Natural Language Features

These work by just chatting — no commands needed:

| Say this | What happens |
|----------|-------------|
| "Be more casual and witty" | Updates assistant personality |
| "Call me Alex" | Saves your name to memory |
| "What did we talk about last week?" | Searches conversation history |
| "Forget about the old project" | Deletes matching memories |
| "Create a skill for code review" | Creates a skill file |
| "Create an agent for research using gpt-4o" | Creates an agent YAML |
| "Research quantum computing in the background" | Delegates to agent in background |
| "Remind me at 9am to check PRs" | Schedules a reminder |

## Image Syntax

```
What's in this? @image:/path/to/image.png
```

Supports: PNG, JPEG, GIF, WebP (max 10MB)

## LLM Tools

| Tool | Auto-approved? |
|------|-----------------|
| `shell_exec` (read commands) | Yes |
| `python_exec` | Yes |
| `read_file` | Yes |
| `write_file` | No |
| `http_request` (GET) | Yes |
| `http_request` (POST, etc.) | No |
| `web_fetch` | Yes |
| `pdf_read` | Yes |
| `arxiv_search` | Yes |
| `wikipedia` | Yes |
| `get_weather` | Yes |
| `web_search` | Yes |
| `memory_search` | Yes |
| `memory_store` | No |
| `memory_forget` | No (delete) |
| `update_identity` (read) | Yes |
| `update_identity` (write) | No |
| `manage_skill` (list) | Yes |
| `manage_skill` (create/edit/delete) | No |
| `manage_agent` (list/reload) | Yes |
| `manage_agent` (create/edit/delete) | No |
| `schedule_reminder` | No |
| `delegate_to_agent` (supports `background=true`) | Yes |
| `delegate_parallel` | Yes |
| `task_status` | Yes |
| `cancel_task` | No |
| `read_output_page` | Yes |
| `browse_web` (extract/screenshot/evaluate) | Yes |
| `browse_web` (click/fill) | No |
| `youtube_search` | Yes |
| `youtube_playlist` (list) | Yes |
| `youtube_playlist` (add/remove/create) | No |
| `reddit_search` | Yes |
| `hackernews` | Yes |
| `google_maps` | Yes |
| `hue` (list_lights/list_rooms/list_scenes) | Yes |
| `hue` (control_light/control_room/activate_scene) | No |
| `finance` | Yes |
| `stock_trade` | Yes (if enabled) |
| `post_to_feed` | Yes |
| `manage_feeds` | Yes |
| `send_email` | Yes |
| `contacts` (list/get/search) | Yes |
| `contacts` (create/update/delete) | No |
| `calendar` (list/today) | Yes |
| `calendar` (create/update/delete) | No |
| `reminders` (list) | Yes |
| `reminders` (create/complete/update/delete) | No |
| `send_notification` | Yes |

## Configuration (`.env`)

### Core
```bash
ANTHROPIC_API_KEY=your-key
ASSISTANT_MODEL=claude-sonnet-4-20250514
ASSISTANT_MAX_TOKENS=8192
ASSISTANT_DATA_DIR=./data
ASSISTANT_DEFAULT_PROVIDER=claude      # claude | openai | gemini | ollama | bedrock
ASSISTANT_MAX_TOOL_ROUNDS=10
```

### Multi-Provider
```bash
OPENAI_API_KEY=sk-...
ASSISTANT_OPENAI_ENABLED=false
ASSISTANT_OPENAI_MODEL=gpt-4o

GEMINI_API_KEY=
ASSISTANT_GEMINI_ENABLED=false
ASSISTANT_GEMINI_MODEL=gemini-2.0-flash
```

### AWS Bedrock
```bash
ASSISTANT_BEDROCK_ENABLED=false
ASSISTANT_BEDROCK_REGION=us-east-1
ASSISTANT_BEDROCK_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0
# Auth via AWS credential chain (AWS_PROFILE, ~/.aws/credentials, IAM roles)
```

### Ollama (Local LLM)
```bash
ASSISTANT_OLLAMA_ENABLED=false
ASSISTANT_OLLAMA_BASE_URL=http://localhost:11434
ASSISTANT_OLLAMA_MODEL=llama3.2
ASSISTANT_LOCAL_MODEL_THRESHOLD_TOKENS=1000
```

### Google Maps
```bash
ASSISTANT_GOOGLE_MAPS_ENABLED=false
GOOGLE_MAPS_API_KEY=your-key
```

### Philips Hue
```bash
ASSISTANT_HUE_ENABLED=false
HUE_BRIDGE_IP=192.168.1.100
HUE_API_KEY=your-hue-api-key
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
ASSISTANT_TELEGRAM_ALLOWED_USER_IDS=123456789
```

### WhatsApp
```bash
ASSISTANT_WHATSAPP_ENABLED=false
ASSISTANT_WHATSAPP_ALLOWED_NUMBERS=+15551234567
ASSISTANT_WHATSAPP_SESSION_NAME=assistant
```

### Slack
```bash
ASSISTANT_SLACK_ENABLED=false
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
ASSISTANT_SLACK_ALLOWED_USER_IDS=U01ABC123
ASSISTANT_SLACK_ALLOWED_CHANNEL_IDS=
```

### Scheduler & Monitoring
```bash
ASSISTANT_SCHEDULER_ENABLED=false
ASSISTANT_SCHEDULER_TIMEZONE=UTC
ASSISTANT_WATCHDOG_ENABLED=false
ASSISTANT_WATCHDOG_PATHS=
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

### Paper Trading
```bash
ASSISTANT_PAPER_TRADING_ENABLED=false
ASSISTANT_PAPER_TRADING_URL=http://localhost:51433
```

### Town Square (Feed)
```bash
ASSISTANT_TOWNSQUARE_URL=http://localhost:51431   # or http://townsquare:51431 in Docker
```

### Plugins & Agents
```bash
ASSISTANT_PLUGINS_ENABLED=false
ASSISTANT_AGENTS_ENABLED=false
```

### Calendar & Contacts
```bash
ASSISTANT_GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
ASSISTANT_CALDAV_ENABLED=false
ASSISTANT_CALDAV_URL=http://localhost:5232/assistant/calendar/
CALDAV_USERNAME=assistant
CALDAV_PASSWORD=your-password
ASSISTANT_CALENDAR_FEEDS=name|https://url.ics,name2|https://url2.ics
```

### YouTube & Reddit & Hacker News
```bash
ASSISTANT_YOUTUBE_ENABLED=false              # Search/transcripts (yt-dlp)
ASSISTANT_YOUTUBE_PLAYLIST_ENABLED=false      # Playlist management (OAuth2)
ASSISTANT_REDDIT_ENABLED=false
ASSISTANT_HACKERNEWS_ENABLED=false
```

### Advanced
```bash
ASSISTANT_APPROVAL_REQUIRED_TOOLS=calendar:create,calendar:update   # Explicit approval list
ASSISTANT_TOOL_OUTPUT_CAP=15000              # Max chars before pagination
ASSISTANT_REFLECTION_ENABLED=false           # Nightly memory reflection
ASSISTANT_REFLECTION_MODEL=ollama/minimax-m2.5:cloud
ASSISTANT_REFLECTION_HOUR=0                  # Hour to run (0 = midnight)
ASSISTANT_OBSERVATORY_URL=http://localhost:51432   # LLM metrics server
```

## Agent Definition (YAML)

```yaml
# data/agents/researcher.yaml
name: researcher
display_name: Nova           # optional — human-friendly name
tagline: the internet sleuth  # optional — short descriptor
description: Research agent
system_prompt: |
  You are a research assistant.
allowed_tools:
  - web_search
  - read_file
allowed_skills:              # optional — whitelist skills (omit = all, [] = none)
  - web-tools
model: openai/gpt-4o         # optional — provider/model syntax
max_tool_rounds: 50
vision: true                 # optional — override vision detection
```

Model providers: `claude/`, `openai/`, `gemini/`, `ollama/`, `bedrock/`. Omit for default.

## Plugin (Python)

```python
# data/plugins/my_plugin.py
from assistant.plugins.types import BasePlugin, PluginManifest, PluginToolDef

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__(PluginManifest(name="my-plugin", version="1.0.0"))

    def get_tools(self) -> list[PluginToolDef]:
        async def handler(params: dict) -> str:
            return params["text"]
        return [PluginToolDef(
            name="my_tool", description="...",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
            handler=handler, permission_category="read",
        )]

def create_plugin() -> MyPlugin:
    return MyPlugin()
```

Requires `ASSISTANT_PLUGINS_ENABLED=true`. Manage with `/plugins`, `/plugins info <name>`, `/plugins reload <name>`.

## Directory Structure

```
data/
├── memory/           # IDENTITY.md, MEMORY.md, daily/
├── skills/           # Skill definitions (.md)
├── threads/          # Saved threads (.json)
├── workflows/        # Workflow definitions (.yaml)
├── agents/           # Agent definitions (.yaml)
├── backups/          # Data backups (.tar.gz)
├── plugins/          # Plugin modules
├── db/               # search.db, embeddings.db, scheduler.db, feed.db
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
ASSISTANT_DEFAULT_PROVIDER=ollama
ASSISTANT_VECTOR_SEARCH_ENABLED=true
```

### Full Featured
```bash
ANTHROPIC_API_KEY=your-key
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_WEB_SEARCH_ENABLED=true
ASSISTANT_VECTOR_SEARCH_ENABLED=true
ASSISTANT_SCHEDULER_ENABLED=true
ASSISTANT_AGENTS_ENABLED=true
ASSISTANT_TELEGRAM_ENABLED=true
ASSISTANT_WHATSAPP_ENABLED=true
ASSISTANT_WEBHOOK_ENABLED=true
ASSISTANT_DND_ENABLED=true
ASSISTANT_REFLECTION_ENABLED=true
ASSISTANT_OBSERVATORY_URL=http://localhost:51432
```
