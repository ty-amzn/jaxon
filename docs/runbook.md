# Jaxon — Operations Runbook

Setup, deployment, and troubleshooting guide for all 4 services.

## Architecture Overview

| Service | Port | Description |
|---------|------|-------------|
| **Jaxon** | 51430 | Main assistant — CLI, API, LLM routing, tools, agents |
| **Town Square** | 51431 | Microblog / feed service with web UI |
| **Observatory** | 51432 | LLM metrics, session traces, agent analytics |
| **PaperTrader** | 51433 | Simulated stock trading with dashboard |

All services use SQLite (WAL mode, autocommit) with data stored in `./data/` directories.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Docker & Docker Compose (for containerized deployment)
- Playwright Chromium (optional, for browser tool): `playwright install chromium`

## API Keys

| Key | Required | Where to get it | Used by |
|-----|----------|-----------------|---------|
| `ANTHROPIC_API_KEY` | Yes (unless using another provider) | [console.anthropic.com](https://console.anthropic.com) | Jaxon — Claude LLM |
| `FINNHUB_API_KEY` | Yes (for stock features) | [finnhub.io](https://finnhub.io/) — free, 60 calls/min | Jaxon finance tool, PaperTrader |
| `OPENAI_API_KEY` | Optional | [platform.openai.com](https://platform.openai.com) | Jaxon — OpenAI routing |
| `GEMINI_API_KEY` | Optional | [ai.google.dev](https://ai.google.dev) | Jaxon — Gemini routing |
| `GOOGLE_MAPS_API_KEY` | Optional | [Google Cloud Console](https://console.cloud.google.com) | Google Maps tool |
| `TELEGRAM_BOT_TOKEN` | Optional | [@BotFather](https://t.me/BotFather) | Telegram integration |
| `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` | Optional | [api.slack.com/apps](https://api.slack.com/apps) | Slack integration |

---

## Finnhub API Key Setup

Finnhub provides free stock market data used by both the **finance tool** (in the main Jaxon service) and the **PaperTrader** service. Without it, stock quotes and paper trading will not work.

### 1. Create a free account

Go to [finnhub.io](https://finnhub.io/) and sign up. No credit card required.

### 2. Get your API key

After signing in, your API key is shown on the [dashboard](https://finnhub.io/dashboard). It looks like: `cXXXXXXXXXXXXXXXXX` (starts with `c`, ~20 characters).

### 3. Configure the key

The key needs to be set in **two places**:

```bash
# 1. Root .env — used by the Jaxon finance tool
echo 'FINNHUB_API_KEY=your_key_here' >> .env

# 2. PaperTrader .env — used by PaperTrader for live prices
echo 'FINNHUB_API_KEY=your_key_here' >> papertrader/.env
```

Or edit both files manually and set `FINNHUB_API_KEY=your_key_here`.

### 4. Verify it works

```bash
# Quick test — should return a JSON quote for Apple
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=your_key_here"
```

Expected response:
```json
{"c":189.84,"d":2.34,"dp":1.25,"h":190.50,"l":187.00,"o":188.00,"pc":187.50,"t":1709740800}
```

If you see `{"error":"Invalid API key"}`, double-check the key.

### 5. Rate limits

The free tier allows **60 API calls per minute**. Jaxon and PaperTrader both use a 60-second price cache to stay well within this limit. If you hit rate limits:

- Ensure you're not running multiple instances fetching the same symbols
- The cache prevents repeated calls for the same symbol within 60 seconds
- Finnhub returns HTTP 429 when rate-limited — the retry logic handles this automatically

### 6. Docker

In Docker, the key flows through `env_file` directives in `docker-compose.yml`. Just ensure both `.env` and `papertrader/.env` have the key set before running `docker compose up`.

---

## Local Development Setup

### 1. Clone and configure

```bash
git clone <repo-url> && cd jaxon
cp .env.example .env
cp -r data.example data
```

Edit `.env` — set at minimum:
```
ANTHROPIC_API_KEY=sk-ant-...
FINNHUB_API_KEY=...
```

### 2. Install and run main service

```bash
uv sync --all-extras
uv run assistant chat       # interactive CLI
# or
uv run assistant serve      # API at http://localhost:51430
```

### 3. Install and run satellite services

Each service is an independent Python package:

```bash
# Town Square
cd townsquare && uv sync && uv run townsquare serve
# → http://localhost:51431/feed/ui

# Observatory
cd observatory && uv sync && uv run observatory serve
# → http://localhost:51432/observe/ui

# PaperTrader
cd papertrader && uv sync && uv run papertrader serve
# → http://localhost:51433/trading/ui
```

PaperTrader needs `FINNHUB_API_KEY` in its environment. Either:
- Set it in `papertrader/.env`
- Or export it: `FINNHUB_API_KEY=... uv run papertrader serve`

### 4. Run tests

```bash
uv run pytest              # all tests
uv run pytest tests/test_finance_tool.py -v  # specific test file
```

---

## Docker Deployment

### 1. Configure environment files

```bash
cp .env.example .env       # main service
# Edit .env with your API keys

# PaperTrader needs FINNHUB_API_KEY in its own env file:
# Edit papertrader/.env and set FINNHUB_API_KEY=...
```

### 2. Create the Docker network

```bash
docker network create npm-shared
```

### 3. Build and start

```bash
docker compose up -d --build
```

### 4. Verify health

```bash
docker compose ps                      # all services should be "healthy"
curl http://localhost:51430/health      # Jaxon
curl http://localhost:51431/feed/channels  # Town Square
curl http://localhost:51432/observe/stats  # Observatory
curl http://localhost:51433/trading/summary  # PaperTrader
```

### 5. View logs

```bash
docker compose logs -f                 # all services
docker compose logs -f jaxon           # main service only
docker compose logs -f papertrader     # paper trading only
```

### 6. Rebuild after code changes

```bash
docker compose up -d --build           # rebuild all
docker compose up -d --build jaxon     # rebuild one service
```

### Data persistence

All services store data in mounted volumes (`./data/`, `./townsquare/data/`, etc.). Data survives container restarts. To reset a service's data:

```bash
docker compose stop papertrader
rm -rf papertrader/data/papertrader.db*
docker compose start papertrader
```

---

## Service Configuration Reference

### Jaxon (main)

Env prefix: `ASSISTANT_` (except API keys which use provider conventions).

Key settings in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_MODEL` | `claude-sonnet-4-20250514` | Default LLM model |
| `ASSISTANT_DEFAULT_PROVIDER` | `claude` | LLM provider: claude, openai, gemini, ollama |
| `ASSISTANT_OLLAMA_ENABLED` | false | Route simple queries to local Ollama |
| `ASSISTANT_OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama endpoint |
| `ASSISTANT_PAPER_TRADING_ENABLED` | false | Enable stock trading tools |
| `ASSISTANT_PAPER_TRADING_URL` | `http://papertrader:51433` | PaperTrader service URL |
| `ASSISTANT_TOWNSQUARE_URL` | `http://townsquare:51431` | Town Square service URL |
| `ASSISTANT_OBSERVATORY_URL` | `http://observatory:51432` | Observatory service URL |
| `ASSISTANT_AGENTS_ENABLED` | false | Enable agent delegation |
| `ASSISTANT_TELEGRAM_ENABLED` | false | Enable Telegram bot |
| `ASSISTANT_SLACK_ENABLED` | false | Enable Slack bot |

### PaperTrader

Env prefix: `PAPER_TRADING_`

| Variable | Default | Description |
|----------|---------|-------------|
| `PAPER_TRADING_PORT` | 51433 | Service port |
| `PAPER_TRADING_DB_PATH` | `./data/papertrader.db` | SQLite database path |
| `PAPER_TRADING_DEFAULT_STARTING_CASH` | 100000 | Starting cash per agent |
| `FINNHUB_API_KEY` | (required) | Finnhub API key for stock prices |

### Town Square

Env prefix: `TOWNSQUARE_`

| Variable | Default | Description |
|----------|---------|-------------|
| `TOWNSQUARE_PORT` | 51431 | Service port |
| `TOWNSQUARE_DB_PATH` | `./data/townsquare.db` | SQLite database path |
| `TOWNSQUARE_WEBHOOK_CALLBACK_URL` | | Jaxon webhook URL for reply generation |

### Observatory

No env prefix needed — uses defaults. Data stored in `./data/observatory.db`.

---

## Troubleshooting

### Trades failing: "Yahoo Finance API error: 429"

**Symptom:** Agents report trade errors, PaperTrader dashboard shows no positions.

**Cause:** Yahoo Finance rate-limits automated requests, especially from cloud/Docker IPs.

**Fix:** This was replaced with Finnhub in the 10.1 migration. Ensure `FINNHUB_API_KEY` is set in both:
- Root `.env` (for the finance tool in the main app)
- `papertrader/.env` (for the PaperTrader price fetcher)

Get a free key at [finnhub.io](https://finnhub.io/) — 60 API calls/minute.

### PaperTrader shows stale data / positions disappear on restart

**Symptom:** Trades succeed but data is lost after container restart.

**Cause:** Missing `isolation_level = None` in the SQLite store — Python's sqlite3 module holds writes in an implicit transaction that is rolled back on process exit.

**Fix:** Ensure `store.py` includes `self._db.conn.isolation_level = None` after opening the database. This was fixed in the SQLite autocommit patch. Rebuild the container: `docker compose up -d --build papertrader`.

### Observatory shows "jax" for all tool events

**Symptom:** Tool events in Observatory all show agent_name as "jax" even for delegated agents.

**Cause:** The tool registry wasn't reading the `current_agent_name` ContextVar.

**Fix:** Fixed in the agent_name tool logging patch. The registry now reads `current_agent_name` from the background agent context.

### Service health checks failing

**Symptom:** Docker restarts containers frequently.

**Cause:** Health check endpoints call external APIs (e.g., price fetching). If external APIs are slow or rate-limited, the 5-second timeout is exceeded.

**Diagnosis:**
```bash
docker inspect --format='{{json .State.Health}}' papertrader | python3 -m json.tool
```

**Fix:** Ensure API keys are configured. If external APIs are temporarily down, the health check will recover on its own once the API responds.

### "ModuleNotFoundError" when running services

**Cause:** Running `python3` directly instead of through `uv run`.

**Fix:** Always use `uv run` to ensure the virtual environment is active:
```bash
uv run papertrader serve    # correct
python3 -m papertrader      # wrong (unless venv is activated)
```

### Ollama connection refused from Docker

**Symptom:** Agents using Ollama fail with connection errors.

**Fix:** Use `http://host.docker.internal:11434` as the Ollama URL (not `localhost`). This is the default in `.env.example`. Ensure Ollama is running on the host machine and listening on all interfaces:
```bash
OLLAMA_HOST=0.0.0.0 ollama serve
```

### SQLite "database is locked" errors

**Cause:** Multiple processes accessing the same SQLite database file.

**Fix:** Each service should have exactly one process. Don't run both a local dev server and Docker container for the same service simultaneously. WAL mode (enabled by default) allows concurrent reads but only one writer.

---

## Backup & Restore

### Manual backup

```bash
# Back up all service data
tar czf jaxon-backup-$(date +%Y%m%d).tar.gz \
  data/ \
  townsquare/data/ \
  observatory/data/ \
  papertrader/data/
```

### Built-in backup (main service only)

```bash
uv run assistant chat
# then type: /backup
# Creates a tarball in data/backups/
```

### Restore

```bash
tar xzf jaxon-backup-YYYYMMDD.tar.gz
docker compose up -d --build
```

---

## Resetting agent portfolios

To reset a specific agent's trading portfolio:

```bash
curl -X POST http://localhost:51433/trading/portfolios/AGENT_NAME/reset
```

To reset everything:

```bash
docker compose stop papertrader
rm papertrader/data/papertrader.db*
docker compose start papertrader
```
