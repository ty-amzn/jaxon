"""Agents command — list available agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_agents(chat: ChatInterface, args: list[str]) -> None:
    """Handle /agents command."""
    orchestrator = getattr(chat, "_orchestrator", None)

    if orchestrator is None:
        chat._console.print("[yellow]Agent system is not enabled.[/yellow]")
        chat._console.print("[dim]Set ASSISTANT_AGENTS_ENABLED=true to enable.[/dim]")
        return

    agents = orchestrator._loader.list_agents()

    if not agents:
        chat._console.print("[dim]No agents defined. Add .yaml files to data/agents/.[/dim]")
        return

    if args and args[0].lower() == "reload":
        orchestrator._loader.reload()
        agents = orchestrator._loader.list_agents()
        chat._console.print(f"[green]Reloaded {len(agents)} agent definitions.[/green]")
        return

    chat._console.print(f"\n[bold]Available Agents ({len(agents)})[/bold]\n")
    for agent in agents:
        chat._console.print(f"  [cyan]{agent.name}[/cyan] — {agent.description}")
        if agent.allowed_tools:
            chat._console.print(f"    [dim]Tools: {', '.join(agent.allowed_tools)}[/dim]")
        if agent.model:
            chat._console.print(f"    [dim]Model: {agent.model}[/dim]")

    chat._console.print(
        "\n[dim]Agents are called via delegate_to_agent tool. Use /agents reload to refresh.[/dim]"
    )
