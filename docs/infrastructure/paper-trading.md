# Paper Trading

Paper Trading is a standalone simulated stock trading service where agents can practice trading strategies using real Yahoo Finance prices without real money. Each agent gets an isolated portfolio with $100K starting cash. It runs as its own FastAPI service (separate from Jaxon) and communicates via HTTP — the same pattern as Town Square.

---

## Running Paper Trading

Paper Trading is a separate service in the `papertrader/` directory:

```bash
cd papertrader
uv sync
uv run papertrader serve
# Dashboard at http://localhost:51433/trading/ui
```

Then set `ASSISTANT_PAPER_TRADING_ENABLED=true` and `ASSISTANT_PAPER_TRADING_URL=http://localhost:51433` in Jaxon's `.env` to connect.

---

## Features

- **Isolated portfolios** — Each agent gets its own portfolio with independent cash and positions
- **Real prices** — All trades execute at live Yahoo Finance prices
- **Weighted average cost** — Additional buys recalculate cost basis
- **P&L tracking** — Unrealized P&L on open positions, realized P&L on sales
- **Performance snapshots** — Portfolio value recorded over time for charting
- **Market hours enforcement** — Trades only execute during NYSE hours (Mon-Fri 9:30 AM - 4:00 PM ET, excluding holidays)
- **Dashboard UI** — Overview of all agents, click through for positions, orders, and performance chart
- **Auto-refresh** — Dashboard updates every 30 seconds
- **Dark/light theme** — Toggle via header button

---

## How Agents Trade

Agents see the tool as `stock_trade` — a real brokerage account. The name and description deliberately don't mention "paper", "simulated", or "practice", so agents trade seriously. Under the hood, it makes HTTP calls to the Paper Trading service.

```
stock_trade(action="buy", symbol="AAPL", quantity=10)
stock_trade(action="sell", symbol="AAPL", quantity=5)
stock_trade(action="portfolio")
stock_trade(action="history")
stock_trade(action="market_status")
```

Portfolios are auto-created on first trade — no setup needed. Portfolio resets are only available via the dashboard UI or REST API (`POST /trading/portfolios/{agent}/reset`), not exposed to agents.

---

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/trading/ui` | GET | Dashboard web UI |
| `/trading/portfolios` | GET | List all portfolios with current values |
| `/trading/portfolios/{agent}` | GET | Portfolio detail with positions and live prices |
| `/trading/trade` | POST | Execute trade (`{"agent_name", "symbol", "side", "quantity"}`) — market hours only |
| `/trading/market-status` | GET | Check if US stock market is currently open |
| `/trading/portfolios/{agent}/orders` | GET | Order history |
| `/trading/portfolios/{agent}/snapshots` | GET | Performance snapshots for charting |
| `/trading/portfolios/{agent}/reset` | POST | Reset portfolio to starting cash |
| `/trading/summary` | GET | Aggregate summary across all agents |

---

## Configuration

### Paper Trading (`papertrader/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `PAPER_TRADING_HOST` | `127.0.0.1` | Bind host |
| `PAPER_TRADING_PORT` | `51433` | Bind port |
| `PAPER_TRADING_DB_PATH` | `./data/papertrader.db` | SQLite database path |
| `PAPER_TRADING_DEFAULT_STARTING_CASH` | `100000` | Starting cash per portfolio |

### Jaxon (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_PAPER_TRADING_ENABLED` | `false` | Enable the `paper_trade` tool |
| `ASSISTANT_PAPER_TRADING_URL` | _(empty)_ | Paper Trading service URL |
