"""Interactive chat interface with Rich Live streaming and prompt_toolkit input."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from assistant.cli.rendering import (
    render_permission_request,
    render_tool_call,
    render_tool_result,
)
from assistant.core.config import Settings
from assistant.core.logging import AuditLogger
from assistant.gateway.permissions import PermissionManager, PermissionRequest
from assistant.gateway.session import SessionManager
from assistant.llm.client import ClaudeClient
from assistant.llm.context import build_messages, build_system_prompt
from assistant.llm.tools import create_tool_registry
from assistant.llm.types import Role, StreamEventType, ToolCall, ToolResult
from assistant.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class ChatInterface:
    """Interactive CLI chat with streaming markdown rendering."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._console = Console()
        self._session_manager = SessionManager()

        # Memory
        self._memory = MemoryManager(
            identity_path=settings.identity_path,
            memory_path=settings.memory_path,
            daily_log_dir=settings.daily_log_dir,
            search_db_path=settings.search_db_path,
        )

        # Audit
        self._audit = AuditLogger(settings.audit_log_path)

        # Permissions with CLI approval callback
        self._permissions = PermissionManager(self._cli_approval)

        # Tools
        self._tool_registry = create_tool_registry(self._permissions, self._audit)

        # LLM client
        self._llm = ClaudeClient(
            api_key=settings.anthropic_api_key,
            model=settings.model,
            max_tokens=settings.max_tokens,
        )

        # Command registry (set up later to avoid circular imports)
        self._command_registry: Any = None

        # Cancellation
        self._cancel_event = asyncio.Event()

    def set_command_registry(self, registry: Any) -> None:
        self._command_registry = registry

    async def _cli_approval(self, request: PermissionRequest) -> bool:
        """Prompt user for approval via CLI."""
        self._console.print(
            render_permission_request(
                request.description, request.action_category.value
            )
        )
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Approve? [y/N] ").strip().lower()
            )
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call via the registry."""
        session = self._session_manager.active_session
        self._console.print(render_tool_call(tool_call.name, tool_call.input))

        result = await self._tool_registry.execute(tool_call, session_id=session.id)

        self._console.print(render_tool_result(result.content, result.is_error))

        session.add_tool_call({
            "name": tool_call.name,
            "input": tool_call.input,
            "output": result.content[:500],
        })

        return result

    async def handle_message(self, user_input: str) -> str:
        """Process a user message and return the assistant's response."""
        session = self._session_manager.active_session
        session.add_message(Role.USER, user_input)
        session.clear_tool_calls()

        system_prompt = build_system_prompt(self._memory)
        messages = build_messages(
            session.get_context_messages(self._settings.max_context_messages),
        )

        full_response = ""
        self._cancel_event.clear()

        self._console.print()
        with Live(
            Text("Thinking..."),
            console=self._console,
            refresh_per_second=10,
            transient=True,
        ) as live:
            async for event in self._llm.stream_with_tool_loop(
                system=system_prompt,
                messages=messages,
                tools=self._tool_registry.definitions,
                tool_executor=self._execute_tool,
            ):
                if self._cancel_event.is_set():
                    break

                if event.type == StreamEventType.TEXT_DELTA:
                    full_response += event.text
                    live.update(Markdown(full_response))
                elif event.type == StreamEventType.TOOL_USE_START:
                    live.update(Text(f"Using tool: {event.text}..."))
                elif event.type == StreamEventType.TOOL_USE_COMPLETE:
                    # Tool rendering happens in _execute_tool
                    live.update(Text("Continuing..."))
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    full_response = event.text
                elif event.type == StreamEventType.ERROR:
                    self._console.print(f"[red]Error: {event.error}[/red]")

        # Print final rendered response
        if full_response:
            self._console.print(Markdown(full_response))

        # Save to session and memory
        session.add_message(Role.ASSISTANT, full_response)
        await self._memory.save_exchange(
            user_input,
            full_response,
            session_id=session.id,
            tool_calls=session.last_tool_calls,
        )

        return full_response

    def cancel(self) -> None:
        self._cancel_event.set()

    async def run(self) -> None:
        """Main interactive chat loop."""
        self._console.print(
            "[bold blue]AI Assistant[/bold blue] - Type /help for commands, Ctrl+C to exit\n"
        )

        history_path = self._settings.data_dir / "logs" / ".chat_history"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_session: PromptSession = PromptSession(
            history=FileHistory(str(history_path))
        )

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: prompt_session.prompt("You: "),
                )
            except (EOFError, KeyboardInterrupt):
                self._console.print("\n[dim]Goodbye![/dim]")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # Slash command dispatch
            if user_input.startswith("/"):
                if self._command_registry:
                    await self._command_registry.dispatch(user_input, self)
                else:
                    self._console.print("[red]Commands not available[/red]")
                continue

            try:
                await self.handle_message(user_input)
            except Exception as e:
                logger.exception("Error handling message")
                self._console.print(f"[red]Error: {e}[/red]")
