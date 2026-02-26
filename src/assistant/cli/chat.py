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

from assistant.cli.media import MediaHandler
from assistant.cli.rendering import (
    render_permission_request,
    render_tool_call,
    render_tool_result,
)
from assistant.core.config import Settings
from assistant.core.logging import AuditLogger
from assistant.gateway.permissions import PermissionManager, PermissionRequest, parse_approval_required
from assistant.gateway.session import SessionManager
from assistant.gateway.thread_store import ThreadStore
from assistant.llm.router import LLMRouter
from assistant.llm.context import build_messages, build_system_prompt
from assistant.llm.tools import create_tool_registry, register_orchestrator_tools
from assistant.llm.types import Role, StreamEventType, ToolCall, ToolResult
from assistant.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class ChatInterface:
    """Interactive CLI chat with streaming markdown rendering."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._console = Console()

        # Thread store for persistent conversations
        thread_store = ThreadStore(settings.threads_dir)
        self._session_manager = SessionManager(thread_store=thread_store)

        # Memory
        self._memory = MemoryManager(
            identity_path=settings.identity_path,
            memory_path=settings.memory_path,
            daily_log_dir=settings.daily_log_dir,
            search_db_path=settings.search_db_path,
            skills_dir=settings.skills_dir,
            embeddings_db_path=settings.embeddings_db_path if settings.vector_search_enabled else None,
            ollama_base_url=settings.ollama_base_url,
            embedding_model=settings.embedding_model,
            vector_search_enabled=settings.vector_search_enabled,
            timezone=settings.scheduler_timezone,
        )

        # Audit
        self._audit = AuditLogger(settings.audit_log_path)

        # Permissions with CLI approval callback
        approval_tools = parse_approval_required(settings.approval_required_tools)
        self._permissions = PermissionManager(self._cli_approval, approval_required_tools=approval_tools)

        # Tools
        self._tool_registry = create_tool_registry(self._permissions, self._audit, settings, self._memory)

        # LLM client (router between Ollama and Claude)
        self._llm = LLMRouter(settings)

        # Media handler for image uploads
        self._media_handler = MediaHandler(max_size_mb=settings.max_media_size_mb)

        # Plugin system (Phase 4)
        self._plugin_manager: Any = None
        self._hook_dispatcher: Any = None
        if settings.plugins_enabled:
            self._init_plugins(settings)

        # Agent system (Phase 4)
        self._orchestrator: Any = None
        if settings.agents_enabled:
            self._init_agents(settings)

        # Command registry (set up later to avoid circular imports)
        self._command_registry: Any = None

        # Cancellation
        self._cancel_event = asyncio.Event()

        # Track active Live widget so approval prompts can pause it
        self._active_live: Live | None = None

    def _init_plugins(self, settings: Settings) -> None:
        """Initialize the plugin system."""
        from assistant.plugins.hooks import HookDispatcher
        from assistant.plugins.manager import PluginManager
        from assistant.plugins.types import PluginContext

        context = PluginContext(data_dir=settings.data_dir, settings=settings)
        self._plugin_manager = PluginManager(settings.plugins_dir, context)
        self._hook_dispatcher = HookDispatcher(self._plugin_manager)

    def _init_agents(self, settings: Settings) -> None:
        """Initialize the agent orchestration system."""
        from assistant.agents.background import BackgroundTaskManager
        from assistant.agents.loader import AgentLoader
        from assistant.agents.orchestrator import Orchestrator
        from assistant.agents.runner import AgentRunner
        from assistant.tools.agent_tool import MANAGE_AGENT_DEF, _make_manage_agent

        loader = AgentLoader(settings.agents_dir)
        loader.load_all()
        runner = AgentRunner(self._llm, self._tool_registry)
        self._bg_manager = BackgroundTaskManager()
        self._orchestrator = Orchestrator(loader, runner, self._memory, bg_manager=self._bg_manager)

        # Register delegation tools
        register_orchestrator_tools(
            self._tool_registry, self._orchestrator, self._permissions
        )

        # Register agent management tool
        self._tool_registry.register(
            MANAGE_AGENT_DEF["name"],
            MANAGE_AGENT_DEF["description"],
            MANAGE_AGENT_DEF["input_schema"],
            _make_manage_agent(loader),
        )

        # Wire context-too-long fallback via long_context_reader agent
        orchestrator = self._orchestrator

        async def _context_fallback(user_text: str) -> str | None:
            try:
                agent_result = await orchestrator.delegate(
                    agent_name="long_text_reader",
                    task=user_text or "Summarize the paginated output.",
                )
                if agent_result.error:
                    return None
                return agent_result.response or None
            except Exception:
                return None

        self._llm._context_fallback = _context_fallback

    def set_command_registry(self, registry: Any) -> None:
        self._command_registry = registry

    async def _cli_approval(self, request: PermissionRequest) -> bool:
        """Prompt user for approval via CLI."""
        # Pause Live rendering so the prompt isn't overwritten
        if self._active_live:
            self._active_live.stop()
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
        finally:
            if self._active_live:
                self._active_live.start()

    async def _execute_tool(
        self,
        tool_call: ToolCall,
        session: Any = None,
        render: bool = True,
        permission_override: PermissionManager | None = None,
    ) -> ToolResult:
        """Execute a tool call via the registry."""
        if session is None:
            session = self._session_manager.active_session
        if render:
            self._console.print(render_tool_call(tool_call.name, tool_call.input))

        result = await self._tool_registry.execute(
            tool_call, session_id=session.id, permission_override=permission_override,
        )

        if render:
            self._console.print(render_tool_result(result.content, result.is_error))

        session.add_tool_call({
            "name": tool_call.name,
            "input": tool_call.input,
            "output": result.content[:500],
        })

        return result

    async def _process_message(
        self,
        session: Any,
        user_input: str,
        permission_manager: PermissionManager | None = None,
        delivery_callback: Any = None,
        content: str | list[dict] | None = None,
    ) -> str:
        """Core message processing without Rich rendering. Returns full response text.

        This is the headless entry point used by Telegram, scheduler, etc.
        Acquires the session lock to prevent concurrent mutations of shared state.

        Args:
            content: Pre-built multimodal content blocks. When provided, skips
                     @image: parsing and uses this directly as message content.
        """
        # Set delivery callback for background tasks
        from assistant.agents.background import current_delivery, current_images
        token = current_delivery.set(delivery_callback)

        async with session.lock:
            # Dispatch pre_message hook
            if self._hook_dispatcher:
                user_input = await self._hook_dispatcher.pre_message(
                    user_input, session_id=session.id
                )

            if content is not None:
                # Pre-built multimodal content (e.g. from Telegram)
                # If the main model doesn't support vision, save images to files
                has_images = isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "image" for b in content
                )
                if has_images and not self._llm.default_model_supports_vision():
                    message_content = self._save_images_and_augment_text(user_input, content)
                else:
                    message_content = content
            else:
                # Parse @image: references
                clean_text, image_paths = self._media_handler.parse_image_reference(user_input)

                # Load images if any
                images = []
                if image_paths:
                    for img_path in image_paths:
                        img = self._media_handler.load_image(img_path)
                        if img:
                            images.append(img)

                # Build message content (text or multimodal)
                if images:
                    if self._llm.default_model_supports_vision():
                        message_content = self._media_handler.build_multimodal_message(clean_text, images)
                    else:
                        message_content = self._save_images_and_augment_text(clean_text, images)
                else:
                    message_content = user_input

            if isinstance(message_content, list):
                session.add_message(Role.USER, message_content)
                # Extract image blocks so delegation tools can auto-forward them
                img_blocks = [
                    {"data": b["source"]["data"], "media_type": b["source"]["media_type"]}
                    for b in message_content
                    if isinstance(b, dict) and b.get("type") == "image"
                ]
                images_token = current_images.set(img_blocks or None)
            else:
                session.add_message(Role.USER, message_content)
                images_token = current_images.set(None)
            session.clear_tool_calls()

            system_prompt = build_system_prompt(self._memory)
            messages = build_messages(
                session.get_context_messages(self._settings.max_context_messages),
            )

            full_response = ""
            last_error: str | None = None
            max_retries = 10

            # Create tool executor bound to this session (no rendering)
            # Pass permission_override so we never mutate the shared registry attribute
            async def headless_tool_executor(tc: ToolCall) -> ToolResult:
                return await self._execute_tool(
                    tc, session=session, render=False, permission_override=permission_manager,
                )

            for attempt in range(1, max_retries + 1):
                full_response = ""
                last_error = None

                try:
                    async for event in self._llm.stream_with_tool_loop(
                        system=system_prompt,
                        messages=messages,
                        tools=self._tool_registry.definitions,
                        tool_executor=headless_tool_executor,
                        max_tool_rounds=self._settings.max_tool_rounds,
                    ):
                        if event.type == StreamEventType.TEXT_DELTA:
                            full_response += event.text
                        elif event.type == StreamEventType.MESSAGE_COMPLETE:
                            full_response = event.text
                        elif event.type == StreamEventType.ERROR:
                            logger.error("LLM error (attempt %d/%d): %s", attempt, max_retries, event.error)
                            last_error = str(event.error)
                except Exception as exc:
                    logger.error("LLM exception (attempt %d/%d): %s", attempt, max_retries, exc)
                    last_error = str(exc)

                # Success — got a response
                if full_response:
                    break

                # No response and error — retry after backoff (unless last attempt)
                if last_error and attempt < max_retries:
                    delay = min(1 + attempt, 10)  # 2s, 3s, 4s, ... 10s cap
                    logger.info("Retrying LLM call in %ds...", delay)
                    await asyncio.sleep(delay)
                    continue

                # Final attempt failed — return a friendly error message
                if last_error:
                    full_response = (
                        f"Sorry, I wasn't able to process your message after "
                        f"{max_retries} attempts. Error: {last_error}"
                    )
                    break

            # Save to session and memory
            session.add_message(Role.ASSISTANT, full_response)
            await self._memory.save_exchange(
                user_input,
                full_response,
                session_id=session.id,
                tool_calls=session.last_tool_calls,
            )

            # Dispatch post_message hook
            if self._hook_dispatcher:
                await self._hook_dispatcher.post_message(
                    user_input, full_response, session_id=session.id
                )

            current_delivery.reset(token)
            current_images.reset(images_token)
            return full_response

    async def get_response(
        self,
        session_id: str,
        user_input: str,
        permission_manager: PermissionManager | None = None,
        delivery_callback: Any = None,
        content: str | list[dict] | None = None,
    ) -> str:
        """Public headless API for external integrations (Telegram, scheduler, WhatsApp).

        Uses or creates a keyed session and processes the message without rendering.
        Optionally accepts a custom PermissionManager for channel-specific approvals.
        Optionally accepts a delivery_callback for background task result delivery.
        Optionally accepts pre-built multimodal content blocks (e.g. from Telegram photos).
        """
        session = self._session_manager.get_or_create_keyed_session(session_id)
        return await self._process_message(
            session, user_input,
            permission_manager=permission_manager,
            delivery_callback=delivery_callback,
            content=content,
        )

    @staticmethod
    def _save_images_and_augment_text(text: str, images: list[dict]) -> str:
        """Save images to temp files and append paths to the text.

        Used when the main model doesn't support vision so the LLM at least
        knows images were provided and can use tools to process them.
        """
        from assistant.agents.orchestrator import Orchestrator

        img_blocks = [
            {"data": img["source"]["data"], "media_type": img["source"]["media_type"]}
            for img in images
            if isinstance(img, dict) and img.get("type") == "image"
        ]
        if not img_blocks:
            return text
        paths = Orchestrator._save_images_to_temp(img_blocks)
        path_list = "\n".join(f"  - {p}" for p in paths)
        return (
            f"{text}\n\n"
            f"[Note: {len(paths)} image(s) were provided but your model does not "
            f"support vision. The images have been saved to temporary files:\n"
            f"{path_list}\n"
            f"You can use tools (e.g. delegate_to_agent with a vision-capable model) "
            f"to analyze them if needed.]"
        )

    async def _cli_delivery(self, text: str) -> None:
        """Deliver a background task result to the CLI console."""
        self._console.print()
        self._console.print(Markdown(text))

    async def handle_message(self, user_input: str) -> str:
        """Process a user message with Rich Live rendering."""
        # Set delivery callback for background tasks
        from assistant.agents.background import current_delivery, current_images
        token = current_delivery.set(self._cli_delivery)

        # Parse @image: references
        clean_text, image_paths = self._media_handler.parse_image_reference(user_input)

        # Load images if any
        images = []
        if image_paths:
            for img_path in image_paths:
                img = self._media_handler.load_image(img_path)
                if img:
                    images.append(img)
                    self._console.print(f"[dim]Loaded image: {img_path}[/dim]")
                else:
                    self._console.print(f"[yellow]Warning: Could not load image: {img_path}[/yellow]")

        # Build message content (text or multimodal)
        if images:
            if self._llm.default_model_supports_vision():
                message_content = self._media_handler.build_multimodal_message(clean_text, images)
            else:
                message_content = self._save_images_and_augment_text(clean_text, images)
        else:
            message_content = user_input  # Use original text if no images

        session = self._session_manager.active_session
        if isinstance(message_content, list):
            session.add_message(Role.USER, message_content)
            img_blocks = [
                {"data": b["source"]["data"], "media_type": b["source"]["media_type"]}
                for b in message_content
                if isinstance(b, dict) and b.get("type") == "image"
            ]
            images_token = current_images.set(img_blocks or None)
        else:
            session.add_message(Role.USER, message_content)
            images_token = current_images.set(None)
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
            self._active_live = live
            async for event in self._llm.stream_with_tool_loop(
                system=system_prompt,
                messages=messages,
                tools=self._tool_registry.definitions,
                tool_executor=lambda tc: self._execute_tool(tc, session=session),
                max_tool_rounds=self._settings.max_tool_rounds,
            ):
                if self._cancel_event.is_set():
                    break

                if event.type == StreamEventType.TEXT_DELTA:
                    full_response += event.text
                    live.update(Markdown(full_response))
                elif event.type == StreamEventType.TOOL_USE_START:
                    live.update(Text(f"Using tool: {event.text}..."))
                elif event.type == StreamEventType.TOOL_USE_COMPLETE:
                    live.update(Text("Continuing..."))
                elif event.type == StreamEventType.ROUTING_INFO:
                    live.update(Text(f"[{event.provider.value}: {event.model}]"))
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    full_response = event.text
                elif event.type == StreamEventType.ERROR:
                    self._console.print(f"[red]Error: {event.error}[/red]")

        self._active_live = None
        current_delivery.reset(token)
        current_images.reset(images_token)

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

    async def _start_plugins(self) -> None:
        """Discover, load, and start plugins. Register their tools and skills."""
        if self._plugin_manager is None:
            return

        await self._plugin_manager.discover_and_load()
        await self._plugin_manager.start_all()

        # Register plugin tools
        for tool in self._plugin_manager.get_all_tools():
            self._tool_registry.register(
                tool.name, tool.description, tool.input_schema, tool.handler
            )
            self._permissions.register_tool_category(tool.name, tool.permission_category)

        # Register plugin skills
        for skill in self._plugin_manager.get_all_skills():
            self._memory.add_plugin_skill(skill.name, skill.content)

        plugins = self._plugin_manager.plugins
        if plugins:
            self._console.print(
                f"[dim]Loaded {len(plugins)} plugin(s): {', '.join(plugins.keys())}[/dim]"
            )

    async def _stop_plugins(self) -> None:
        """Stop all plugins."""
        if self._plugin_manager:
            await self._plugin_manager.stop_all()

    async def _run_onboarding(self) -> None:
        """First-run setup: ask for name and communication style."""
        self._console.print(
            "[bold yellow]Welcome! Let's set up your assistant.[/bold yellow]\n"
        )

        # Ask for name
        try:
            name = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("What should I call you? ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            name = ""

        # Ask for style
        self._console.print()
        self._console.print(
            "How would you like me to communicate?\n"
            "[dim]Examples: \"casual and witty\", \"formal and concise\", "
            "\"friendly with emoji\"[/dim]\n"
            "[dim]Press Enter to skip and use defaults.[/dim]"
        )
        try:
            style = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Style: ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            style = ""

        # Build identity
        style_line = style if style else "helpful, direct, and concise"
        identity = (
            "# Identity\n\n"
            f"You are a personal AI assistant. You are {style_line}.\n\n"
            "## Core Traits\n"
            "- You remember context from previous conversations via daily logs and durable memory.\n"
            "- You can execute tools (shell commands, file operations, HTTP requests) when needed.\n"
            "- You always ask for permission before performing destructive actions.\n"
            "- You maintain an audit trail of all tool executions.\n\n"
            "## Communication Style\n"
            f"- {style_line.capitalize()}.\n"
            "- Use markdown formatting when helpful.\n"
            "- When unsure, ask clarifying questions rather than guessing.\n"
        )
        await self._memory.identity.write(identity)

        # Save name to durable memory
        if name:
            await self._memory.durable.append("User Preferences", f"User's name: {name}")
            self._console.print(f"\n[green]Nice to meet you, {name}![/green]")
        else:
            self._console.print()

        self._console.print("[dim]Setup complete. You can change these anytime by chatting.[/dim]\n")

    async def run(self) -> None:
        """Main interactive chat loop."""
        # Sync configured calendar feeds
        from assistant.tools.calendar_tool import sync_configured_feeds

        try:
            await sync_configured_feeds()
        except Exception:
            pass  # logged inside sync_configured_feeds

        # Start plugins
        await self._start_plugins()

        # Dispatch session_start hook
        if self._hook_dispatcher:
            await self._hook_dispatcher.session_start()

        self._console.print(
            "[bold blue]AI Assistant[/bold blue] - Type /help for commands, Ctrl+C to exit\n"
        )

        # First-run onboarding if identity is not set up
        if not self._memory.identity.load().strip():
            await self._run_onboarding()

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
                if self._hook_dispatcher:
                    await self._hook_dispatcher.session_end()
                await self._stop_plugins()
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
