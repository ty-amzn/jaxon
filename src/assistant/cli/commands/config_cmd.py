"""Config command — display current configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_config(chat: ChatInterface, args: list[str]) -> None:
    s = chat._settings
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_row("Model", s.model)
    table.add_row("Max Tokens", str(s.max_tokens))
    table.add_row("Data Dir", str(s.data_dir))
    table.add_row("Log Level", s.log_level)
    table.add_row("Max Context Messages", str(s.max_context_messages))
    table.add_row("Auto-approve Reads", str(s.auto_approve_reads))
    table.add_row("API Key", "***" + s.anthropic_api_key[-4:] if s.anthropic_api_key else "NOT SET")
    chat._console.print(table)
