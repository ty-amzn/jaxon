# Observatory

Observatory is a standalone metrics service that tracks LLM inference events and tool call events across all providers. It runs as its own FastAPI service and provides a dashboard UI for monitoring usage, latency, errors, and token consumption.

---

## Running Observatory

Observatory is a separate service in the `observatory/` directory:

```bash
cd observatory
uv sync
uv run observatory serve
# Dashboard at http://localhost:51432/observe/ui
```

Then set `ASSISTANT_OBSERVATORY_URL=http://localhost:51432` in Jaxon's `.env` to enable metrics logging.

---

## Features

- **Inference event tracking** — Provider, model, latency, token counts, success/failure for every LLM call
- **Tool event tracking** — Tool name, duration, success/failure for every tool call
- **Dashboard UI** — Real-time stats with customizable time range (hours/days/weeks)
- **Timeline chart** — Calls over time with configurable bucket size (hour/6h/day) and scrollable history
- **Breakdown views** — Calls by provider, model, and agent
- **Token usage** — Input/output token totals and per-model breakdown
- **Raw prompt/response storage** — Stored for 30 days, then automatically cleaned up
- **Data retention** — Events retained for 180 days, configurable via cleanup

---

## How It Works

Jaxon sends fire-and-forget HTTP POSTs to Observatory after each LLM call and tool call. This adds negligible latency since the calls are non-blocking. If Observatory is unavailable, metrics are silently dropped.

---

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/observe/ui` | GET | Dashboard web UI |
| `/observe/events` | POST | Log an inference event |
| `/observe/events` | GET | List inference events (filterable by provider, model, agent, session) |
| `/observe/events/{id}` | GET | Get a single event |
| `/observe/events/{id}/raw` | GET | Get raw prompt/response for an event |
| `/observe/stats` | GET | Aggregate statistics (`?period_hours=24`) |
| `/observe/timeline` | GET | Call counts by time bucket (`?period_hours=24&offset_hours=0&bucket_hours=1`) |
| `/observe/tool-events` | POST | Log a tool call event |
| `/observe/tool-events` | GET | List tool events (filterable by tool_name, agent, success) |
| `/observe/tool-stats` | GET | Aggregate tool call statistics |

---

## Configuration

### Observatory (`observatory/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSERVATORY_HOST` | `127.0.0.1` | Bind host |
| `OBSERVATORY_PORT` | `51432` | Bind port |
| `OBSERVATORY_DB_PATH` | `./data/observatory.db` | SQLite database path |

### Jaxon (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_OBSERVATORY_URL` | _(empty)_ | Observatory service URL (enables metrics logging when set) |
