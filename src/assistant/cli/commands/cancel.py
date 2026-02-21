"""Cancel command."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_cancel(chat: ChatInterface, args: list[str]) -> None:
    chat.cancel()
    chat._console.print("[yellow]Cancelled current operation.[/yellow]")
