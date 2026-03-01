# Tools

The assistant can execute actions through a permission-gated tool system.

## Built-in Tools

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
| `delegate_to_agent` | Delegate task to an agent (supports `background=true`) | Auto-approved (if agents enabled) |
| `delegate_parallel` | Run multiple agents in parallel | Auto-approved (if agents enabled) |
| `task_status` | Check status of a background task | Auto-approved |
| `browse_web` | Browse JS-heavy pages with Playwright | extract/screenshot/evaluate auto-approved; click/fill require approval |
| `youtube_search` | Search YouTube, get video info, or extract transcripts | Auto-approved (if enabled) |
| `reddit_search` | Search Reddit, browse subreddits, or read posts | Auto-approved (if enabled) |
| `google_maps` | Get directions, find nearby places, or geocode addresses | Auto-approved (if enabled) |
| `finance` | Stock quotes, crypto prices, and currency conversion | Auto-approved |
| `post_to_feed` | Post updates to the internal feed (Town Square) | Auto-approved |

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
