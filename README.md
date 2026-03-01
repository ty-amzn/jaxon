# AI Assistant

A self-hosted personal AI assistant with multi-provider LLM support, streaming CLI, tool use, persistent memory, agent delegation, and messaging integrations.

## Features

- **Multi-provider LLM** — Claude, OpenAI, Gemini, Ollama, Bedrock with smart routing
- **Streaming CLI** — Rich-rendered chat with prompt_toolkit input
- **Tool use** — Shell, file, HTTP, browser, web search, finance, YouTube, Reddit, Google Maps
- **Persistent memory** — Identity, durable facts, daily logs, FTS5, vector search
- **Agents** — YAML-defined sub-agents with scoped tools and background delegation
- **Skills & Plugins** — Markdown prompt extensions and Python plugin system
- **Messaging** — Telegram, WhatsApp, Slack bots
- **Automations** — Scheduler, file monitoring, workflows, webhooks, DND
- **Town Square** — Standalone microblog/feed service for agent updates
- **Docker ready** — Single-command deployment with health checks

## Quick Start

```bash
cp .env.example .env          # set ANTHROPIC_API_KEY
cp -r data.example data       # seed data directory
uv sync --all-extras
uv run assistant chat         # interactive CLI
```

On first launch, the assistant will ask for your name and preferred communication style.

## Documentation

| Guide | Description |
|-------|-------------|
| **[Getting Started](docs/getting-started.md)** | Install, first run, onboarding, basic config |
| **[Features](docs/features.md)** | Commands, memory, skills, identity, threading, images |
| **[Agents](docs/agents.md)** | YAML agents, delegation, background tasks |
| **[Tools](docs/tools.md)** | Built-in tools, permissions, browser automation |
| **[LLM Providers](docs/llm-providers.md)** | Claude, OpenAI, Gemini, Ollama, Bedrock, routing |
| **Integrations** | [Telegram](docs/integrations/telegram.md) · [WhatsApp](docs/integrations/whatsapp.md) · [Slack](docs/integrations/slack.md) · [Google Calendar](docs/integrations/google-calendar.md) · [Google Maps](docs/integrations/google-maps.md) |
| **Infrastructure** | [Deployment](docs/infrastructure/deployment.md) · [Webhooks](docs/infrastructure/webhooks.md) · [Scheduler](docs/infrastructure/scheduler.md) · [Cloudflare](docs/infrastructure/cloudflare.md) · [Town Square](docs/infrastructure/town-square.md) |
| **Reference** | [Quick Reference](docs/reference/quick-reference.md) · [Configuration](docs/reference/configuration.md) · [Plugins](docs/reference/plugins.md) |

## Development

```bash
uv sync --all-extras    # Install with dev dependencies
uv run pytest           # Run tests
uv run pytest -v        # Verbose output
```

## License

Private project.
