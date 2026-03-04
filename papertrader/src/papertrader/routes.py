"""Paper Trading API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from papertrader.prices import fetch_price, fetch_prices, fetch_savings_apy
from papertrader.ui import TEMPLATES_DIR

logger = logging.getLogger(__name__)

trading_router = APIRouter(prefix="/trading", tags=["trading"])

# US Eastern timezone (ET) — NYSE/NASDAQ hours
_ET = timezone(timedelta(hours=-5))
_EDT = timezone(timedelta(hours=-4))

# US market holidays for 2025-2026 (NYSE observed closures)
_MARKET_HOLIDAYS: set[tuple[int, int, int]] = {
    # 2025
    (2025, 1, 1), (2025, 1, 20), (2025, 2, 17), (2025, 4, 18),
    (2025, 5, 26), (2025, 6, 19), (2025, 7, 4), (2025, 9, 1),
    (2025, 11, 27), (2025, 12, 25),
    # 2026
    (2026, 1, 1), (2026, 1, 19), (2026, 2, 16), (2026, 4, 3),
    (2026, 5, 25), (2026, 6, 19), (2026, 7, 3), (2026, 9, 7),
    (2026, 11, 26), (2026, 12, 25),
}


def _get_et_now() -> datetime:
    """Get current time in US Eastern.

    Uses a simplified DST rule: EDT (UTC-4) from second Sunday of March
    to first Sunday of November, EST (UTC-5) otherwise.
    """
    utc_now = datetime.now(timezone.utc)
    year = utc_now.year

    # Second Sunday of March
    mar1 = datetime(year, 3, 1, tzinfo=timezone.utc)
    dst_start_day = 8 + (6 - mar1.weekday()) % 7  # second Sunday
    dst_start = datetime(year, 3, dst_start_day, 7, 0, tzinfo=timezone.utc)  # 2am ET = 7am UTC

    # First Sunday of November
    nov1 = datetime(year, 11, 1, tzinfo=timezone.utc)
    dst_end_day = 1 + (6 - nov1.weekday()) % 7
    if dst_end_day == 8:
        dst_end_day = 1
    dst_end = datetime(year, 11, dst_end_day, 6, 0, tzinfo=timezone.utc)  # 2am EDT = 6am UTC

    if dst_start <= utc_now < dst_end:
        return utc_now.astimezone(_EDT)
    return utc_now.astimezone(_ET)


def _is_market_open() -> tuple[bool, str]:
    """Check if US stock market is currently open.

    Returns (is_open, reason_if_closed).
    NYSE/NASDAQ regular hours: Mon-Fri 9:30 AM - 4:00 PM ET.
    """
    now_et = _get_et_now()
    weekday = now_et.weekday()  # 0=Mon, 6=Sun

    if weekday >= 5:
        day_name = "Saturday" if weekday == 5 else "Sunday"
        return False, f"Market is closed ({day_name}). Opens Monday 9:30 AM ET."

    date_tuple = (now_et.year, now_et.month, now_et.day)
    if date_tuple in _MARKET_HOLIDAYS:
        return False, "Market is closed (holiday). Try again on the next trading day."

    hour, minute = now_et.hour, now_et.minute
    market_time = hour * 60 + minute
    open_time = 9 * 60 + 30   # 9:30 AM
    close_time = 16 * 60       # 4:00 PM

    if market_time < open_time:
        return False, f"Market hasn't opened yet. Opens at 9:30 AM ET (currently {now_et.strftime('%I:%M %p ET')})."
    if market_time >= close_time:
        return False, f"Market is closed for the day. Closed at 4:00 PM ET (currently {now_et.strftime('%I:%M %p ET')})."

    return True, ""


class TradeRequest(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=100)
    symbol: str = Field(..., min_length=1, max_length=10)
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)


class SavingsRequest(BaseModel):
    amount: float = Field(..., gt=0)


class NoteRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = Field("general", pattern="^(research|thesis|watchlist|lesson|general)$")
    note_id: int | None = None


# -- Dashboard UI ------------------------------------------------------------

@trading_router.get("/ui", response_class=HTMLResponse)
async def dashboard_ui():
    return HTMLResponse((TEMPLATES_DIR / "dashboard.html").read_text())


# -- Portfolios --------------------------------------------------------------

@trading_router.get("/portfolios")
async def list_portfolios(request: Request):
    """List all portfolios with current values."""
    store = request.app.state.store
    portfolios = store.list_portfolios()

    apy = await fetch_savings_apy()
    enriched = []
    for p in portfolios:
        store.accrue_interest(p["id"], apy)
        # Re-read after accrual
        p = store.get_portfolio(p["agent_name"]) or p

        positions = store.get_positions(p["id"])
        positions_value = 0.0

        if positions:
            symbols = [pos["symbol"] for pos in positions]
            prices = await fetch_prices(symbols)
            for pos in positions:
                info = prices.get(pos["symbol"])
                if info:
                    positions_value += pos["quantity"] * info["price"]

        savings = p.get("savings", 0) or 0
        total_value = p["current_cash"] + savings + positions_value
        pnl = total_value - p["starting_cash"]
        enriched.append({
            **p,
            "positions_value": round(positions_value, 2),
            "total_value": round(total_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / p["starting_cash"]) * 100, 2) if p["starting_cash"] else 0,
            "position_count": len(positions),
        })

    return {"portfolios": enriched}


@trading_router.get("/portfolios/{agent}")
async def get_portfolio(agent: str, request: Request):
    """Get portfolio detail with positions and live prices."""
    store = request.app.state.store
    portfolio = store.get_portfolio(agent)
    if not portfolio:
        return {"error": f"No portfolio found for agent '{agent}'"}

    # Accrue savings interest so balance is current
    apy = await fetch_savings_apy()
    store.accrue_interest(portfolio["id"], apy)
    portfolio = store.get_portfolio(agent)

    positions = store.get_positions(portfolio["id"])
    positions_value = 0.0
    enriched_positions = []

    if positions:
        symbols = [pos["symbol"] for pos in positions]
        prices = await fetch_prices(symbols)
        for pos in positions:
            info = prices.get(pos["symbol"])
            current_price = info["price"] if info else 0
            market_value = pos["quantity"] * current_price
            cost_basis = pos["quantity"] * pos["avg_cost"]
            pnl = market_value - cost_basis
            positions_value += market_value
            enriched_positions.append({
                **pos,
                "current_price": round(current_price, 2),
                "market_value": round(market_value, 2),
                "cost_basis": round(cost_basis, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round((pnl / cost_basis) * 100, 2) if cost_basis else 0,
            })

    savings = portfolio.get("savings", 0) or 0
    total_value = portfolio["current_cash"] + savings + positions_value
    pnl = total_value - portfolio["starting_cash"]

    # Save snapshot for charting
    store.save_snapshot(portfolio["id"], total_value, portfolio["current_cash"], positions_value)

    return {
        "portfolio": {
            **portfolio,
            "positions_value": round(positions_value, 2),
            "total_value": round(total_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / portfolio["starting_cash"]) * 100, 2) if portfolio["starting_cash"] else 0,
        },
        "positions": enriched_positions,
    }


# -- Trading ------------------------------------------------------------------

@trading_router.get("/market-status")
async def market_status():
    """Check if the US stock market is currently open."""
    is_open, reason = _is_market_open()
    now_et = _get_et_now()
    return {
        "is_open": is_open,
        "reason": reason,
        "current_time_et": now_et.strftime("%Y-%m-%d %I:%M %p ET"),
        "hours": "Mon-Fri 9:30 AM - 4:00 PM ET",
    }


@trading_router.post("/trade")
async def execute_trade(body: TradeRequest, request: Request):
    """Execute a buy or sell order at current market price."""
    is_open, reason = _is_market_open()
    if not is_open:
        return {"error": reason}

    store = request.app.state.store

    try:
        price_info = await fetch_price(body.symbol)
    except ValueError as e:
        return {"error": str(e)}

    price = price_info["price"]

    try:
        if body.side == "buy":
            order = store.execute_buy(body.agent_name, body.symbol, body.quantity, price)
        else:
            order = store.execute_sell(body.agent_name, body.symbol, body.quantity, price)
    except ValueError as e:
        return {"error": str(e)}

    return {
        "order": order,
        "price_info": price_info,
    }


# -- Order history ------------------------------------------------------------

@trading_router.get("/portfolios/{agent}/orders")
async def get_orders(agent: str, request: Request, limit: int = 50):
    """Get order history for an agent."""
    store = request.app.state.store
    portfolio = store.get_portfolio(agent)
    if not portfolio:
        return {"error": f"No portfolio found for agent '{agent}'"}

    orders = store.get_orders(portfolio["id"], limit=limit)
    return {"orders": orders}


# -- Snapshots ----------------------------------------------------------------

@trading_router.get("/portfolios/{agent}/snapshots")
async def get_snapshots(agent: str, request: Request, limit: int = 100):
    """Get performance snapshots for charting."""
    store = request.app.state.store
    portfolio = store.get_portfolio(agent)
    if not portfolio:
        return {"error": f"No portfolio found for agent '{agent}'"}

    snapshots = store.get_snapshots(portfolio["id"], limit=limit)
    return {"snapshots": snapshots}


# -- Savings ------------------------------------------------------------------

@trading_router.get("/savings-rate")
async def savings_rate():
    """Return the current savings APY derived from BIL."""
    apy = await fetch_savings_apy()
    return {"apy": apy, "apy_pct": round(apy * 100, 2), "source": "BIL (1-3 Month T-Bill ETF)"}


@trading_router.post("/portfolios/{agent}/savings/deposit")
async def deposit_savings(agent: str, body: SavingsRequest, request: Request):
    """Deposit cash into savings account."""
    store = request.app.state.store
    apy = await fetch_savings_apy()
    try:
        result = store.deposit_savings(agent, body.amount, apy)
    except ValueError as e:
        return {"error": str(e)}
    return result


@trading_router.post("/portfolios/{agent}/savings/withdraw")
async def withdraw_savings(agent: str, body: SavingsRequest, request: Request):
    """Withdraw from savings account to cash."""
    store = request.app.state.store
    apy = await fetch_savings_apy()
    try:
        result = store.withdraw_savings(agent, body.amount, apy)
    except ValueError as e:
        return {"error": str(e)}
    return result


# -- Reset --------------------------------------------------------------------

@trading_router.post("/portfolios/{agent}/reset")
async def reset_portfolio(agent: str, request: Request):
    """Reset a portfolio to starting cash."""
    store = request.app.state.store
    existed = store.reset_portfolio(agent)
    if not existed:
        return {"error": f"No portfolio found for agent '{agent}'"}
    return {"status": "reset", "agent": agent}


# -- Activity log -------------------------------------------------------------

@trading_router.get("/activity")
async def get_activity(request: Request, agent: str | None = None, limit: int = 100):
    """Get activity log, optionally filtered by agent name."""
    store = request.app.state.store
    portfolio_id = None
    if agent:
        portfolio = store.get_portfolio(agent)
        if not portfolio:
            return {"error": f"No portfolio found for agent '{agent}'"}
        portfolio_id = portfolio["id"]

    events = store.get_activity_log(portfolio_id=portfolio_id, limit=limit)
    return {"activity": events}


# -- Agent Notes --------------------------------------------------------------

@trading_router.get("/portfolios/{agent}/notes")
async def get_notes(
    agent: str, request: Request,
    category: str | None = None, q: str | None = None, limit: int = 50,
):
    """List or search notes for an agent."""
    store = request.app.state.store
    if q:
        notes = store.search_notes(agent, q, limit=limit)
    else:
        notes = store.get_notes(agent, category=category, limit=limit)
    return {"notes": notes}


@trading_router.post("/portfolios/{agent}/notes")
async def save_note(agent: str, body: NoteRequest, request: Request):
    """Create or update a note."""
    store = request.app.state.store
    try:
        note = store.save_note(
            agent, body.title, body.content,
            category=body.category, note_id=body.note_id,
        )
    except ValueError as e:
        return {"error": str(e)}
    return {"note": note}


@trading_router.delete("/portfolios/{agent}/notes/{note_id}")
async def delete_note(agent: str, note_id: int, request: Request):
    """Delete a note."""
    store = request.app.state.store
    deleted = store.delete_note(agent, note_id)
    if not deleted:
        return {"error": f"Note {note_id} not found for agent '{agent}'"}
    return {"status": "deleted", "note_id": note_id}


# -- Summary ------------------------------------------------------------------

@trading_router.get("/summary")
async def trading_summary(request: Request):
    """Aggregate summary across all agents."""
    store = request.app.state.store
    portfolios = store.list_portfolios()

    if not portfolios:
        return {
            "agent_count": 0,
            "total_value": 0,
            "total_cash": 0,
            "total_savings": 0,
            "total_invested": 0,
            "total_pnl": 0,
        }

    apy = await fetch_savings_apy()
    total_value = 0.0
    total_cash = 0.0
    total_savings = 0.0
    total_starting = 0.0

    for p in portfolios:
        store.accrue_interest(p["id"], apy)
        p = store.get_portfolio(p["agent_name"]) or p

        positions = store.get_positions(p["id"])
        positions_value = 0.0
        if positions:
            symbols = [pos["symbol"] for pos in positions]
            prices = await fetch_prices(symbols)
            for pos in positions:
                info = prices.get(pos["symbol"])
                if info:
                    positions_value += pos["quantity"] * info["price"]

        savings = p.get("savings", 0) or 0
        total_value += p["current_cash"] + savings + positions_value
        total_cash += p["current_cash"]
        total_savings += savings
        total_starting += p["starting_cash"]

    total_pnl = total_value - total_starting

    return {
        "agent_count": len(portfolios),
        "total_value": round(total_value, 2),
        "total_cash": round(total_cash, 2),
        "total_savings": round(total_savings, 2),
        "total_invested": round(total_value - total_cash - total_savings, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / total_starting) * 100, 2) if total_starting else 0,
    }
