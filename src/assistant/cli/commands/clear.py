"""``/clear`` slash command — reset session, history, memory, or search data."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface

_USAGE = (
    "[bold]/clear[/bold] <subcommand>\n"
    "  session  — clear current session messages\n"
    "  history  — delete all daily log files\n"
    "  memory   — wipe durable MEMORY.md\n"
    "  search   — clear FTS5 index and embeddings\n"
    "  all      — all of the above"
)


async def _confirm(chat: "ChatInterface", action: str) -> bool:
    """Prompt the user for confirmation on the CLI."""
    chat._console.print(f"[yellow]This will {action}. Are you sure? [y/N][/yellow]")
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: input().strip().lower()
        )
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


async def handle_clear(chat: "ChatInterface", args: list[str]) -> None:
    if not args:
        chat._console.print(_USAGE)
        return

    sub = args[0].lower()

    if sub == "session":
        if not await _confirm(chat, "clear the current session"):
            return
        session = chat._session_manager.active_session
        session.messages.clear()
        session.clear_tool_calls()
        chat._console.print("[green]Session cleared.[/green]")

    elif sub == "history":
        if not await _confirm(chat, "delete all daily log files"):
            return
        chat._memory.daily_log.clear_all()
        chat._console.print("[green]Daily logs cleared.[/green]")

    elif sub == "memory":
        if not await _confirm(chat, "wipe durable memory (MEMORY.md)"):
            return
        await chat._memory.durable.write("")
        chat._console.print("[green]Durable memory cleared.[/green]")

    elif sub == "search":
        if not await _confirm(chat, "clear the search index and embeddings"):
            return
        chat._memory.search.clear_all()
        if chat._memory.embeddings:
            chat._memory.embeddings.clear_all()
        chat._console.print("[green]Search index cleared.[/green]")

    elif sub == "all":
        if not await _confirm(chat, "clear ALL data (session, history, memory, search)"):
            return
        session = chat._session_manager.active_session
        session.messages.clear()
        session.clear_tool_calls()
        chat._memory.daily_log.clear_all()
        await chat._memory.durable.write("")
        chat._memory.search.clear_all()
        if chat._memory.embeddings:
            chat._memory.embeddings.clear_all()
        chat._console.print("[green]All data cleared.[/green]")

    else:
        chat._console.print(f"[red]Unknown subcommand: {sub}[/red]")
        chat._console.print(_USAGE)
