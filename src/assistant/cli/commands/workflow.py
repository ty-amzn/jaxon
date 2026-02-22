"""Slash command: /workflow — manage and run workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_workflow(chat: ChatInterface, args: list[str]) -> None:
    """Handle /workflow command."""
    console = chat._console

    workflow_manager = getattr(chat, "_workflow_manager", None)
    workflow_runner = getattr(chat, "_workflow_runner", None)

    if workflow_manager is None:
        console.print("[yellow]Workflow system not initialized.[/yellow]")
        return

    subcommand = args[0] if args else "list"

    if subcommand == "list":
        workflows = workflow_manager.list_workflows()
        if not workflows:
            console.print("[dim]No workflows defined. Add YAML files to data/workflows/[/dim]")
            return

        console.print("[bold]Workflows:[/bold]")
        for wf in workflows:
            status = "[green]enabled[/green]" if wf["enabled"] else "[red]disabled[/red]"
            console.print(
                f"  {wf['name']}: {wf['description']} "
                f"({wf['steps']} steps, trigger={wf['trigger']}, {status})"
            )

    elif subcommand == "run" and len(args) > 1:
        name = args[1]
        definition = workflow_manager.get(name)
        if not definition:
            console.print(f"[red]Workflow not found: {name}[/red]")
            return
        if not definition.enabled:
            console.print(f"[yellow]Workflow '{name}' is disabled.[/yellow]")
            return

        console.print(f"[bold]Running workflow: {name}[/bold]")
        if workflow_runner:
            results = await workflow_runner.run(definition)
            for r in results:
                status = r["status"]
                color = "green" if status == "success" else "red" if status == "error" else "yellow"
                detail = r.get("output", r.get("error", r.get("reason", "")))
                console.print(f"  [{color}]{r['step']}: {status}[/{color}] {detail}")
        else:
            console.print("[yellow]Workflow runner not available.[/yellow]")

    elif subcommand == "reload":
        workflow_manager.load()
        count = len(workflow_manager.list_workflows())
        console.print(f"[green]Reloaded {count} workflows.[/green]")

    else:
        console.print(
            "[bold]Usage:[/bold]\n"
            "  /workflow list           — List all workflows\n"
            "  /workflow run <name>     — Run a workflow\n"
            "  /workflow reload         — Reload workflow definitions"
        )
