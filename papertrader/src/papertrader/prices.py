"""Yahoo Finance price fetcher for paper trading."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -- Savings APY cache (module-level) ----------------------------------------

_apy_cache: dict[str, float] = {}
_apy_cache_time: float = 0.0
_APY_CACHE_TTL = 3600  # 1 hour
_APY_FALLBACK = 0.045  # 4.5%

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


async def fetch_savings_apy() -> float:
    """Fetch annualized yield from BIL (1-3 Month T-Bill ETF) trailing 1-year return.

    Caches for 1 hour.  Falls back to 4.5% on any error.
    """
    global _apy_cache, _apy_cache_time

    now = time.monotonic()
    if _apy_cache and (now - _apy_cache_time) < _APY_CACHE_TTL:
        return _apy_cache["apy"]

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = await client.get(
                YAHOO_CHART_URL.format(symbol="BIL"),
                params={"interval": "1d", "range": "1y"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("chart", {}).get("result")
        if not results:
            raise ValueError("No chart data for BIL")

        closes = results[0].get("indicators", {}).get("adjclose")
        if closes:
            adj = closes[0].get("adjclose", [])
        else:
            adj = results[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])

        # Filter out None values
        adj = [v for v in adj if v is not None]
        if len(adj) < 2:
            raise ValueError("Insufficient BIL price data")

        first, last = adj[0], adj[-1]
        apy = (last - first) / first  # trailing 1-year return ≈ annualized

        if apy <= 0:
            apy = _APY_FALLBACK

        _apy_cache = {"apy": round(apy, 6)}
        _apy_cache_time = now
        logger.info("Fetched BIL savings APY: %.4f%%", apy * 100)
        return _apy_cache["apy"]

    except Exception:
        logger.warning("Failed to fetch BIL APY, using fallback %.1f%%", _APY_FALLBACK * 100)
        return _APY_FALLBACK


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
