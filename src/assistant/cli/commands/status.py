"""Status command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_status(chat: ChatInterface, args: list[str]) -> None:
    session = chat._session_manager.active_session
    table = Table(title="Session Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    table.add_row("Session ID", session.id)
    table.add_row("Messages", str(len(session.messages)))
    table.add_row("Model", chat._settings.model)
    table.add_row("Max Tokens", str(chat._settings.max_tokens))
    chat._console.print(table)
