"""Finnhub price fetcher for paper trading.

Uses the Finnhub /quote endpoint for real-time stock prices.
Free tier: 60 calls/min with an API key.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -- Config ------------------------------------------------------------------

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

# -- Price cache (module-level) ----------------------------------------------

_price_cache: dict[str, tuple[float, dict[str, Any]]] = {}  # symbol -> (timestamp, data)
_PRICE_CACHE_TTL = 60  # 60 seconds

# -- Savings APY cache (module-level) ----------------------------------------

_apy_cache: dict[str, float] = {}
_apy_cache_time: float = 0.0
_APY_CACHE_TTL = 3600  # 1 hour
_APY_FALLBACK = 0.045  # 4.5%

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds


def _finnhub_headers() -> dict[str, str]:
    return {"X-Finnhub-Token": FINNHUB_API_KEY}


async def fetch_price(symbol: str) -> dict[str, Any]:
    """Fetch current price for a single symbol via Finnhub.

    Returns dict with keys: symbol, price, currency, name,
    plus open, high, low, prev_close, change_pct.
    Raises ValueError if symbol not found or API error.
    Uses a 60-second cache to stay within rate limits.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Empty symbol")

    if not FINNHUB_API_KEY:
        raise ValueError("FINNHUB_API_KEY not set. Get a free key at https://finnhub.io/")

    # Check cache
    now = time.monotonic()
    cached = _price_cache.get(symbol)
    if cached and (now - cached[0]) < _PRICE_CACHE_TTL:
        return cached[1]

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers=_finnhub_headers(),
            ) as client:
                resp = await client.get(
                    f"{FINNHUB_BASE_URL}/quote",
                    params={"symbol": symbol},
                )
                resp.raise_for_status()
                data = resp.json()
            break  # success
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("Finnhub 429 for %s, retrying in %.0fs (attempt %d)", symbol, delay, attempt + 1)
                await asyncio.sleep(delay)
                last_error = e
                continue
            if e.response.status_code == 401:
                raise ValueError("Invalid FINNHUB_API_KEY. Check your key at https://finnhub.io/")
            raise ValueError(f"Finnhub API error: {e.response.status_code}")
        except httpx.HTTPError as e:
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
                last_error = e
                continue
            raise ValueError(f"Finnhub API error: {e}")
    else:
        raise ValueError(f"Finnhub API error: rate limited (after {_MAX_RETRIES} retries)")

    # Finnhub returns {"c": current, "h": high, "l": low, "o": open, "pc": prevClose, "dp": pctChange, "d": change}
    # A price of 0 means the symbol was not found
    price = data.get("c", 0)
    if not price:
        raise ValueError(f"No price available for {symbol}. Check if the ticker is valid on US exchanges.")

    result = {
        "symbol": symbol,
        "price": float(price),
        "currency": "USD",
        "name": symbol,  # Finnhub /quote doesn't return name; callers can use /profile2 if needed
        "open": data.get("o"),
        "high": data.get("h"),
        "low": data.get("l"),
        "prev_close": data.get("pc"),
        "change": data.get("d"),
        "change_pct": data.get("dp"),
    }

    # Store in cache
    _price_cache[symbol] = (now, result)
    return result


async def fetch_savings_apy() -> float:
    """Fetch annualized yield from BIL (1-3 Month T-Bill ETF).

    Uses Finnhub quote to compare current vs previous close as a rough proxy.
    Caches for 1 hour. Falls back to 4.5% on any error.
    """
    global _apy_cache, _apy_cache_time

    now = time.monotonic()
    if _apy_cache and (now - _apy_cache_time) < _APY_CACHE_TTL:
        return _apy_cache["apy"]

    try:
        info = await fetch_price("BIL")
        # BIL is a T-Bill ETF; its annualized return is approximately the T-Bill rate.
        # Use a rough estimate from price: prevClose vs current over 1 day → annualize.
        # This is very approximate; fallback is fine for paper trading.
        price = info["price"]
        prev = info.get("prev_close") or price
        if prev > 0 and price > 0:
            daily_return = (price - prev) / prev
            # Annualize: (1 + daily)^252 - 1
            apy = (1 + daily_return) ** 252 - 1
            if apy <= 0 or apy > 0.20:
                # Unreasonable → use fallback
                apy = _APY_FALLBACK
        else:
            apy = _APY_FALLBACK

        _apy_cache = {"apy": round(apy, 6)}
        _apy_cache_time = now
        logger.info("Estimated BIL savings APY: %.4f%%", apy * 100)
        return _apy_cache["apy"]

    except Exception:
        logger.warning("Failed to fetch BIL APY, using fallback %.1f%%", _APY_FALLBACK * 100)
        return _APY_FALLBACK


async def fetch_prices(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch current prices for multiple symbols.

    Returns {symbol: {symbol, price, currency, name, ...}} for successful lookups.
    Failed symbols are silently skipped. Uses cache so repeated lookups are free.
    """

    async def _fetch_one(sym: str) -> tuple[str, dict[str, Any] | None]:
        try:
            return sym.upper(), await fetch_price(sym)
        except ValueError:
            logger.warning("Failed to fetch price for %s", sym)
            return sym.upper(), None

    pairs = await asyncio.gather(*[_fetch_one(s) for s in symbols])
    return {sym: data for sym, data in pairs if data is not None}
