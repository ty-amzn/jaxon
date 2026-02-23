"""Tool definitions and registry setup for Anthropic API format."""

from __future__ import annotations

from typing import Any

from assistant.core.config import Settings
from assistant.core.logging import AuditLogger
from assistant.gateway.permissions import PermissionManager
from assistant.tools.file_tool import READ_FILE_DEF, WRITE_FILE_DEF, read_file, write_file
from assistant.tools.http_tool import HTTP_TOOL_DEF, http_request
from assistant.tools.memory_tool import (
    MEMORY_FORGET_DEF,
    MEMORY_SEARCH_DEF,
    MEMORY_STORE_DEF,
    UPDATE_IDENTITY_DEF,
    _make_memory_forget,
    _make_memory_search,
    _make_memory_store,
    _make_update_identity,
)
from assistant.tools.registry import ToolRegistry
from assistant.tools.shell import SHELL_TOOL_DEF, shell_exec
from assistant.tools.skill_tool import MANAGE_SKILL_DEF, _make_manage_skill
from assistant.tools.weather_tool import WEATHER_TOOL_DEF, get_weather
from assistant.tools.browser_tool import BROWSE_WEB_DEF, browse_web
from assistant.tools.web_fetch import WEB_FETCH_TOOL_DEF, web_fetch
from assistant.tools.web_search import WEB_SEARCH_TOOL_DEF, web_search
from assistant.tools.pdf_tool import PDF_READ_TOOL_DEF, pdf_read
from assistant.tools.arxiv_tool import ARXIV_SEARCH_TOOL_DEF, arxiv_search
from assistant.tools.email_tool import SEND_EMAIL_DEF, send_email


def register_orchestrator_tools(
    registry: ToolRegistry,
    orchestrator: Any,
    permission_manager: PermissionManager,
) -> None:
    """Register agent delegation tools from an Orchestrator instance."""
    for tool_def in orchestrator.get_tool_definitions():
        handlers = orchestrator.get_tool_handlers()
        handler = handlers.get(tool_def["name"])
        if handler:
            registry.register(
                tool_def["name"],
                tool_def["description"],
                tool_def["input_schema"],
                handler,
            )
            # Delegation tools are read-like (they run in scoped context)
            permission_manager.register_tool_category(tool_def["name"], "read")


def create_tool_registry(
    permission_manager: PermissionManager,
    audit_logger: AuditLogger,
    settings: Settings | None = None,
    memory: Any | None = None,
) -> ToolRegistry:
    """Create and populate the tool registry with all available tools."""
    registry = ToolRegistry(permission_manager, audit_logger)

    registry.register(
        SHELL_TOOL_DEF["name"],
        SHELL_TOOL_DEF["description"],
        SHELL_TOOL_DEF["input_schema"],
        shell_exec,
    )
    registry.register(
        READ_FILE_DEF["name"],
        READ_FILE_DEF["description"],
        READ_FILE_DEF["input_schema"],
        read_file,
    )
    registry.register(
        WRITE_FILE_DEF["name"],
        WRITE_FILE_DEF["description"],
        WRITE_FILE_DEF["input_schema"],
        write_file,
    )
    registry.register(
        HTTP_TOOL_DEF["name"],
        HTTP_TOOL_DEF["description"],
        HTTP_TOOL_DEF["input_schema"],
        http_request,
    )

    # Register web_fetch, pdf_read, arxiv_search (always available)
    registry.register(
        WEB_FETCH_TOOL_DEF["name"],
        WEB_FETCH_TOOL_DEF["description"],
        WEB_FETCH_TOOL_DEF["input_schema"],
        web_fetch,
    )
    registry.register(
        PDF_READ_TOOL_DEF["name"],
        PDF_READ_TOOL_DEF["description"],
        PDF_READ_TOOL_DEF["input_schema"],
        pdf_read,
    )
    registry.register(
        ARXIV_SEARCH_TOOL_DEF["name"],
        ARXIV_SEARCH_TOOL_DEF["description"],
        ARXIV_SEARCH_TOOL_DEF["input_schema"],
        arxiv_search,
    )
    registry.register(
        WEATHER_TOOL_DEF["name"],
        WEATHER_TOOL_DEF["description"],
        WEATHER_TOOL_DEF["input_schema"],
        get_weather,
    )
    registry.register(
        BROWSE_WEB_DEF["name"],
        BROWSE_WEB_DEF["description"],
        BROWSE_WEB_DEF["input_schema"],
        browse_web,
    )

    registry.register(
        SEND_EMAIL_DEF["name"],
        SEND_EMAIL_DEF["description"],
        SEND_EMAIL_DEF["input_schema"],
        send_email,
    )

    # Register web_search if enabled
    if settings and settings.web_search_enabled:
        # Create a wrapper that captures the searxng_url
        searxng_url = settings.searxng_url

        async def web_search_wrapper(params: dict[str, Any]) -> str:
            return await web_search(params, searxng_url)

        registry.register(
            WEB_SEARCH_TOOL_DEF["name"],
            WEB_SEARCH_TOOL_DEF["description"],
            WEB_SEARCH_TOOL_DEF["input_schema"],
            web_search_wrapper,
        )

    # Register memory tools (search + store + forget)
    if memory is not None:
        registry.register(
            MEMORY_SEARCH_DEF["name"],
            MEMORY_SEARCH_DEF["description"],
            MEMORY_SEARCH_DEF["input_schema"],
            _make_memory_search(memory),
        )
        registry.register(
            MEMORY_STORE_DEF["name"],
            MEMORY_STORE_DEF["description"],
            MEMORY_STORE_DEF["input_schema"],
            _make_memory_store(memory),
        )
        registry.register(
            MEMORY_FORGET_DEF["name"],
            MEMORY_FORGET_DEF["description"],
            MEMORY_FORGET_DEF["input_schema"],
            _make_memory_forget(memory),
        )
        registry.register(
            UPDATE_IDENTITY_DEF["name"],
            UPDATE_IDENTITY_DEF["description"],
            UPDATE_IDENTITY_DEF["input_schema"],
            _make_update_identity(memory),
        )

        # Register skill management tool if skills loader is available
        if memory.skills is not None:
            registry.register(
                MANAGE_SKILL_DEF["name"],
                MANAGE_SKILL_DEF["description"],
                MANAGE_SKILL_DEF["input_schema"],
                _make_manage_skill(memory.skills),
            )

    # Register schedule_reminder if scheduler is enabled
    if settings and settings.scheduler_enabled:
        from assistant.scheduler.tool import SCHEDULE_REMINDER_DEF

        # Handler will be set later during wiring (when SchedulerManager is created)
        # Use a placeholder that returns an error until wired
        async def schedule_reminder_placeholder(params: dict[str, Any]) -> str:
            return "Scheduler not yet initialized."

        registry.register(
            SCHEDULE_REMINDER_DEF["name"],
            SCHEDULE_REMINDER_DEF["description"],
            SCHEDULE_REMINDER_DEF["input_schema"],
            schedule_reminder_placeholder,
        )

    return registry
