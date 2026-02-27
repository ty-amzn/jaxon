"""Finance tool — stock quotes, crypto prices, and currency conversion via free APIs."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_SEARCH_URL = "https://api.coingecko.com/api/v3/search"
FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"


def _fmt_number(n: float | int | None, prefix: str = "", suffix: str = "") -> str:
    """Format a number with commas and optional prefix/suffix."""
    if n is None:
        return "N/A"
    if isinstance(n, float):
        if abs(n) >= 1_000_000_000:
            return f"{prefix}{n / 1_000_000_000:.2f}B{suffix}"
        if abs(n) >= 1_000_000:
            return f"{prefix}{n / 1_000_000:.2f}M{suffix}"
        if abs(n) >= 1:
            return f"{prefix}{n:,.2f}{suffix}"
        return f"{prefix}{n:.6f}{suffix}"
    return f"{prefix}{n:,}{suffix}"


async def _stock_quote(params: dict[str, Any]) -> str:
    """Fetch stock quote from Yahoo Finance."""
    symbol = params.get("symbol", "").strip().upper()
    if not symbol:
        return "Error: No ticker symbol provided. Use the `symbol` parameter (e.g. 'AAPL')."

    try:
        async with make_httpx_client(timeout=15.0) as client:
            resp = await client.get(
                YAHOO_CHART_URL.format(symbol=symbol),
                params={"interval": "1d", "range": "5d"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Ticker symbol not found: {symbol}"
        return f"Yahoo Finance API error: {e.response.status_code}"
    except httpx.HTTPError as e:
        return f"Yahoo Finance API error: {e}"

    chart = data.get("chart", {})
    results = chart.get("result")
    if not results:
        error = chart.get("error", {})
        return f"Could not find ticker: {symbol}. {error.get('description', '')}"

    result = results[0]
    meta = result.get("meta", {})
    indicators = result.get("indicators", {})
    quotes = indicators.get("quote", [{}])[0]

    price = meta.get("regularMarketPrice")
    prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
    currency = meta.get("currency", "USD")
    name = meta.get("shortName") or meta.get("longName") or symbol

    # Calculate change
    change = None
    change_pct = None
    if price is not None and prev_close is not None and prev_close != 0:
        change = price - prev_close
        change_pct = (change / prev_close) * 100

    # Volume from latest quote data
    volumes = quotes.get("volume", [])
    volume = volumes[-1] if volumes else None

    # 52-week range from meta
    fifty_two_low = meta.get("fiftyTwoWeekLow")
    fifty_two_high = meta.get("fiftyTwoWeekHigh")

    sign = "+" if change and change >= 0 else ""
    lines = [
        f"# {name} ({symbol})",
        "",
        f"- **Price:** {_fmt_number(price, prefix=currency + ' ')}",
    ]
    if change is not None:
        lines.append(f"- **Change:** {sign}{_fmt_number(change)} ({sign}{change_pct:.2f}%)")
    if volume is not None:
        lines.append(f"- **Volume:** {_fmt_number(volume)}")
    if fifty_two_low is not None and fifty_two_high is not None:
        lines.append(f"- **52-Week Range:** {_fmt_number(fifty_two_low)} – {_fmt_number(fifty_two_high)}")
    lines.append(f"- **Currency:** {currency}")

    return "\n".join(lines)


async def _crypto_price(params: dict[str, Any]) -> str:
    """Fetch crypto price from CoinGecko."""
    coin = params.get("coin", "").strip().lower()
    if not coin:
        return "Error: No coin provided. Use the `coin` parameter (e.g. 'bitcoin' or 'btc')."

    # Common symbol → id mapping for convenience
    symbol_map = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "sol": "solana",
        "ada": "cardano",
        "dot": "polkadot",
        "doge": "dogecoin",
        "xrp": "ripple",
        "bnb": "binancecoin",
        "avax": "avalanche-2",
        "matic": "matic-network",
        "link": "chainlink",
        "ltc": "litecoin",
        "uni": "uniswap",
        "atom": "cosmos",
        "shib": "shiba-inu",
    }
    coin_id = symbol_map.get(coin, coin)

    try:
        async with make_httpx_client(timeout=15.0) as client:
            resp = await client.get(
                COINGECKO_PRICE_URL,
                params={
                    "ids": coin_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        return f"CoinGecko API error: {e}"

    if coin_id not in data:
        # Try searching by name
        try:
            async with make_httpx_client(timeout=15.0) as client:
                search_resp = await client.get(
                    COINGECKO_SEARCH_URL,
                    params={"query": coin},
                )
                search_resp.raise_for_status()
                search_data = search_resp.json()
                coins = search_data.get("coins", [])
                if coins:
                    suggestion = coins[0]
                    return (
                        f"Coin '{coin}' not found. Did you mean "
                        f"**{suggestion['name']}** (id: `{suggestion['id']}`)?  "
                        f"Try again with the id."
                    )
        except httpx.HTTPError:
            pass
        return f"Coin not found: {coin}. Try using the CoinGecko id (e.g. 'bitcoin', 'ethereum')."

    info = data[coin_id]
    price = info.get("usd")
    change_24h = info.get("usd_24h_change")
    market_cap = info.get("usd_market_cap")
    volume_24h = info.get("usd_24h_vol")

    sign = "+" if change_24h and change_24h >= 0 else ""
    lines = [
        f"# {coin_id.replace('-', ' ').title()}",
        "",
        f"- **Price:** {_fmt_number(price, prefix='$')}",
    ]
    if change_24h is not None:
        lines.append(f"- **24h Change:** {sign}{change_24h:.2f}%")
    if market_cap is not None:
        lines.append(f"- **Market Cap:** {_fmt_number(market_cap, prefix='$')}")
    if volume_24h is not None:
        lines.append(f"- **24h Volume:** {_fmt_number(volume_24h, prefix='$')}")

    return "\n".join(lines)


async def _currency_convert(params: dict[str, Any]) -> str:
    """Convert currency using Frankfurter API."""
    amount = params.get("amount")
    if amount is None:
        return "Error: No amount provided."

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return f"Error: Invalid amount '{amount}'."

    from_cur = params.get("from", "USD").strip().upper()
    to_cur = params.get("to", "EUR").strip().upper()

    try:
        async with make_httpx_client(timeout=15.0) as client:
            resp = await client.get(
                FRANKFURTER_URL,
                params={"from": from_cur, "to": to_cur, "amount": amount},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Currency not supported: {from_cur} → {to_cur}"
        return f"Frankfurter API error: {e.response.status_code}"
    except httpx.HTTPError as e:
        return f"Frankfurter API error: {e}"

    rates = data.get("rates", {})
    if to_cur not in rates:
        return f"Currency not found in response: {to_cur}"

    converted = rates[to_cur]
    rate = converted / amount if amount != 0 else 0

    return (
        f"# Currency Conversion\n\n"
        f"**{_fmt_number(amount)} {from_cur}** = **{_fmt_number(converted)} {to_cur}**\n\n"
        f"Rate: 1 {from_cur} = {rate:.6f} {to_cur}  \n"
        f"Source: European Central Bank (via Frankfurter)"
    )


async def finance(params: dict[str, Any]) -> str:
    """Finance tool — stock quotes, crypto prices, and currency conversion.

    Args:
        params: Dictionary with 'action' (stock|crypto|currency) and action-specific fields.

    Returns:
        Formatted financial data as markdown.
    """
    action = params.get("action", "stock")

    if action == "stock":
        return await _stock_quote(params)
    elif action == "crypto":
        return await _crypto_price(params)
    elif action == "currency":
        return await _currency_convert(params)
    else:
        return f"Unknown finance action: {action}. Use 'stock', 'crypto', or 'currency'."


FINANCE_TOOL_DEF = {
    "name": "finance",
    "description": (
        "Get financial data: stock quotes, cryptocurrency prices, or currency conversion. "
        "All data comes from free public APIs (Yahoo Finance, CoinGecko, Frankfurter)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["stock", "crypto", "currency"],
                "description": (
                    "The type of financial query: "
                    "'stock' for stock/ETF quotes, "
                    "'crypto' for cryptocurrency prices, "
                    "'currency' for currency conversion."
                ),
            },
            "symbol": {
                "type": "string",
                "description": (
                    "Ticker symbol for stocks (e.g. 'AAPL', 'MSFT', 'TSLA'). "
                    "Used with action='stock'."
                ),
            },
            "coin": {
                "type": "string",
                "description": (
                    "Cryptocurrency name or symbol (e.g. 'bitcoin', 'btc', 'ethereum', 'eth'). "
                    "Used with action='crypto'."
                ),
            },
            "amount": {
                "type": "number",
                "description": "Amount to convert. Used with action='currency'.",
            },
            "from": {
                "type": "string",
                "description": "Source currency code (e.g. 'USD', 'EUR', 'GBP'). Used with action='currency'. Default: 'USD'.",
            },
            "to": {
                "type": "string",
                "description": "Target currency code (e.g. 'EUR', 'JPY', 'GBP'). Used with action='currency'. Default: 'EUR'.",
            },
        },
        "required": ["action"],
    },
}
