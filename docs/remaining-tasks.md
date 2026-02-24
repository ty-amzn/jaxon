# Remaining Tasks — PRD Completion

*Last updated: 2026-02-22*

This document tracks features from the PRD that are not yet implemented.

---

## Priority Legend

- **P0** — Must have (core functionality)
- **P1** — Should have (important but not blocking)
- **P2** — Nice to have (enhancement)

---

## Phase 2.5 Gap: Agent Local Model Support

### 0. Ollama/Local Model Support for Agents (P0)

**PRD Reference:** Section 4.3 — Local model support via Ollama

Current state: Agents use a fixed LLM client passed at construction time. The `AgentDef` has a `model` field but it's not connected to the LLMRouter. All agent tasks go to Claude regardless of complexity.

**Problem:**
- Simple agent tasks (e.g., basic research, formatting) cannot be routed to cheaper local models
- No per-agent model configuration
- Wastes API credits on tasks Ollama could handle

**Tasks:**
- [ ] Add `provider` field to `AgentDef` (options: `claude`, `ollama`, `auto`)
- [ ] Wire `AgentRunner` to use `LLMRouter` instead of a fixed `BaseLLMClient`
- [ ] Support agent-level model override in YAML definitions:
  ```yaml
  name: researcher
  provider: auto  # auto = use router logic, ollama = always local, claude = always cloud
  model: llama3.2  # specific model for this agent (optional)
  ```
- [ ] Update `AgentLoader` to parse provider/model from YAML
- [ ] Pass settings to `AgentRunner` so it can create appropriate LLM client
- [ ] Add routing logic: agents with tools → Claude, simple agents → Ollama (if enabled)
- [ ] Test with `coder` agent (needs tools → Claude) and a new `summarizer` agent (no tools → Ollama)

**Files to modify:**
- `src/assistant/agents/types.py` — Add `provider` field
- `src/assistant/agents/loader.py` — Parse provider/model from YAML
- `src/assistant/agents/runner.py` — Use LLMRouter with agent-specific config
- `src/assistant/agents/orchestrator.py` — Pass settings to runner
- `data/agents/*.yaml` — Add provider/model fields

**New agent example (`data/agents/summarizer.yaml`):**
```yaml
name: summarizer
description: Summarization agent — condenses text and extracts key points.
provider: ollama
model: llama3.2
system_prompt: |
  You are a summarization assistant. Your job is to condense text into
  clear, concise summaries highlighting key points. Be brief but comprehensive.
allowed_tools: []  # No tools needed → perfect for local model
max_tool_rounds: 1
```

---

## Phase 3 Gaps: Messaging & Automation

### 1. Automation Management Commands (P0)

**PRD Reference:** Section 4.6.6

Current state: Has `/schedule` and `/workflow` but missing unified automation management.

**Tasks:**
- [ ] Implement `/automations` command with subcommands:
  - `/automations` — List all automations and status (active, paused, errored)
  - `/automations enable <name>` — Activate a paused automation
  - `/automations disable <name>` — Pause without deleting
  - `/automations run <name>` — Trigger manually on demand
  - `/automations log <name>` — View recent execution history
- [ ] Create unified view combining scheduled jobs and workflows

**Files to modify:**
- `src/assistant/cli/commands/schedule.py` (extend or create new command)

---

### 2. Kill Switch Command (P0)

**PRD Reference:** Section 4.6.5

**Tasks:**
- [ ] Implement `/stop-all` command to halt all running and scheduled automations immediately
- [ ] Add confirmation prompt before stopping
- [ ] Log the kill switch activation

**Files to modify:**
- `src/assistant/cli/commands/__init__.py` (register new command)
- `src/assistant/scheduler/manager.py` (add stop_all method)

---

### 3. Built-in Automation Templates (P1)

**PRD Reference:** Section 4.6.2

Current state: `data/automations/` is empty.

**Tasks:**
- [ ] Create `morning-briefing.md` — Weather, calendar, unread messages, top news
- [ ] Create `inbox-digest.md` — Summarize unread emails, flag urgent
- [ ] Create `daily-journal.md` — End-of-day reflection prompts
- [ ] Create `weekly-review.md` — Summarize week's activity from daily logs
- [ ] Document automation file format in user-guide.md

**Files to create:**
- `data/automations/morning-briefing.md`
- `data/automations/inbox-digest.md`
- `data/automations/daily-journal.md`
- `data/automations/weekly-review.md`

---

### 4. Email Watcher (P1)

**PRD Reference:** Section 4.6.3

**Tasks:**
- [ ] Create `src/assistant/watchers/email_watcher.py`
- [ ] Implement IMAP connection with configurable credentials
- [ ] Add email filtering (sender, subject keyword)
- [ ] Trigger automation on new matching emails
- [ ] Add configuration: `EMAIL_WATCHER_ENABLED`, `IMAP_*` settings

**New files:**
- `src/assistant/watchers/__init__.py`
- `src/assistant/watchers/email_watcher.py`

---

### 5. Calendar Watcher (P1)

**PRD Reference:** Section 4.6.3

**Tasks:**
- [ ] Create `src/assistant/watchers/calendar_watcher.py`
- [ ] Implement Google Calendar API integration
- [ ] Add CalDAV fallback for other providers
- [ ] Trigger automation N minutes before events
- [ ] Add configuration: `CALENDAR_WATCHER_ENABLED`, `CALENDAR_*` settings

**New files:**
- `src/assistant/watchers/calendar_watcher.py`

---

## Phase 4 Gaps: Polish Features

### 6. Conversation Export (P1)

**PRD Reference:** Section 4.1.3

**Tasks:**
- [ ] Extend `/thread` command with export functionality:
  - `/thread export <id>` — Export thread to Markdown
  - `/thread export --range <start> <end>` — Export date range
- [ ] Support export formats: Markdown, JSON

**Files to modify:**
- `src/assistant/cli/commands/thread.py`
- `src/assistant/gateway/thread_store.py`

---

### 7. Pinned Messages (P1)

**PRD Reference:** Section 4.1.3

**Tasks:**
- [ ] Create `src/assistant/memory/pins.py` for pin storage
- [ ] Implement `/pin` command to pin current/last response
- [ ] Implement `/pins` command to list pinned items
- [ ] Implement `/pin remove <id>` to unpin
- [ ] Persist pins to `data/pins.json`

**New files:**
- `src/assistant/memory/pins.py`

**Files to modify:**
- `src/assistant/cli/commands/__init__.py`

---

### 8. Undo/Correction (P1)

**PRD Reference:** Section 4.1.3

**Tasks:**
- [ ] Detect "undo" or "actually..." in user messages
- [ ] Track last action (tool calls, file writes, etc.)
- [ ] Implement rollback for reversible actions
- [ ] Store action history in session for undo capability

**Files to modify:**
- `src/assistant/gateway/session.py`
- `src/assistant/cli/chat.py`

---

### 9. File Upload Processing (P1)

**PRD Reference:** Section 4.1.4

Current state: Only images supported via `@image:/path`.

**Tasks:**
- [ ] Add `@file:/path` syntax for arbitrary file uploads
- [ ] Implement PDF text extraction
- [ ] Implement CSV parsing and summarization
- [ ] Add file size limits per type
- [ ] Update `MAX_MEDIA_SIZE_MB` to apply to all files

**Files to modify:**
- `src/assistant/cli/media.py`

---

### 10. Notification Levels (P1)

**PRD Reference:** Section 4.1.5

Current state: DND windows implemented, but no level preferences.

**Tasks:**
- [ ] Add notification level per channel: `all`, `important`, `silent`
- [ ] Store preferences in `data/preferences.json`
- [ ] Implement `/notifications` command to configure
- [ ] Respect levels when dispatching notifications

**Files to modify:**
- `src/assistant/core/notifications.py`

**New files:**
- `src/assistant/core/preferences.py`

---

### 11. Channel Routing (P1)

**PRD Reference:** Section 4.1.6

**Tasks:**
- [ ] Implement shared session state across Telegram, WhatsApp, CLI
- [ ] Add channel preference for proactive notifications
- [ ] Create `ChannelRouter` to determine where to send notifications
- [ ] Add configuration: `DEFAULT_NOTIFICATION_CHANNEL`

**Files to modify:**
- `src/assistant/gateway/session.py`
- `src/assistant/core/notifications.py`

---

### 12. Browser Automation Tool (P1)

**PRD Reference:** Section 4.5

**Tasks:**
- [ ] Create `src/assistant/tools/browser.py`
- [ ] Integrate Playwright or Selenium for headless browsing
- [ ] Implement per-action logging
- [ ] Require explicit approval for each browser action
- [ ] Add configuration: `BROWSER_ENABLED`, `BROWSER_HEADLESS`

**New files:**
- `src/assistant/tools/browser.py`

---

### 13. Calendar Read Tool (P1)

**PRD Reference:** Section 4.5

**Tasks:**
- [ ] Create `src/assistant/tools/calendar.py`
- [ ] Implement Google Calendar read-only integration
- [ ] Add CalDAV support for other providers
- [ ] Add configuration: `CALENDAR_ENABLED`, `CALENDAR_PROVIDER`

**New files:**
- `src/assistant/tools/calendar.py`

---

### 14. Email Read Tool (P1)

**PRD Reference:** Section 4.5

**Tasks:**
- [ ] Create `src/assistant/tools/email.py`
- [ ] Implement IMAP email reading
- [ ] Add search and filter capabilities
- [ ] Add configuration: `EMAIL_ENABLED`, `IMAP_*` settings

**New files:**
- `src/assistant/tools/email.py`

---

## P2 Features (Nice to Have)

### 15. Calendar Write (P2)

**PRD Reference:** Section 4.5

**Tasks:**
- [ ] Extend calendar tool with write capabilities
- [ ] Require approval for event creation
- [ ] Support draft + approve flow

---

### 16. Email Send (P2)

**PRD Reference:** Section 4.5

**Tasks:**
- [ ] Create `src/assistant/tools/email_send.py`
- [ ] Implement SMTP integration
- [ ] Draft + approve flow (no direct send)
- [ ] Add configuration: `SMTP_*` settings

---

### 17. Cost Tracking (P1)

**PRD Reference:** Section 4.3

**Tasks:**
- [ ] Track token usage per provider
- [ ] Calculate estimated costs
- [ ] Store in `data/logs/usage.jsonl`
- [ ] Add `/usage` command to view costs

---

### 18. Automatic Summarization (P1)

**PRD Reference:** Section 4.2

**Tasks:**
- [ ] Create daily log summarization job
- [ ] Extract candidates for durable memory
- [ ] Prompt user to confirm additions to MEMORY.md
- [ ] Run at configurable time (e.g., midnight)

---

### 19. Image/Chart Generation (P1)

**PRD Reference:** Section 4.1.4

**Tasks:**
- [ ] Create `src/assistant/tools/image_gen.py`
- [ ] Integrate with image generation API (DALL-E, Stable Diffusion)
- [ ] Add configuration: `IMAGE_GEN_ENABLED`, `IMAGE_GEN_PROVIDER`

---

## Summary Table

| # | Feature | Priority | Phase | Effort |
|---|---------|----------|-------|--------|
| 0 | Ollama support for agents | P0 | 2.5 | Medium |
| 1 | `/automations` command | P0 | 3 | Medium |
| 2 | `/stop-all` kill switch | P0 | 3 | Small |
| 3 | Built-in automation templates | P1 | 3 | Medium |
| 4 | Email watcher | P1 | 3 | Large |
| 5 | Calendar watcher | P1 | 3 | Large |
| 6 | Conversation export | P1 | 4 | Small |
| 7 | Pinned messages | P1 | 4 | Small |
| 8 | Undo/correction | P1 | 4 | Medium |
| 9 | File upload processing | P1 | 4 | Medium |
| 10 | Notification levels | P1 | 4 | Small |
| 11 | Channel routing | P1 | 4 | Medium |
| 12 | Browser automation tool | P1 | 3 | Large |
| 13 | Calendar read tool | P1 | 3 | Medium |
| 14 | Email read tool | P1 | 3 | Medium |
| 15 | Calendar write | P2 | 4 | Medium |
| 16 | Email send | P2 | 4 | Medium |
| 17 | Cost tracking | P1 | 2 | Small |
| 18 | Automatic summarization | P1 | 2 | Medium |
| 19 | Image/chart generation | P1 | 4 | Medium |

---

## Recommended Order

1. **Quick wins** (small effort, P0): #2 Kill switch
2. **Agent improvements** (medium effort, P0): #0 Ollama for agents
3. **Core automation** (medium effort, P0): #1 Automation commands
4. **User experience** (small effort, P1): #6 Export, #7 Pins, #10 Notification levels
5. **Tools** (medium effort, P1): #13 Calendar read, #14 Email read, #9 File uploads
6. **Integrations** (large effort, P1): #4 Email watcher, #5 Calendar watcher, #12 Browser

---

## Notes

- Some features may require additional external dependencies (Playwright, IMAP libraries, etc.)
- Calendar and email integrations should support multiple providers
- All new tools should follow the existing permission model in `gateway/permissions.py`
- All new commands should be documented in `docs/user-guide.md` and `docs/quick-reference.md`