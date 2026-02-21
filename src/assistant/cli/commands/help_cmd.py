"""Help command."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_help(chat: ChatInterface, args: list[str]) -> None:
    registry = chat._command_registry
    if not registry:
        chat._console.print("[red]No commands registered[/red]")
        return

    chat._console.print("\n[bold]Available Commands[/bold]\n")
    for name, desc in sorted(registry.commands.items()):
        chat._console.print(f"  [cyan]/{name}[/cyan] — {desc}")
    chat._console.print()
