"""Background tasks command — list and inspect background agent tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_tasks(chat: ChatInterface, args: list[str]) -> None:
    """List background tasks or show a specific task's result.

    Usage:
        /tasks              — list all background tasks
        /tasks result <id>  — show full result of a task
    """
    bg_manager = getattr(chat, "_bg_manager", None)
    if bg_manager is None:
        chat._console.print("[yellow]Background tasks not available (agents not enabled).[/yellow]")
        return

    # /tasks result <id>
    if len(args) >= 2 and args[0] == "result":
        task_id = args[1]
        bt = bg_manager.get(task_id)
        if bt is None:
            chat._console.print(f"[red]No task found with ID: {task_id}[/red]")
            return
        chat._console.print(f"[bold]Task {bt.id}[/bold] ({bt.agent_name}): {bt.status.value}")
        if bt.result:
            from rich.markdown import Markdown
            chat._console.print(Markdown(bt.result))
        elif bt.error:
            chat._console.print(f"[red]{bt.error}[/red]")
        else:
            chat._console.print("[dim]No result yet.[/dim]")
        return

    # /tasks — list all
    tasks = bg_manager.list_all()
    if not tasks:
        chat._console.print("[dim]No background tasks.[/dim]")
        return

    status_colors = {
        "pending": "yellow",
        "running": "blue",
        "done": "green",
        "error": "red",
    }

    for bt in tasks:
        color = status_colors.get(bt.status.value, "white")
        desc = bt.task_description[:60] + ("..." if len(bt.task_description) > 60 else "")
        chat._console.print(
            f"  [{color}]{bt.status.value:7s}[/{color}]  {bt.id}  {bt.agent_name}: {desc}"
        )
