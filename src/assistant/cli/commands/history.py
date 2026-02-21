"""History search command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_history(chat: ChatInterface, args: list[str]) -> None:
    if not args:
        chat._console.print("Usage: /history <search query>")
        return

    query = " ".join(args)
    results = chat._memory.search.search(query)

    if not results:
        chat._console.print(f"[dim]No results for: {query}[/dim]")
        return

    table = Table(title=f"Search: {query}")
    table.add_column("Time", style="dim")
    table.add_column("Role", style="cyan")
    table.add_column("Content", max_width=80)

    for row in results:
        content = str(row.get("content", ""))[:100]
        table.add_row(
            row.get("timestamp", ""),
            row.get("role", ""),
            content,
        )

    chat._console.print(table)
