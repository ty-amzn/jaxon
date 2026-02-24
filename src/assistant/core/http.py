"""Shared httpx client factory with working SSL on macOS.

uv-managed Python on macOS fails SSL verification with httpx's default
context.  Passing an explicit ``ssl.create_default_context()`` fixes it
because that path correctly loads the system certificate store.
"""

from __future__ import annotations

import ssl
from typing import Any

import httpx


def _ssl_context() -> ssl.SSLContext:
    """Return an SSL context that works with the macOS system cert store."""
    return ssl.create_default_context()


def make_httpx_client(**kwargs: Any) -> httpx.AsyncClient:
    """Create an ``httpx.AsyncClient`` with SSL verification that works on macOS.

    Accepts the same keyword arguments as ``httpx.AsyncClient``.
    If ``verify`` is not explicitly provided, uses the system SSL context.
    """
    kwargs.setdefault("verify", _ssl_context())
    return httpx.AsyncClient(**kwargs)
