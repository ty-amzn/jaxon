"""Browser tool — Playwright-based browser for dynamic web content."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 15_000

# Singleton browser instance (lazy-initialized)
_browser = None
_playwright = None


async def _get_browser():
    """Get or create the singleton browser instance."""
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        from playwright.async_api import async_playwright

        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        logger.info("Playwright browser launched")
    return _browser


async def shutdown_browser() -> None:
    """Shut down the singleton browser (call during app teardown)."""
    global _browser, _playwright
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None
        logger.info("Playwright browser shut down")


async def browse_web(params: dict[str, Any]) -> str:
    """Browse a web page using a real browser with JavaScript support.

    Supports extracting content, taking screenshots, clicking elements,
    filling form fields, and evaluating JavaScript.
    """
    url = params.get("url", "")
    if not url:
        raise ValueError("No URL provided")

    action = params.get("action", "extract")
    selector = params.get("selector", "")
    value = params.get("value", "")
    expression = params.get("expression", "")
    wait_for = params.get("wait_for", "")
    timeout = params.get("timeout", 30000)

    if action in ("click", "fill") and not selector:
        raise ValueError(f"Action '{action}' requires a 'selector' parameter")
    if action == "fill" and not value:
        raise ValueError("Action 'fill' requires a 'value' parameter")
    if action == "evaluate" and not expression:
        raise ValueError("Action 'evaluate' requires an 'expression' parameter")

    browser = await _get_browser()
    page = await browser.new_page()

    try:
        page.set_default_timeout(timeout)
        await page.goto(url, wait_until="networkidle", timeout=timeout)

        if wait_for:
            await page.wait_for_selector(wait_for, timeout=timeout)

        if action == "extract":
            content = await page.inner_text("body")
        elif action == "screenshot":
            import base64

            screenshot_bytes = await page.screenshot(full_page=True)
            b64 = base64.b64encode(screenshot_bytes).decode("ascii")
            return f"Screenshot of {url} (base64 PNG, {len(screenshot_bytes)} bytes):\n{b64}"
        elif action == "click":
            await page.click(selector)
            await page.wait_for_load_state("networkidle")
            content = await page.inner_text("body")
        elif action == "fill":
            await page.fill(selector, value)
            content = await page.inner_text("body")
        elif action == "evaluate":
            result = await page.evaluate(expression)
            return f"JS result from {url}:\n{result}"
        else:
            raise ValueError(f"Unknown action: {action}")
    except Exception as e:
        return f"Browser error: {e}"
    finally:
        await page.close()

    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + f"\n\n... (truncated, {len(content)} total chars)"

    return f"# Content from {url}\n\n{content}"


BROWSE_WEB_DEF = {
    "name": "browse_web",
    "description": (
        "Browse a web page using a real browser with full JavaScript support. "
        "Use this for JavaScript-heavy sites (SPAs, dynamic content) that web_fetch cannot handle. "
        "Supports extracting page text, taking screenshots, clicking elements, filling forms, "
        "and evaluating JavaScript expressions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to navigate to",
            },
            "action": {
                "type": "string",
                "enum": ["extract", "screenshot", "click", "fill", "evaluate"],
                "description": "Action to perform: extract (get page text), screenshot (capture PNG), click (click a selector), fill (fill a form field), evaluate (run JavaScript)",
                "default": "extract",
            },
            "selector": {
                "type": "string",
                "description": "CSS selector for click/fill actions",
            },
            "value": {
                "type": "string",
                "description": "Value for fill action",
            },
            "expression": {
                "type": "string",
                "description": "JavaScript expression for evaluate action",
            },
            "wait_for": {
                "type": "string",
                "description": "CSS selector to wait for before performing the action",
            },
            "timeout": {
                "type": "integer",
                "description": "Navigation timeout in milliseconds",
                "default": 30000,
            },
        },
        "required": ["url"],
    },
}
