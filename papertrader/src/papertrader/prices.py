"""Yahoo Finance price fetcher for paper trading."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


async def fetch_price(symbol: str) -> dict[str, Any]:
    """Fetch current price for a single symbol.

    Returns dict with keys: symbol, price, currency, name.
    Raises ValueError if symbol not found or API error.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Empty symbol")

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = await client.get(
                YAHOO_CHART_URL.format(symbol=symbol),
                params={"interval": "1d", "range": "1d"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Ticker not found: {symbol}")
        raise ValueError(f"Yahoo Finance API error: {e.response.status_code}")
    except httpx.HTTPError as e:
        raise ValueError(f"Yahoo Finance API error: {e}")

    chart = data.get("chart", {})
    results = chart.get("result")
    if not results:
        error = chart.get("error", {})
        raise ValueError(f"Could not find ticker: {symbol}. {error.get('description', '')}")

    meta = results[0].get("meta", {})
    price = meta.get("regularMarketPrice")
    if price is None:
        raise ValueError(f"No price available for {symbol}")

    return {
        "symbol": symbol,
        "price": float(price),
        "currency": meta.get("currency", "USD"),
        "name": meta.get("shortName") or meta.get("longName") or symbol,
    }


async def fetch_prices(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch current prices for multiple symbols.

    Returns {symbol: {symbol, price, currency, name}} for successful lookups.
    Failed symbols are silently skipped.
    """
    results: dict[str, dict[str, Any]] = {}
    for sym in symbols:
        try:
            results[sym.upper()] = await fetch_price(sym)
        except ValueError:
            logger.warning("Failed to fetch price for %s", sym)
    return results
