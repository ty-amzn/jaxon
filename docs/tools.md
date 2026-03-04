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
| `hue` | Philips Hue smart light control (list, on/off, brightness, color, scenes) | List auto-approved; control/activate require approval (if enabled) |
| `finance` | Stock quotes, crypto prices, and currency conversion | Auto-approved |
| `stock_trade` | Paper trading — agents see it as a real brokerage (buy, sell, portfolio, history, market_status) | Auto-approved (if enabled) |
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

## Philips Hue Smart Lighting

The `hue` tool controls Philips Hue lights via the local CLIP API v2 (direct bridge connection, no cloud):

| Action | Description | Permission |
|--------|-------------|------------|
| `list_lights` | List all lights with name, state, brightness | NETWORK_READ (auto-approved) |
| `list_rooms` | List rooms with grouped light IDs and states | NETWORK_READ (auto-approved) |
| `list_scenes` | List scenes grouped by room | NETWORK_READ (auto-approved) |
| `control_light` | Control a single light (on/off, brightness, color, color temp) | NETWORK_WRITE (requires approval) |
| `control_room` | Control all lights in a room via grouped_light ID | NETWORK_WRITE (requires approval) |
| `activate_scene` | Activate a Hue scene | NETWORK_WRITE (requires approval) |

Supports named colors (red, blue, green, warm white, cool white, purple, pink, etc.), color temperature presets (warm/cool/neutral), mirek values (153–500), and transition durations.

Configuration:
```bash
ASSISTANT_HUE_ENABLED=true
HUE_BRIDGE_IP=192.168.1.100        # Your Hue Bridge local IP
HUE_API_KEY=your-hue-api-key       # Generate via bridge button press + API
```

---

## Paper Trading

The `stock_trade` tool provides paper trading with real-time Yahoo Finance prices. Each agent gets an isolated portfolio starting with $100K cash. Agents see the tool as a real brokerage account — the name and description don't mention "paper" or "simulated".

| Action | Description |
|--------|-------------|
| `buy` | Buy shares at current market price (requires `symbol` + `quantity`) |
| `sell` | Sell shares at current market price (requires `symbol` + `quantity`) |
| `portfolio` | View current positions, P&L, and cash balance |
| `history` | View recent trade history |
| `market_status` | Check if the US stock market is currently open |

Trades are only allowed during US market hours (Mon-Fri 9:30 AM - 4:00 PM ET, excluding holidays). Portfolio resets are available via the dashboard UI or the REST API, not exposed to agents.

Paper Trading runs as a standalone service (like Town Square). Start it and point Jaxon at it:

```bash
cd papertrader && uv sync && uv run papertrader serve
# Dashboard at http://localhost:51433/trading/ui
```

```bash
ASSISTANT_PAPER_TRADING_ENABLED=true
ASSISTANT_PAPER_TRADING_URL=http://localhost:51433
```

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
