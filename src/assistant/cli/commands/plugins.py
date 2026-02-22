"""Plugins command — list, info, reload plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_plugins(chat: ChatInterface, args: list[str]) -> None:
    """Handle /plugins command."""
    pm = getattr(chat, "_plugin_manager", None)

    if pm is None:
        chat._console.print("[yellow]Plugin system is not enabled.[/yellow]")
        chat._console.print("[dim]Set ASSISTANT_PLUGINS_ENABLED=true to enable.[/dim]")
        return

    plugins = pm.plugins

    if not args:
        # List all plugins
        if not plugins:
            chat._console.print("[dim]No plugins loaded. Add .py files to data/plugins/.[/dim]")
            return

        chat._console.print(f"\n[bold]Loaded Plugins ({len(plugins)})[/bold]\n")
        for name, plugin in plugins.items():
            m = plugin.manifest
            tools = plugin.get_tools()
            skills = plugin.get_skills()
            hooks = plugin.get_hooks()
            chat._console.print(
                f"  [cyan]{m.name}[/cyan] v{m.version} — {m.description}"
            )
            parts = []
            if tools:
                parts.append(f"{len(tools)} tools")
            if skills:
                parts.append(f"{len(skills)} skills")
            if hooks:
                parts.append(f"{len(hooks)} hooks")
            if parts:
                chat._console.print(f"    [dim]{', '.join(parts)}[/dim]")

        chat._console.print(
            "\n[dim]Use /plugins info <name> or /plugins reload <name>.[/dim]"
        )
        return

    subcommand = args[0].lower()

    if subcommand == "info" and len(args) > 1:
        name = args[1]
        plugin = plugins.get(name)
        if not plugin:
            chat._console.print(f"[red]Plugin not found: {name}[/red]")
            return

        m = plugin.manifest
        chat._console.print(f"\n[bold]{m.name}[/bold] v{m.version}")
        if m.description:
            chat._console.print(f"  {m.description}")
        if m.author:
            chat._console.print(f"  Author: {m.author}")

        tools = plugin.get_tools()
        if tools:
            chat._console.print(f"\n  [bold]Tools ({len(tools)}):[/bold]")
            for t in tools:
                chat._console.print(f"    [cyan]{t.name}[/cyan] — {t.description}")

        skills = plugin.get_skills()
        if skills:
            chat._console.print(f"\n  [bold]Skills ({len(skills)}):[/bold]")
            for s in skills:
                preview = s.content[:60] + "..." if len(s.content) > 60 else s.content
                chat._console.print(f"    [cyan]{s.name}[/cyan] — {preview}")

        hooks = plugin.get_hooks()
        if hooks:
            chat._console.print(f"\n  [bold]Hooks ({len(hooks)}):[/bold]")
            for ht in hooks:
                chat._console.print(f"    [cyan]{ht.value}[/cyan]")

    elif subcommand == "reload":
        name = args[1] if len(args) > 1 else None
        if not name:
            chat._console.print("[red]Usage: /plugins reload <name>[/red]")
            return

        # Unregister old tools/skills
        old_plugin = plugins.get(name)
        if old_plugin:
            for tool in old_plugin.get_tools():
                chat._tool_registry.unregister(tool.name)
            for skill in old_plugin.get_skills():
                chat._memory.remove_plugin_skill(skill.name)

        success = await pm.reload_plugin(name)
        if success:
            # Re-register tools/skills
            new_plugin = pm.plugins.get(name)
            if new_plugin:
                for tool in new_plugin.get_tools():
                    chat._tool_registry.register(
                        tool.name, tool.description, tool.input_schema, tool.handler
                    )
                    chat._permissions.register_tool_category(
                        tool.name, tool.permission_category
                    )
                for skill in new_plugin.get_skills():
                    chat._memory.add_plugin_skill(skill.name, skill.content)
            chat._console.print(f"[green]Reloaded plugin: {name}[/green]")
        else:
            chat._console.print(f"[red]Failed to reload plugin: {name}[/red]")

    elif subcommand == "list":
        # Alias for no-args
        await handle_plugins(chat, [])

    else:
        chat._console.print(
            "[red]Usage: /plugins [list | info <name> | reload <name>][/red]"
        )
