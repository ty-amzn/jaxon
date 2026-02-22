"""Skills command — list and manage skills."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_skills(chat: ChatInterface, args: list[str]) -> None:
    """Handle /skills command to list available skills."""
    memory = chat._memory

    if not memory.skills:
        chat._console.print("[yellow]Skills system not configured.[/yellow]")
        return

    skills = memory.skills.list_skills()

    if not skills:
        chat._console.print(
            "[dim]No skills found. Add .md files to data/skills/ directory.[/dim]"
        )
        return

    # Handle subcommands
    if args:
        subcommand = args[0].lower()

        if subcommand == "reload":
            memory.skills.reload()
            skills = memory.skills.list_skills()
            chat._console.print(f"[green]Reloaded {len(skills)} skills.[/green]")
            return

        # Try to show specific skill details
        skill = memory.skills.get_skill(subcommand)
        if skill:
            chat._console.print(f"\n[bold]Skill: {skill.name}[/bold]\n")
            chat._console.print(f"[dim]{skill.path}[/dim]\n")
            chat._console.print(skill.content)
            return

        chat._console.print(f"[red]Unknown skill or subcommand: {subcommand}[/red]")
        return

    # List all skills
    chat._console.print(f"\n[bold]Available Skills ({len(skills)})[/bold]\n")
    for skill in skills:
        # Get first line as a preview
        first_line = skill.content.split("\n")[0][:60]
        if len(skill.content.split("\n")[0]) > 60:
            first_line += "..."
        chat._console.print(f"  • [cyan]{skill.name}[/cyan]: {first_line}")

    chat._console.print(
        "\n[dim]Use /skills <name> for details, /skills reload to refresh.[/dim]"
    )