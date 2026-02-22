"""Command registry and dispatch for slash commands."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface

CommandHandler = Callable[["ChatInterface", list[str]], Awaitable[None]]


class CommandRegistry:
    """Registry for slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandHandler] = {}
        self._descriptions: dict[str, str] = {}
        self._register_defaults()

    def register(
        self, name: str, handler: CommandHandler, description: str = ""
    ) -> None:
        self._commands[name] = handler
        self._descriptions[name] = description

    def _register_defaults(self) -> None:
        from assistant.cli.commands.cancel import handle_cancel
        from assistant.cli.commands.config_cmd import handle_config
        from assistant.cli.commands.help_cmd import handle_help
        from assistant.cli.commands.history import handle_history
        from assistant.cli.commands.memory_cmd import handle_memory
        from assistant.cli.commands.skills import handle_skills
        from assistant.cli.commands.status import handle_status
        from assistant.cli.commands.thread import handle_thread
        from assistant.cli.commands.schedule import handle_schedule
        from assistant.cli.commands.watch import handle_watch
        from assistant.cli.commands.plugins import handle_plugins
        from assistant.cli.commands.agents import handle_agents
        from assistant.cli.commands.config_backup import handle_backup
        from assistant.cli.commands.workflow import handle_workflow
        from assistant.cli.commands.webhook import handle_webhook

        self.register("help", handle_help, "Show available commands")
        self.register("status", handle_status, "Show session status")
        self.register("memory", handle_memory, "View or update durable memory")
        self.register("history", handle_history, "Search conversation history")
        self.register("cancel", handle_cancel, "Cancel current operation")
        self.register("config", handle_config, "View current configuration")
        self.register("skills", handle_skills, "List and manage available skills")
        self.register("thread", handle_thread, "Manage conversation threads")
        self.register("schedule", handle_schedule, "Manage scheduled reminders")
        self.register("watch", handle_watch, "Manage filesystem monitoring")
        self.register("plugins", handle_plugins, "Manage plugins")
        self.register("agents", handle_agents, "List available agents")
        self.register("backup", handle_backup, "Create, list, or restore data backups")
        self.register("workflow", handle_workflow, "Manage and run workflows")
        self.register("webhook", handle_webhook, "List and test webhooks")

    async def dispatch(self, raw_input: str, chat: ChatInterface) -> None:
        parts = raw_input.strip().split(maxsplit=1)
        cmd_name = parts[0].lstrip("/").lower()
        args = parts[1].split() if len(parts) > 1 else []

        handler = self._commands.get(cmd_name)
        if handler:
            await handler(chat, args)
        else:
            chat._console.print(
                f"[red]Unknown command: /{cmd_name}[/red]. Type /help for available commands."
            )

    @property
    def commands(self) -> dict[str, str]:
        return dict(self._descriptions)
