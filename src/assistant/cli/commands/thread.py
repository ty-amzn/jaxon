"""Thread command — manage conversation threads."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_thread(chat: ChatInterface, args: list[str]) -> None:
    """Handle /thread command for thread management."""
    session_manager = chat._session_manager

    # Check if thread store is available
    if not session_manager._thread_store:
        chat._console.print(
            "[yellow]Thread persistence not configured. "
            "Set ASSISTANT_THREADS_DIR to enable thread saving.[/yellow]"
        )
        return

    if not args:
        # Show current thread status
        session = session_manager.active_session
        if session.thread_id:
            chat._console.print(
                f"[green]Current thread:[/green] {session.thread_name or session.thread_id}"
            )
        else:
            chat._console.print("[dim]No active thread. Use /thread new <name> to create one.[/dim]")
        return

    subcommand = args[0].lower()

    if subcommand == "new":
        if len(args) < 2:
            chat._console.print("[red]Usage: /thread new <name>[/red]")
            return
        name = " ".join(args[1:])
        session = session_manager.create_session(name=name)
        chat._console.print(f"[green]Created new thread:[/green] {name} ({session.id})")

    elif subcommand == "save":
        thread = session_manager.save_current_thread()
        if thread:
            chat._console.print(
                f"[green]Saved thread:[/green] {thread.name} ({thread.id})"
            )
        else:
            chat._console.print("[yellow]No messages to save.[/yellow]")

    elif subcommand == "load":
        if len(args) < 2:
            chat._console.print("[red]Usage: /thread load <name|id>[/red]")
            return
        identifier = " ".join(args[1:])

        # Try loading by name first, then by ID
        session = session_manager.load_thread_by_name(identifier)
        if not session:
            session = session_manager.load_thread(identifier)

        if session:
            chat._console.print(
                f"[green]Loaded thread:[/green] {session.thread_name} ({session.thread_id})"
            )
            chat._console.print(
                f"[dim]{len(session.messages)} messages loaded.[/dim]"
            )
        else:
            chat._console.print(f"[red]Thread not found: {identifier}[/red]")

    elif subcommand == "list" or subcommand == "ls":
        threads = session_manager.list_threads()
        if not threads:
            chat._console.print("[dim]No saved threads.[/dim]")
            return

        chat._console.print(f"\n[bold]Saved Threads ({len(threads)})[/bold]\n")
        for thread in threads[:20]:  # Limit to 20 most recent
            msg_count = len(thread.messages)
            chat._console.print(
                f"  • [cyan]{thread.name}[/cyan] "
                f"[dim]({thread.id}, {msg_count} messages)[/dim]"
            )

    elif subcommand == "export":
        if len(args) < 2:
            chat._console.print("[red]Usage: /thread export <format>[/red]")
            return
        format_type = args[1].lower()

        session = session_manager.active_session
        if not session.messages:
            chat._console.print("[yellow]No messages to export.[/yellow]")
            return

        # Create a temporary thread for export
        thread_store = session_manager._thread_store
        thread = thread_store.create_thread(
            name=session.thread_name or "Export"
        )
        thread.messages = [m.to_api() for m in session.messages]

        try:
            exported = thread_store.export_thread(thread, format_type)
            chat._console.print(f"\n{exported}")
        except ValueError as e:
            chat._console.print(f"[red]{e}[/red]")

    elif subcommand == "delete":
        if len(args) < 2:
            chat._console.print("[red]Usage: /thread delete <id>[/red]")
            return
        thread_id = args[1]
        if session_manager._thread_store.delete(thread_id):
            chat._console.print(f"[green]Deleted thread: {thread_id}[/green]")
        else:
            chat._console.print(f"[red]Thread not found: {thread_id}[/red]")

    else:
        chat._console.print(
            f"[red]Unknown subcommand: {subcommand}[/red]\n"
            "Available: new, save, load, list, export, delete"
        )