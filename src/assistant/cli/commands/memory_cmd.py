"""Memory command — view or update durable memory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_memory(chat: ChatInterface, args: list[str]) -> None:
    if not args:
        content = chat._memory.durable.read()
        if content:
            chat._console.print(Markdown(content))
        else:
            chat._console.print("[dim]No durable memory stored yet.[/dim]")
        return

    if args[0] == "add" and len(args) >= 3:
        section = args[1]
        entry = " ".join(args[2:])
        await chat._memory.durable.append(section, entry)
        chat._console.print(f"[green]Added to {section}: {entry}[/green]")
    else:
        chat._console.print(
            "Usage: /memory — view memory\n"
            "       /memory add <section> <entry> — add an entry"
        )
