"""Tests for the finance tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from assistant.tools.finance_tool import finance


def _mock_response(data: dict, status_code: int = 200):
    """Create a mock httpx response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json.return_value = data
    return resp


def _mock_client(*responses):
    """Create a mock async httpx client that returns responses in order."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=list(responses))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# --- Stock tests ---


@pytest.mark.asyncio
async def test_stock_quote_success():
    data = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 189.84,
                        "previousClose": 187.50,
                        "currency": "USD",
                        "shortName": "Apple Inc.",
                        "fiftyTwoWeekLow": 140.0,
                        "fiftyTwoWeekHigh": 199.62,
                    },
                    "indicators": {
                        "quote": [{"volume": [None, None, None, None, 52_300_000]}]
                    },
                }
            ]
        }
    }
    client = _mock_client(_mock_response(data))

    with patch("assistant.tools.finance_tool.make_httpx_client", return_value=client):
        result = await finance({"action": "stock", "symbol": "AAPL"})

    assert "Apple Inc." in result
    assert "AAPL" in result
    assert "189.84" in result
    assert "+2.34" in result
    assert "+1.25%" in result
    assert "52" in result  # 52-week


@pytest.mark.asyncio
async def test_stock_quote_not_found():
    data = {
        "chart": {
            "result": None,
            "error": {"description": "No data found"},
        }
    }
    client = _mock_client(_mock_response(data))

    with patch("assistant.tools.finance_tool.make_httpx_client", return_value=client):
        result = await finance({"action": "stock", "symbol": "XYZXYZ"})

    assert "Could not find ticker" in result


@pytest.mark.asyncio
async def test_stock_no_symbol():
    result = await finance({"action": "stock", "symbol": ""})
    assert "No ticker symbol" in result


@pytest.mark.asyncio
async def test_stock_api_error():
    client = _mock_client()
    client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    with patch("assistant.tools.finance_tool.make_httpx_client", return_value=client):
        result = await finance({"action": "stock", "symbol": "AAPL"})

    assert "API error" in result


# --- Crypto tests ---


@pytest.mark.asyncio
async def test_crypto_price_success():
    data = {
        "bitcoin": {
            "usd": 67234.50,
            "usd_24h_change": 2.35,
            "usd_market_cap": 1_320_000_000_000,
            "usd_24h_vol": 28_500_000_000,
        }
    }
    client = _mock_client(_mock_response(data))

    with patch("assistant.tools.finance_tool.make_httpx_client", return_value=client):
        result = await finance({"action": "crypto", "coin": "btc"})

    assert "Bitcoin" in result
    assert "67,234.50" in result
    assert "+2.35%" in result
    assert "1.32T" in result or "1,320" in result


@pytest.mark.asyncio
async def test_crypto_not_found_with_suggestion():
    price_data = {}
    search_data = {"coins": [{"id": "bitcoin", "name": "Bitcoin"}]}

    price_resp = _mock_response(price_data)
    search_resp = _mock_response(search_data)
    # Two separate clients will be created (two `async with` blocks)
    client1 = _mock_client(price_resp)
    client2 = _mock_client(search_resp)

    call_count = 0

    def mock_make_client(**kwargs):
        nonlocal call_count
        call_count += 1
        return client1 if call_count == 1 else client2

    with patch("assistant.tools.finance_tool.make_httpx_client", side_effect=mock_make_client):
        result = await finance({"action": "crypto", "coin": "btcoin"})

    assert "Did you mean" in result
    assert "Bitcoin" in result


@pytest.mark.asyncio
async def test_crypto_no_coin():
    result = await finance({"action": "crypto", "coin": ""})
    assert "No coin provided" in result


# --- Currency tests ---


@pytest.mark.asyncio
async def test_currency_convert_success():
    data = {
        "amount": 100,
        "base": "USD",
        "date": "2026-02-26",
        "rates": {"EUR": 92.45},
    }
    client = _mock_client(_mock_response(data))

    with patch("assistant.tools.finance_tool.make_httpx_client", return_value=client):
        result = await finance(
            {"action": "currency", "amount": 100, "from": "USD", "to": "EUR"}
        )

    assert "100" in result
    assert "USD" in result
    assert "92.45" in result
    assert "EUR" in result
    assert "European Central Bank" in result


@pytest.mark.asyncio
async def test_currency_no_amount():
    result = await finance({"action": "currency", "from": "USD", "to": "EUR"})
    assert "No amount" in result


@pytest.mark.asyncio
async def test_currency_api_error():
    client = _mock_client()
    client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    with patch("assistant.tools.finance_tool.make_httpx_client", return_value=client):
        result = await finance(
            {"action": "currency", "amount": 100, "from": "USD", "to": "EUR"}
        )

    assert "API error" in result


# --- General tests ---


@pytest.mark.asyncio
async def test_unknown_action():
    result = await finance({"action": "options"})
    assert "Unknown finance action" in result
