"""Slash command: /watch — manage filesystem monitoring."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_watch(chat: ChatInterface, args: list[str]) -> None:
    """Handle /watch command."""
    console = chat._console

    if not chat._settings.watchdog_enabled:
        console.print("[yellow]Watchdog is not enabled. Set ASSISTANT_WATCHDOG_ENABLED=true[/yellow]")
        return

    monitor = getattr(chat, "_file_monitor", None)
    if monitor is None:
        console.print("[yellow]File monitor not initialized.[/yellow]")
        return

    subcommand = args[0] if args else "list"

    if subcommand == "list":
        paths = monitor.watched_paths
        if not paths:
            console.print("[dim]No watched paths.[/dim]")
            return
        console.print("[bold]Watched Paths:[/bold]")
        for p in paths:
            console.print(f"  {p}")

    elif subcommand == "add" and len(args) > 1:
        path = args[1]
        if monitor.add_path(path):
            console.print(f"[green]Now watching: {path}[/green]")
        else:
            console.print(f"[yellow]Already watching or failed: {path}[/yellow]")

    elif subcommand == "remove" and len(args) > 1:
        path = args[1]
        if monitor.remove_path(path):
            console.print(f"[green]Stopped watching: {path}[/green]")
        else:
            console.print(f"[red]Not watching: {path}[/red]")

    else:
        console.print(
            "[bold]Usage:[/bold]\n"
            "  /watch list             — List watched paths\n"
            "  /watch add <path>       — Start watching a path\n"
            "  /watch remove <path>    — Stop watching a path"
        )
