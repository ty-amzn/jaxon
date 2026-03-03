# Tools

The assistant can execute actions through a permission-gated tool system.

## Built-in Tools

| Tool | Description | Permission |
|------|-------------|------------|
| `shell_exec` | Execute shell commands | Read commands auto-approved; writes require approval |
| `read_file` | Read file contents | Auto-approved |
| `write_file` | Write/create files | Requires approval |
| `http_request` | Make HTTP requests | GET auto-approved; others require approval |
| `web_fetch` | Fetch and extract text from URLs | Auto-approved (NETWORK_READ) |
| `pdf_read` | Extract text from PDF URLs | Auto-approved (NETWORK_READ) |
| `arxiv_search` | Search arXiv for academic papers | Auto-approved (NETWORK_READ) |
| `wikipedia` | Wikipedia article summaries and search | Auto-approved (NETWORK_READ) |
| `get_weather` | Current conditions, feels-like, snow, forecast, and NWS alerts via Open-Meteo | Auto-approved (NETWORK_READ) |
| `web_search` | Search the web via SearXNG | Auto-approved (if enabled) |
| `memory_search` | Search conversation history and memory | Auto-approved |
| `memory_store` | Store a fact in durable memory | Requires approval (WRITE) |
| `memory_forget` | Delete memories by topic or all | Requires approval (delete) |
| `update_identity` | Read/update assistant personality | Read auto-approved; write requires approval |
| `manage_skill` | Create/edit/delete/list skills | List auto-approved; changes require approval |
| `manage_agent` | Create/edit/delete/list/reload agents | List/reload auto-approved; changes require approval |
| `schedule_reminder` | Create scheduled reminders | Requires approval |
| `run_workflow` | Execute a workflow | Requires approval |
| `delegate_to_agent` | Delegate task to an agent (supports `background=true`) | Auto-approved (if agents enabled) |
| `delegate_parallel` | Run multiple agents in parallel | Auto-approved (if agents enabled) |
| `task_status` | Check status of a background task | Auto-approved |
| `cancel_task` | Cancel a running background task | Requires approval (WRITE) |
| `read_output_page` | Read paginated tool output | Auto-approved (READ) |
| `browse_web` | Browse JS-heavy pages with Playwright | extract/screenshot/evaluate auto-approved; click/fill require approval |
| `youtube_search` | Search YouTube, get video info, or extract transcripts | Auto-approved (if enabled) |
| `youtube_playlist` | Manage YouTube playlists (list, create, add/remove videos) | List auto-approved; add/remove/create require approval (if enabled) |
| `reddit_search` | Search Reddit, browse subreddits, or read posts | Auto-approved (if enabled) |
| `hackernews` | Browse Hacker News (top, best, new, ask, show) and search | Auto-approved (if enabled) |
| `google_maps` | Get directions, find nearby places, or geocode addresses | Auto-approved (if enabled) |
| `finance` | Stock quotes, crypto prices, and currency conversion | Auto-approved |
| `post_to_feed` | Post updates to the internal feed (Town Square) | Auto-approved |
| `manage_feeds` | Manage Town Square feed subscriptions | Auto-approved |
| `send_email` | Send email notification via IFTTT webhook | Auto-approved (NETWORK_READ) |
| `contacts` | Personal relationship manager (CRUD for contacts) | List/get/search auto-approved; create/update/delete require approval |
| `calendar` | Calendar events (SQLite or CalDAV/Google) | List/today auto-approved; create/update/delete require approval (WRITE or NETWORK_WRITE depending on backend) |
| `reminders` | CalDAV task/reminder management (VTODO) | List auto-approved; create/complete/update/delete require approval |
| `send_notification` | Push notification to configured channels | Auto-approved (if dispatcher available) |

---

## Browser Automation

The `browse_web` tool uses a real Chromium browser (via Playwright) to handle JavaScript-heavy sites, SPAs, and dynamic content that `web_fetch` cannot render. Actions:

- **extract** — Load the page, wait for JS, return text content
- **screenshot** — Return a base64-encoded PNG screenshot
- **click** — Click a CSS selector, return resulting page text
- **fill** — Fill a form field (selector + value), return resulting page text
- **evaluate** — Run a JavaScript expression, return the result

Each page runs in a fresh browser context (no persistent cookies). Use the optional `wait_for` parameter (CSS selector) to wait for specific elements before extracting content.

Setup: `playwright install chromium` after installing dependencies.

---

## Hack-er News

The `hackernews` tool browses Hacker News via the Firebase API and Algolia search:

- **top/best/new/ask/show** — Fetch stories from these feeds
- **story** — Get details and comments for a story
- **search** — Search HN via Algolia

Configuration: `ASSISTANT_HACKERNEWS_ENABLED=true`

---

## Contacts (PRM)

The `contacts` tool is a personal relationship manager stored in SQLite:

| Action | Description | Permission |
|--------|-------------|------------|
| `list` | List all contacts | READ (auto-approved) |
| `get` | Get a contact by ID | READ (auto-approved) |
| `search` | Search contacts by name/notes | READ (auto-approved) |
| `create` | Create a new contact | WRITE (requires approval) |
| `update` | Update a contact | WRITE (requires approval) |
| `delete` | Delete a contact | DELETE (requires approval) |

Automatically tracks last contact date and interaction count.

---

## Weather

The `get_weather` tool fetches current conditions, feels-like temperature, snow data, and forecasts from Open-Meteo (free, no API key required). For US locations, it also fetches active NWS severe weather alerts.

Supports `units` parameter: `"metric"` (default, °C/km/h/mm) or `"imperial"` (°F/mph/in).

```
What's the weather in Tokyo?
Weather forecast for Paris, France for the next 5 days
What's the weather in Boston in Fahrenheit?
```

---

## Wikipedia

The `wikipedia` tool fetches article summaries or searches for topics (free, no API key required). Faster and cleaner than `web_fetch` for factual lookups:

```
Tell me about the Apollo 11 mission
Who was Ada Lovelace?
Search Wikipedia for articles about quantum entanglement
```

---

## arXiv

The `arxiv_search` tool searches academic papers:

```
Search arXiv for quantum computing papers
Find papers about machine learning transformers
```

---

## PDF Reading

The `pdf_read` tool extracts text from PDF URLs:

```
Summarize this paper: https://arxiv.org/pdf/2301.12345.pdf
What's in this PDF? @url:https://example.com/document.pdf
```

Optional `pages` parameter: `"1-5,8,10"` to extract specific pages.

---

## Email Notifications

The `send_email` tool sends emails via IFTTT webhook. Configure in IFTTT to receive notifications.

---

## Permission System

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

---

## Tool Round Limit

The assistant has a configurable maximum number of tool calls per response (`ASSISTANT_MAX_TOOL_ROUNDS`, default 10). When the limit is reached, the assistant automatically summarizes what it accomplished and what remains. Agents can override this with their own `max_tool_rounds` in their YAML definition.
