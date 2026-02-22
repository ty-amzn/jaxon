# Personal AI Assistant — Product Requirements Document

*Author: Ty | Date: February 21, 2026*

---

## 1. Background & Motivation

### 1.1 Inspiration: OpenClaw

[OpenClaw](https://github.com/openclaw/openclaw) (formerly Clawdbot / Moltbot) is an open-source, self-hosted AI agent created by Peter Steinberger in November 2025. It exploded to 60,000+ GitHub stars in days and demonstrated the appeal of a personal AI assistant that can actually *do things* — run commands, manage calendars, send messages — rather than just chat.

**What OpenClaw gets right:**

- Local-first memory (Markdown files on disk, not a black-box vector DB)
- Model-agnostic design (bring your own API key or run local models)
- Multi-channel messaging (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, etc.)
- Extensible skill system (100+ community-built AgentSkills)
- Proactive behavior via heartbeat daemon and cron jobs
- Multi-agent routing (isolated workspaces per agent)

**Why build something different:**

- **Security concerns are severe.** Cisco found 26% of community skills contained vulnerabilities. Over 800 malicious skills (~20% of ClawHub) were discovered, including active data exfiltration. CVE-2026-25253 was rated CVSS 8.8. Meta and other enterprises have banned OpenClaw outright.
- **Too much surface area.** Supporting 15+ messaging channels, voice wake, companion apps, and 3,000+ community skills creates complexity and attack vectors most personal users don't need.
- **Privacy trade-offs.** Cross-user privacy breaches were found — conversations from one user resurfacing in another session. Credential theft risks from tools reading API keys and OAuth tokens.
- **You don't need all of it.** A personal assistant for one person can be radically simpler, more secure, and more maintainable than a general-purpose agent framework.

---

## 2. Vision & Principles

### 2.1 Vision

A personal AI assistant that runs on your own infrastructure, can take real actions on your behalf, and is simple enough to audit, secure, and maintain by a single person.

### 2.2 Design Principles

| Principle | What it means |
|---|---|
| **Privacy by default** | Data stays local. Cloud LLM calls send only what's necessary. No telemetry. Self-hosted SearXNG for web search. |
| **Minimal attack surface** | Fewer integrations, no community skill marketplace, no auth layer needed (sole user). |
| **Hybrid intelligence** | Local models for lightweight tasks; cloud APIs (Claude, etc.) for heavy reasoning. |
| **Transparency** | All memory is human-readable files. All actions are logged and auditable. |
| **One user, one instance** | No auth, no session isolation, no rate limiting. Trust-by-default for all locally managed skills. |
| **Simplicity over defense-in-depth** | Single container, no sandbox isolation. The operator *is* the user — protect against bugs, not adversaries. |

---

## 3. OpenClaw Feature Analysis

The table below maps OpenClaw's features against what this project will adopt, adapt, or skip.

| OpenClaw Feature | Adopt / Adapt / Skip | Rationale |
|---|---|---|
| Local-first memory (Markdown) | **Adopt** | Excellent approach — transparent, editable, version-controllable |
| Two-tier memory (daily logs + durable) | **Adopt** | Smart separation of working context vs. long-term knowledge |
| Model-agnostic LLM routing | **Adopt** | Essential for hybrid local/cloud approach |
| Multi-channel inbox (15+ platforms) | **Adapt** | Support 3 channels only: Telegram, WhatsApp, and local CLI |
| AgentSkills system | **Adapt** | Use the folder-based skill format, but curate manually — no community registry |
| ClawHub skill registry | **Skip** | Major security risk. 20% of registry was malicious. |
| Heartbeat / cron proactive actions | **Adapt** | Useful but needs strict sandboxing and permission gates |
| Multi-agent routing | **Skip (for now)** | Single-user doesn't need isolated agent workspaces initially |
| Voice wake / talk mode | **Skip** | Nice-to-have, not core. Can add later. |
| Companion apps (macOS/iOS/Android) | **Skip** | Telegram + WhatsApp cover mobile; no native app needed |
| Browser automation tool | **Adapt** | Useful but high-risk. Needs explicit per-action approval. |
| Shell command execution | **Adopt** | Core capability, with sandboxing |
| Calendar / email integration | **Adapt** | Read-only first, write with explicit approval |

---

## 4. Core Feature Requirements

### 4.1 Conversational Interface & Chat Features

#### 4.1.1 Core Chat (P0 — Must Have)

- Three messaging channels: Telegram, WhatsApp, and local CLI
- Natural language input with context awareness (remembers recent conversation)
- Streaming responses for long outputs
- Message history preserved locally

#### 4.1.2 Slash Commands (P0 — Must Have)

Built-in commands that bypass LLM interpretation for fast, predictable actions:

- `/status` — Show running tasks, active skills, and system health
- `/memory` — View or edit durable memory (`MEMORY.md`)
- `/history [query]` — Search conversation history
- `/skills` — List loaded skills and their status
- `/cancel` — Abort the current running task
- `/config [key] [value]` — View or update configuration
- `/help` — List available commands

Custom slash commands can be defined per-skill (e.g., a file-management skill could register `/ls`, `/find`).

#### 4.1.3 Conversation Management (P1 — Should Have)

- **Conversation threading:** Start named threads for distinct topics (e.g., `/thread "server migration"`) so context doesn't bleed between unrelated tasks
- **Conversation export:** Export a thread or date range to Markdown for archival or sharing
- **Pinned messages:** Pin important responses (decisions, code snippets, links) for quick retrieval via `/pins`
- **Undo / correction:** Reply with "undo" or "actually..." to revise the last action the assistant took

#### 4.1.4 Rich Media & Attachments (P1 — Should Have)

- Accept image uploads and pass to vision-capable models for analysis
- Accept file uploads (PDF, CSV, code files) and process inline
- Return formatted output: code blocks with syntax highlighting, tables, inline links
- Generate and return images/charts when requested (via tool or API)

#### 4.1.5 Notification Preferences (P1 — Should Have)

- Configurable notification levels: `all`, `important`, `silent`
- Do-not-disturb windows (e.g., no proactive messages between 11pm–7am)
- Notification routing: urgent alerts always delivered, summaries batched

#### 4.1.6 Multi-Channel Behavior (P1 — Should Have)

- **Telegram:** Concise summaries, inline buttons for approvals, mobile-friendly formatting
- **WhatsApp:** Similar to Telegram; uses WhatsApp Business API or bridge (e.g., Baileys / whatsapp-web.js)
- **Local CLI:** Verbose output, full streaming, syntax-highlighted code blocks, ideal for development tasks
- Message sync: conversation state and memory shared across all three channels
- Channel routing: user can set preferred channel for proactive notifications (e.g., automations notify via Telegram only)

### 4.2 Memory System

**P0 — Must Have**

- **Daily logs:** Append-only Markdown files, one per day, auto-loaded for context
- **Durable memory:** Curated `MEMORY.md` for persistent facts, preferences, and decisions
- **Identity file:** `IDENTITY.md` defining the assistant's personality and boundaries
- All memory stored as plaintext files on local disk
- Git-friendly format for version history

**P1 — Should Have**

- Local vector index (SQLite-based) for semantic search over past conversations
- Automatic summarization of daily logs into durable memory candidates

### 4.3 LLM Routing (Hybrid Model Support)

**P0 — Must Have**

- Cloud API support (Claude API as primary, with ability to swap providers)
- Local model support via Ollama (user provides a custom base URL endpoint)
- Configurable routing rules: which tasks go local vs. cloud
- API key management via environment variables or encrypted config
- Ollama endpoint configurable as `OLLAMA_BASE_URL` (e.g., `http://localhost:11434` or a remote server)
- SearXNG endpoint configurable as `SEARXNG_BASE_URL` (e.g., `http://localhost:8888`) — web search is just a local HTTP GET, no API keys needed

**P1 — Should Have**

- Cost tracking per model/provider
- Automatic fallback (if local model fails or is too slow, escalate to cloud)

### 4.4 Skill System

**P0 — Must Have**

- Folder-based skills using Markdown instruction files (compatible with AgentSkills format)
- Skills are **manually curated** — no auto-install from registries
- Skill metadata: name, description, required tools, dependencies
- Skill loading at session start with environment scoping

**P1 — Should Have**

- Skill templates for common patterns (file management, web lookup, summarization)
- Skill enable/disable via config without deleting files

### 4.5 Tool Execution

**P0 — Must Have**

- Shell command execution (sandboxed — restricted directories, no `sudo`)
- File read/write within designated workspace
- HTTP requests (for API integrations)
- Explicit permission model: destructive actions require confirmation

**P1 — Should Have**

- Browser automation (headless, with per-action logging)
- Calendar read access (Google Calendar / CalDAV)
- Email read access (IMAP)

**P2 — Nice to Have**

- Calendar write (create events with approval)
- Email send (draft + approve flow)

### 4.6 Automation & Proactive Actions

#### 4.6.1 Trigger Types

Automations are initiated by one of three trigger mechanisms:

| Trigger | Description | Example |
|---|---|---|
| **Time-based (cron)** | Fires on a schedule | "Every morning at 7am, summarize my inbox" |
| **Event-based** | Fires when a watched condition changes | "When a new email arrives from boss@company.com, notify me" |
| **Webhook** | Fires when an external service sends an HTTP POST | GitHub push → summarize the diff |

#### 4.6.2 Scheduled Tasks (P1 — Should Have)

- Cron-style scheduling with human-readable syntax (e.g., `every day at 7am`, `every monday at 9am`)
- Built-in task templates:
  - **Morning briefing** — weather, calendar, unread messages, top news
  - **Inbox digest** — summarize unread emails, flag urgent ones
  - **Daily journal prompt** — end-of-day reflection questions appended to daily log
  - **Weekly review** — summarize the week's activity from daily logs
- Tasks defined as Markdown files in an `automations/` folder:
  ```
  automations/
    morning-briefing.md    # schedule + instructions
    inbox-digest.md
    weekly-review.md
  ```
- Each automation file specifies: schedule, required skills/tools, output destination, and permission level

#### 4.6.3 Event-Based Triggers (P1 — Should Have)

- File watcher: trigger when a file in a watched directory changes (e.g., new download → auto-organize)
- Email watcher: trigger on new email matching a filter (sender, subject keyword)
- Calendar watcher: trigger N minutes before an upcoming event (e.g., prep meeting notes)
- Configurable polling interval per watcher (default: 5 minutes)

#### 4.6.4 Workflow Chains — "If X then Y" (P2 — Nice to Have)

- Define multi-step workflows where the output of one action feeds into the next
- Example workflow:
  1. **Trigger:** New email from `receipts@airline.com`
  2. **Step 1:** Extract flight details (date, route, confirmation number)
  3. **Step 2:** Create calendar event with flight info
  4. **Step 3:** Save confirmation to `travel/` folder
  5. **Step 4:** Send summary to Telegram
- Workflow definition format (Markdown or YAML in `automations/`):
  ```yaml
  name: flight-tracker
  trigger:
    type: email
    filter: { from: "receipts@airline.com" }
  steps:
    - skill: extract-flight-info
    - skill: create-calendar-event
      requires_approval: true
    - skill: file-organizer
      destination: travel/
    - skill: notify
      channel: telegram
  ```
- Each step can be marked `requires_approval: true` to pause and wait for user confirmation

#### 4.6.5 Automation Safety (P0 — Must Have)

- **Read-only by default:** Automations can read and summarize, but cannot send, delete, or modify without explicit per-automation approval
- **Approval modes per automation:**
  - `auto` — runs without confirmation (only for read-only tasks like briefings)
  - `notify` — runs and notifies you what it did (for low-risk writes like saving a file)
  - `approve` — pauses and asks before executing (for sends, deletes, API calls)
- **Kill switch:** `/stop-all` command halts all running and scheduled automations immediately
- **Audit log:** Every automation run logged with trigger time, steps executed, outputs, and any errors
- **Resource limits:** Max execution time per automation (default: 60s), max API calls per run (default: 10)

#### 4.6.6 Automation Management Commands

- `/automations` — List all automations and their status (active, paused, errored)
- `/automations enable <name>` — Activate a paused automation
- `/automations disable <name>` — Pause without deleting
- `/automations run <name>` — Trigger manually on demand
- `/automations log <name>` — View recent execution history

### 4.7 Security & Permissions

Since this is a sole-user, self-hosted system, the security model focuses on **preventing accidental damage and prompt injection** rather than defending against malicious users.

**P0 — Must Have**

- All tool calls logged with timestamp, input, and output
- Destructive actions (delete, send, post) require explicit user approval
- No community skill registry — all skills are locally managed
- Input sanitization on all external data (anti-prompt-injection)

**Simplified (sole user):**

- ~~Authentication / login~~ — Not needed. You are the only user.
- ~~Environment variable isolation per skill~~ — Not needed. You trust your own skills. Single `.env` file is sufficient.
- ~~Rate limiting on tool calls~~ — Not needed. No abuse vector from other users.
- ~~Anomaly detection~~ — Not needed. You control what skills are installed.
- ~~Two-container sandbox~~ — Not needed. Single container; the operator is the user.

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  User Interface                  │
│         (CLI  /  Telegram Bot  /  Web UI)        │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                  Gateway (Core)                  │
│  ┌─────────────┐  ┌───────────┐  ┌───────────┐  │
│  │  Session     │  │  Router   │  │  Auth &   │  │
│  │  Manager     │  │  (LLM)   │  │  Perms    │  │
│  └─────────────┘  └───────────┘  └───────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   Memory     │ │  Skills  │ │    Tools     │
│  (Markdown   │ │  (Local  │ │  (Shell,     │
│   + SQLite)  │ │  folders)│ │   HTTP,      │
│              │ │          │ │   Browser)   │
└──────────────┘ └──────────┘ └──────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│        External Services             │
│  ┌────────────┐  ┌────────────────┐  │
│  │  Ollama     │  │  Claude API    │  │
│  │  (local)    │  │  (cloud)       │  │
│  └────────────┘  └────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │  SearXNG (self-hosted search)  │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### 5.1 Key Architectural Decisions

**Adopted from OpenClaw:**

- Gateway as single control plane (Python long-running service)
- Two-tier memory with Markdown source of truth
- Skill-based extensibility using folder conventions
- Session-scoped skill loading

**Changed from OpenClaw:**

- No multi-agent routing (single user, single agent)
- No community skill registry (manual curation only)
- Explicit permission gates on all write/send/delete operations
- Sandboxed tool execution by default
- No voice or companion app layer at launch

### 5.2 Suggested Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Runtime** | Python 3.11+ / asyncio | Async-native, rich ML/AI ecosystem, single language for entire stack |
| **Web framework** | FastAPI | Async, lightweight, built-in OpenAPI docs, WebSocket support |
| **Local LLM** | Ollama (user-provided base URL) | Simple REST API, wide model support; endpoint is externally managed |
| **Cloud LLM** | Anthropic Python SDK (`anthropic`) | First-class Claude API support with streaming and tool use |
| **Memory store** | Markdown files + SQLite FTS5 | Human-readable + fast full-text search |
| **Vector search** | SQLite + sqlite-vec (or ChromaDB) | Lightweight, no external DB dependency |
| **Telegram** | python-telegram-bot (v20+) | Async-native, well-maintained, full Bot API coverage |
| **WhatsApp** | whatsapp-web.js via subprocess, or Baileys bridge | No mature pure-Python WhatsApp library; bridge to JS library as needed |
| **CLI** | Textual or Rich + Click | Beautiful terminal UI with streaming, syntax highlighting |
| **Scheduling** | APScheduler | Python-native cron + interval scheduling, persistent job store |
| **File watching** | watchdog | Cross-platform filesystem event monitoring |
| **Web search** | SearXNG (self-hosted) | Privacy-preserving metasearch; just another local HTTP call |
| **HTTP client** | httpx | Async HTTP/2 client for API integrations and SearXNG queries |
| **Config** | Pydantic Settings + `.env` | Type-safe config with environment variable support |
| **Containerization** | Docker / Podman | Single container for the assistant; SearXNG and Ollama run separately |
| **Packaging** | uv or Poetry | Fast dependency resolution and lockfiles |

### 5.3 Containerization Strategy

The entire assistant can be containerized for portable, reproducible deployment. This also provides an additional security boundary — tool execution happens inside a container with limited host access.

#### 5.3.1 Container Architecture

Since you're the sole user, a single container is sufficient — no need for a separate tool-sandbox. SearXNG and Ollama run as their own services (you likely already have them running).

```
┌──────────────────────────────────────────────────────────┐
│                     Host Machine                          │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │            Docker Compose Stack                      │  │
│  │                                                      │  │
│  │  ┌───────────────────────────────────────────────┐   │  │
│  │  │  assistant                                    │   │  │
│  │  │  Python gateway, LLM router, skills,          │   │  │
│  │  │  Telegram bot, WhatsApp bridge, scheduler     │   │  │
│  │  │  Port: 51430 (API + webhooks, localhost only)  │   │  │
│  │  └───────────────────────────────────────────────┘   │  │
│  │                                                      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  Already running on host / separate containers:           │
│    - SearXNG  (e.g., http://localhost:8888)               │
│    - Ollama   (e.g., http://localhost:11434)              │
│                                                           │
│  Volumes:                                                 │
│    ./data/memory/      → /app/memory                      │
│    ./data/skills/      → /app/skills                      │
│    ./data/automations/ → /app/automations                 │
│    ./data/logs/        → /app/logs                        │
│    ./.env              → /app/.env                        │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

#### 5.3.2 Docker Compose Definition (Illustrative)

```yaml
version: "3.9"

services:
  assistant:
    build: .
    container_name: personal-ai-assistant
    restart: unless-stopped
    ports:
      - "127.0.0.1:51430:51430"
    volumes:
      - ./data/memory:/app/memory
      - ./data/skills:/app/skills
      - ./data/automations:/app/automations
      - ./data/logs:/app/logs
    env_file: .env
    environment:
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL}
      - SEARXNG_BASE_URL=${SEARXNG_BASE_URL}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    # Use host network if Ollama/SearXNG run on localhost
    # network_mode: host
```

#### 5.3.3 Deployment Options

| Option | How it works | Best for |
|---|---|---|
| **Docker Compose (recommended)** | `docker compose up -d` on any Linux/macOS/WSL machine | Most users — simple, reproducible, easy to back up |
| **Single container** | One Dockerfile, no sandbox isolation | Quick start or low-resource devices |
| **Bare metal** | Run Python directly, use systemd for process management | Users who want full control, no Docker overhead |
| **NAS / home server** | Deploy to Synology, Unraid, TrueNAS, or Raspberry Pi | Always-on assistant without a dedicated server |
| **Cloud VM** | Deploy to a small VPS (2 vCPU, 2GB RAM) behind VPN/Tailscale | Remote access while keeping data on your own infra |

#### 5.3.4 Containerization Benefits

- **Portability:** Move the entire assistant between machines with `docker compose up`
- **Easy backup:** All state lives in `./data/` — just `tar czf backup.tar.gz data/` and copy
- **Reproducibility:** Pinned Python dependencies via lockfile, deterministic builds
- **Upgrade path:** Pull new image, restart — data volumes persist across upgrades

#### 5.3.5 Notes

- **WhatsApp bridge** may need persistent session state (browser profile) — mount as a volume
- **Ollama and SearXNG** are assumed to run externally — the assistant container just needs network access to their base URLs
- **Ports are bound to 127.0.0.1 only** — use Tailscale/WireGuard if you need remote access
- **Secrets** in `.env` with `chmod 600` is sufficient for a sole-user setup

---

## 6. Lessons from OpenClaw's Security Issues

OpenClaw's rapid growth exposed critical security flaws that this project must learn from:

| Issue | Impact | Our Mitigation |
|---|---|---|
| Malicious community skills (20% of registry) | Data exfiltration, credential theft | No community registry. All skills manually written or audited. |
| Prompt injection via email/web content | Agent tricked into leaking secrets | Sanitize all external inputs. Treat ingested content as untrusted. |
| 42,000+ exposed instances online | Authentication bypass on 93% | Never expose to public internet. Localhost-only; Tailscale for remote access. |
| Cross-user data leakage | Privacy breach across sessions | **Eliminated entirely** — sole user, no sessions to isolate. |
| Unsanitized log entries (CVE-2026-25253) | Log poisoning | Sanitize all inputs before logging. |
| Credential access by tools | API keys stolen | Per-skill environment isolation. Minimal credential exposure. |

---

## 7. Development Roadmap

Phases are task-based milestones, not time-bound. Each phase has a clear "done when" gate before moving on.

### Phase 1: Foundation

**Goal:** A working CLI chatbot with memory, backed by Claude API.

- [ ] Set up Python gateway runtime (FastAPI + asyncio)
- [ ] Pydantic Settings config with `.env` support
- [ ] Create Dockerfile and docker-compose.yml
- [ ] Implement two-tier memory system (daily logs + MEMORY.md + IDENTITY.md)
- [ ] Integrate Claude API via Anthropic Python SDK
- [ ] Build local CLI interface with Rich/Textual and streaming responses
- [ ] Implement slash command framework (`/status`, `/memory`, `/help`, `/cancel`, etc.)
- [ ] Implement basic permission model (approve destructive actions)
- [ ] Logging and audit trail for all tool calls

**Done when:** You can chat with the assistant via CLI, it remembers context across sessions via daily logs and durable memory, and all interactions are logged.

### Phase 2: Local Intelligence & Skills

**Goal:** Hybrid local/cloud model routing and an extensible skill system.

- [ ] Integrate Ollama via user-provided base URL endpoint
- [ ] Build LLM router (local vs. cloud based on configurable rules)
- [ ] Integrate SearXNG as a web search tool via self-hosted base URL
- [ ] Implement skill loading system (folder-based, Markdown instructions)
- [ ] Add foundational skills: file management, web search (SearXNG), note-taking
- [ ] Add SQLite-based vector search for memory retrieval
- [ ] Conversation threading and export support
- [ ] Rich media handling (image/file uploads, formatted output)

**Done when:** The assistant routes between Ollama and Claude based on task type, skills can be added by dropping a folder in `skills/`, and you can search past conversations semantically.

### Phase 3: Messaging & Automation

**Goal:** Reach the assistant from your phone and have it do things proactively.

- [ ] Integrate Telegram Bot as a messaging channel
- [ ] Integrate WhatsApp as a messaging channel (Baileys / whatsapp-web.js bridge)
- [ ] Multi-channel behavior: shared state, per-channel formatting, channel routing for notifications
- [ ] Implement automation engine with cron scheduling (APScheduler)
- [ ] Build `automations/` folder system with Markdown/YAML definitions
- [ ] Implement built-in automations: morning briefing, inbox digest, weekly review
- [ ] Add event-based triggers (file watcher via watchdog, email watcher, calendar watcher)
- [ ] Implement automation safety: approval modes (`auto`/`notify`/`approve`), kill switch, resource limits
- [ ] Add automation management commands (`/automations list/enable/disable/run/log`)
- [ ] Add calendar read integration (Google Calendar / CalDAV)
- [ ] Add email read integration (IMAP)

**Done when:** You can message the assistant from Telegram and WhatsApp, it sends you a morning briefing automatically, and at least one event-based trigger works end-to-end.

### Phase 4: Workflows & Polish

**Goal:** Multi-step automations and production-readiness.

- [ ] Implement workflow chains (multi-step if-X-then-Y automations with YAML definitions)
- [ ] Webhook trigger support for external service integration
- [ ] Notification preferences and do-not-disturb windows
- [ ] Input sanitization and prompt injection defenses
- [ ] Configuration management (backup/restore of `./data/`)
- [ ] Documentation and personal runbook

**Done when:** You can define a multi-step workflow (e.g., email → extract → calendar → notify), the assistant runs reliably for a week with no unintended actions, and you have a documented setup/restore process.

---

## 8. Success Criteria

The assistant is considered successful when it can:

1. Answer questions using conversation history and durable memory
2. Execute simple tasks (file operations, web lookups) with appropriate permissions
3. Route between local and cloud models based on task needs
4. Run at least one proactive daily task (e.g., morning briefing)
5. Operate for 30 days with zero unintended data exposure
6. Have all actions be auditable through local logs

---

## 9. Out of Scope (Explicitly)

- Multi-user / multi-tenant support
- Voice interaction
- Mobile companion apps
- Community skill marketplace
- Public-facing deployment
- Real-time collaboration features

---

## 10. Research Sources

- [OpenClaw GitHub Repository](https://github.com/openclaw/openclaw)
- [OpenClaw Official Site](https://openclaw.ai/)
- [OpenClaw Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
- [DigitalOcean — What is OpenClaw?](https://www.digitalocean.com/resources/articles/what-is-openclaw)
- [Milvus — Complete Guide to OpenClaw](https://milvus.io/blog/openclaw-formerly-clawdbot-moltbot-explained-a-complete-guide-to-the-autonomous-ai-agent.md)
- [OpenClaw Skills Documentation](https://docs.openclaw.ai/tools/skills)
- [Cisco Blog — OpenClaw Security Risks](https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare)
- [Microsoft Security Blog — Running OpenClaw Safely](https://www.microsoft.com/en-us/security/blog/2026/02/19/running-openclaw-safely-identity-isolation-runtime-risk/)
- [Fortune — OpenClaw Security Concerns](https://fortune.com/2026/02/12/openclaw-ai-agents-security-risks-beware/)
- [Giskard — OpenClaw Security Vulnerabilities](https://www.giskard.ai/knowledge/openclaw-security-vulnerabilities-include-data-leakage-and-prompt-injection-risks)
