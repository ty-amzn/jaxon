"""LLM tool for stock trading via the Paper Trading HTTP API.

The tool name and description are deliberately neutral — agents see this as
a real brokerage tool so they trade seriously.  The backend is actually a
paper-trading simulator with no real money involved.
"""

from __future__ import annotations

from typing import Any

import httpx

from assistant.agents.background import current_agent_name

PAPER_TRADE_DEF: dict[str, Any] = {
    "name": "stock_trade",
    "description": (
        "Execute stock trades on your brokerage account. You have a funded "
        "account with a cash balance. Trades execute at live market prices. "
        "Only available during US market hours (Mon-Fri 9:30 AM - 4:00 PM ET, "
        "excluding holidays).\n\n"
        "Actions:\n"
        "- buy: Buy shares of a stock at current market price\n"
        "- sell: Sell shares you hold at current market price\n"
        "- portfolio: View your current positions and P&L\n"
        "- history: View your recent trade history\n"
        "- market_status: Check if the market is currently open"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["buy", "sell", "portfolio", "history", "market_status"],
                "description": "The trading action to perform.",
            },
            "symbol": {
                "type": "string",
                "description": "Stock ticker symbol (e.g. 'AAPL', 'MSFT'). Required for buy/sell.",
            },
            "quantity": {
                "type": "number",
                "description": "Number of shares to buy or sell. Required for buy/sell.",
            },
        },
        "required": ["action"],
    },
}


def _make_paper_trade(base_url: str):
    """Factory: returns an async handler that trades via Paper Trading HTTP API."""

    async def paper_trade(params: dict[str, Any]) -> str:
        action = params.get("action")
        agent = current_agent_name.get("assistant")

        async with httpx.AsyncClient(timeout=30) as client:
            if action == "buy" or action == "sell":
                symbol = params.get("symbol", "").strip().upper()
                quantity = params.get("quantity")
                if not symbol:
                    return "Error: 'symbol' is required for buy/sell."
                if not quantity or quantity <= 0:
                    return "Error: 'quantity' must be a positive number."

                resp = await client.post(
                    f"{base_url}/trading/trade",
                    json={
                        "agent_name": agent,
                        "symbol": symbol,
                        "side": action,
                        "quantity": float(quantity),
                    },
                )
                data = resp.json()
                if "error" in data:
                    return f"Error: {data['error']}"

                order = data["order"]
                price_info = data.get("price_info", {})
                name = price_info.get("name", symbol)

                lines = [
                    f"Order executed: {'Bought' if action == 'buy' else 'Sold'} {order['quantity']:.0f} shares of {name} ({symbol})",
                    f"Price: ${order['price']:,.2f}",
                    f"Total: ${order['total']:,.2f}",
                    f"Cash remaining: ${order['cash_remaining']:,.2f}",
                ]
                if "realized_pnl" in order:
                    pnl = order["realized_pnl"]
                    sign = "+" if pnl >= 0 else ""
                    lines.append(f"Realized P&L: {sign}${pnl:,.2f}")
                return "\n".join(lines)

            elif action == "portfolio":
                resp = await client.get(f"{base_url}/trading/portfolios/{agent}")
                data = resp.json()
                if "error" in data:
                    return "No portfolio yet. Execute a trade to get started."

                p = data["portfolio"]
                positions = data.get("positions", [])

                lines = [
                    f"Portfolio for {agent}",
                    f"Total value: ${p['total_value']:,.2f}",
                    f"Cash: ${p['current_cash']:,.2f}",
                    f"Invested: ${p['positions_value']:,.2f}",
                ]
                pnl = p["pnl"]
                sign = "+" if pnl >= 0 else ""
                lines.append(f"P&L: {sign}${pnl:,.2f} ({sign}{p['pnl_pct']:.2f}%)")
                lines.append("")

                if not positions:
                    lines.append("No open positions.")
                else:
                    lines.append("Positions:")
                    for pos in positions:
                        pos_pnl = pos["pnl"]
                        pos_sign = "+" if pos_pnl >= 0 else ""
                        lines.append(
                            f"  {pos['symbol']}: {pos['quantity']:.0f} shares @ "
                            f"${pos['avg_cost']:,.2f} → ${pos['current_price']:,.2f} "
                            f"({pos_sign}${pos_pnl:,.2f}, {pos_sign}{pos['pnl_pct']:.1f}%)"
                        )
                return "\n".join(lines)

            elif action == "history":
                resp = await client.get(f"{base_url}/trading/portfolios/{agent}/orders")
                data = resp.json()
                if "error" in data:
                    return "No portfolio yet. Execute a trade to get started."

                orders = data.get("orders", [])
                if not orders:
                    return "No trade history yet."

                lines = [f"Recent trades for {agent}:", ""]
                for o in orders[:15]:
                    side = o["side"].upper()
                    lines.append(
                        f"  {o['executed_at'][:16]} {side} {o['quantity']:.0f} "
                        f"{o['symbol']} @ ${o['price']:,.2f} = ${o['total']:,.2f}"
                    )
                return "\n".join(lines)

            elif action == "market_status":
                resp = await client.get(f"{base_url}/trading/market-status")
                data = resp.json()
                status = "OPEN" if data["is_open"] else "CLOSED"
                lines = [
                    f"Market is {status}",
                    f"Current time: {data['current_time_et']}",
                    f"Trading hours: {data['hours']}",
                ]
                if data.get("reason"):
                    lines.append(data["reason"])
                return "\n".join(lines)

        return f"Error: unknown action '{action}'. Use buy, sell, portfolio, history, or market_status."

    return paper_trade
