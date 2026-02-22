"""Slash command: /schedule — manage scheduled jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_schedule(chat: ChatInterface, args: list[str]) -> None:
    """Handle /schedule command."""
    console = chat._console

    if not chat._settings.scheduler_enabled:
        console.print("[yellow]Scheduler is not enabled. Set ASSISTANT_SCHEDULER_ENABLED=true[/yellow]")
        return

    scheduler = getattr(chat, "_scheduler_manager", None)
    if scheduler is None:
        console.print("[yellow]Scheduler not initialized.[/yellow]")
        return

    subcommand = args[0] if args else "list"

    if subcommand == "list":
        jobs = scheduler.list_jobs()
        if not jobs:
            console.print("[dim]No scheduled jobs.[/dim]")
            return
        console.print("[bold]Scheduled Jobs:[/bold]")
        for job in jobs:
            console.print(f"  {job['id']}: {job['description']} ({job['trigger']})")

    elif subcommand == "remove" and len(args) > 1:
        job_id = args[1]
        if scheduler.remove_job(job_id):
            console.print(f"[green]Removed job: {job_id}[/green]")
        else:
            console.print(f"[red]Job not found: {job_id}[/red]")

    else:
        console.print(
            "[bold]Usage:[/bold]\n"
            "  /schedule list          — List all scheduled jobs\n"
            "  /schedule remove <id>   — Remove a scheduled job\n"
            "\nTo create reminders, use natural language:\n"
            '  "Remind me at 9am to review PRs"'
        )
