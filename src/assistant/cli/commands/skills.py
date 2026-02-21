"""Skills command — stub for Phase 2."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_skills(chat: ChatInterface, args: list[str]) -> None:
    chat._console.print(
        "[dim]Skills system coming in Phase 2. "
        "Skills will allow the assistant to learn and execute custom workflows.[/dim]"
    )
