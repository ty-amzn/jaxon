"""Tests for the browser tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from assistant.gateway.permissions import ActionCategory, PermissionManager
from assistant.tools.browser_tool import BROWSE_WEB_DEF, browse_web


# ── Schema validation ──────────────────────────────────────────────


def test_tool_definition_schema():
    assert BROWSE_WEB_DEF["name"] == "browse_web"
    schema = BROWSE_WEB_DEF["input_schema"]
    assert schema["required"] == ["url"]
    props = schema["properties"]
    assert "url" in props
    assert "action" in props
    assert set(props["action"]["enum"]) == {"extract", "screenshot", "click", "fill", "evaluate"}
    assert "selector" in props
    assert "value" in props
    assert "expression" in props
    assert "wait_for" in props
    assert "timeout" in props


# ── Permission classification ──────────────────────────────────────


@pytest.mark.parametrize(
    "action,expected_category",
    [
        ("extract", ActionCategory.NETWORK_READ),
        ("screenshot", ActionCategory.NETWORK_READ),
        ("evaluate", ActionCategory.NETWORK_READ),
        ("click", ActionCategory.NETWORK_WRITE),
        ("fill", ActionCategory.NETWORK_WRITE),
    ],
)
def test_permission_classification(action, expected_category):
    pm = PermissionManager(AsyncMock())
    req = pm.classify_tool_call("browse_web", {"url": "https://example.com", "action": action})
    assert req.action_category == expected_category


def test_permission_default_action_is_network_read():
    pm = PermissionManager(AsyncMock())
    req = pm.classify_tool_call("browse_web", {"url": "https://example.com"})
    assert req.action_category == ActionCategory.NETWORK_READ


# ── Validation ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_browse_web_no_url():
    with pytest.raises(ValueError, match="No URL provided"):
        await browse_web({"url": ""})


@pytest.mark.asyncio
async def test_browse_web_click_requires_selector():
    with pytest.raises(ValueError, match="requires a 'selector'"):
        await browse_web({"url": "https://example.com", "action": "click"})


@pytest.mark.asyncio
async def test_browse_web_fill_requires_selector():
    with pytest.raises(ValueError, match="requires a 'selector'"):
        await browse_web({"url": "https://example.com", "action": "fill", "value": "test"})


@pytest.mark.asyncio
async def test_browse_web_fill_requires_value():
    with pytest.raises(ValueError, match="requires a 'value'"):
        await browse_web({"url": "https://example.com", "action": "fill", "selector": "#input"})


@pytest.mark.asyncio
async def test_browse_web_evaluate_requires_expression():
    with pytest.raises(ValueError, match="requires an 'expression'"):
        await browse_web({"url": "https://example.com", "action": "evaluate"})


# ── Mocked browser tests ──────────────────────────────────────────


def _mock_page(body_text: str = "Hello World"):
    """Create a mock Playwright page."""
    page = AsyncMock()
    page.inner_text = AsyncMock(return_value=body_text)
    page.goto = AsyncMock()
    page.close = AsyncMock()
    page.set_default_timeout = MagicMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.evaluate = AsyncMock(return_value="42")
    page.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\nfakedata")
    return page


def _mock_browser(page):
    """Create a mock Playwright browser."""
    browser = AsyncMock()
    browser.is_connected = MagicMock(return_value=True)
    browser.new_page = AsyncMock(return_value=page)
    return browser


@pytest.mark.asyncio
async def test_extract_action():
    page = _mock_page("Page content here")
    browser = _mock_browser(page)

    with patch("assistant.tools.browser_tool._get_browser", return_value=browser):
        result = await browse_web({"url": "https://example.com"})

    assert "Page content here" in result
    assert "Content from https://example.com" in result
    page.goto.assert_awaited_once()
    page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_with_wait_for():
    page = _mock_page("Dynamic content")
    browser = _mock_browser(page)

    with patch("assistant.tools.browser_tool._get_browser", return_value=browser):
        result = await browse_web({"url": "https://example.com", "wait_for": "#main"})

    page.wait_for_selector.assert_awaited_once_with("#main", timeout=30000)
    assert "Dynamic content" in result


@pytest.mark.asyncio
async def test_click_action():
    page = _mock_page("After click")
    browser = _mock_browser(page)

    with patch("assistant.tools.browser_tool._get_browser", return_value=browser):
        result = await browse_web({
            "url": "https://example.com",
            "action": "click",
            "selector": "#btn",
        })

    page.click.assert_awaited_once_with("#btn")
    page.wait_for_load_state.assert_awaited_once_with("networkidle")
    assert "After click" in result


@pytest.mark.asyncio
async def test_fill_action():
    page = _mock_page("Form filled")
    browser = _mock_browser(page)

    with patch("assistant.tools.browser_tool._get_browser", return_value=browser):
        result = await browse_web({
            "url": "https://example.com",
            "action": "fill",
            "selector": "#email",
            "value": "test@example.com",
        })

    page.fill.assert_awaited_once_with("#email", "test@example.com")
    assert "Form filled" in result


@pytest.mark.asyncio
async def test_screenshot_action():
    page = _mock_page()
    browser = _mock_browser(page)

    with patch("assistant.tools.browser_tool._get_browser", return_value=browser):
        result = await browse_web({
            "url": "https://example.com",
            "action": "screenshot",
        })

    page.screenshot.assert_awaited_once_with(full_page=True)
    assert "Screenshot of https://example.com" in result
    assert "base64 PNG" in result


@pytest.mark.asyncio
async def test_evaluate_action():
    page = _mock_page()
    page.evaluate = AsyncMock(return_value="document.title is Test")
    browser = _mock_browser(page)

    with patch("assistant.tools.browser_tool._get_browser", return_value=browser):
        result = await browse_web({
            "url": "https://example.com",
            "action": "evaluate",
            "expression": "document.title",
        })

    page.evaluate.assert_awaited_once_with("document.title")
    assert "JS result" in result
    assert "document.title is Test" in result


@pytest.mark.asyncio
async def test_content_truncation():
    long_content = "x" * 20_000
    page = _mock_page(long_content)
    browser = _mock_browser(page)

    with patch("assistant.tools.browser_tool._get_browser", return_value=browser):
        result = await browse_web({"url": "https://example.com"})

    assert "truncated" in result
    assert "20000 total chars" in result


@pytest.mark.asyncio
async def test_browser_error_handling():
    page = _mock_page()
    page.goto = AsyncMock(side_effect=Exception("Connection refused"))
    browser = _mock_browser(page)

    with patch("assistant.tools.browser_tool._get_browser", return_value=browser):
        result = await browse_web({"url": "https://unreachable.example.com"})

    assert "Browser error" in result
    assert "Connection refused" in result
    page.close.assert_awaited_once()
