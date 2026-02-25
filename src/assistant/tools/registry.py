"""Tool registry for registering, dispatching, and executing tools."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from assistant.core.logging import AuditLogger
from assistant.gateway.permissions import PermissionManager
from assistant.llm.types import ToolCall, ToolResult

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(
        self,
        permission_manager: PermissionManager,
        audit_logger: AuditLogger,
        output_cap: int = 15_000,
    ) -> None:
        self._handlers: dict[str, ToolHandler] = {}
        self._definitions: list[dict[str, Any]] = []
        self._permissions = permission_manager
        self._audit = audit_logger
        self._output_cap = output_cap

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: ToolHandler,
    ) -> None:
        self._handlers[name] = handler
        self._definitions.append({
            "name": name,
            "description": description,
            "input_schema": input_schema,
        })

    def unregister(self, name: str) -> bool:
        """Remove a tool by name. Returns True if found and removed."""
        if name not in self._handlers:
            return False
        del self._handlers[name]
        self._definitions = [d for d in self._definitions if d["name"] != name]
        return True

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return self._definitions

    async def execute(
        self,
        tool_call: ToolCall,
        session_id: str = "",
        permission_override: PermissionManager | None = None,
    ) -> ToolResult:
        """Execute a tool call with permission checking and audit logging."""
        permissions = permission_override or self._permissions
        allowed, perm_request = await permissions.check(
            tool_call.name, tool_call.input
        )

        if not allowed:
            self._audit.log(
                "tool_denied",
                session_id=session_id,
                tool_name=tool_call.name,
                input_data=tool_call.input,
                action_category=perm_request.action_category.value,
                approval_required=True,
            )
            return ToolResult(
                tool_use_id=tool_call.id,
                content="Permission denied by user.",
                is_error=True,
            )

        handler = self._handlers.get(tool_call.name)
        if not handler:
            return ToolResult(
                tool_use_id=tool_call.id,
                content=f"Unknown tool: {tool_call.name}",
                is_error=True,
            )

        # Sanitize inputs before execution
        from assistant.tools.sanitize import sanitize_tool_input

        sanitized_input = sanitize_tool_input(tool_call.input)

        # Log tool call to app log for visibility in serve output
        input_summary = ", ".join(
            f"{k}={v!r}" for k, v in tool_call.input.items()
            if k != "data"  # skip base64 image data
        )
        logger.info("Tool call: %s(%s)", tool_call.name, input_summary)

        start = time.monotonic()
        try:
            result_text = await handler(sanitized_input)
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "Tool result: %s -> %dms, %d chars",
                tool_call.name, duration_ms, len(result_text),
            )
            self._audit.log(
                "tool_call",
                session_id=session_id,
                tool_name=tool_call.name,
                input_data=tool_call.input,
                output_data={"result": result_text[:500]},
                action_category=perm_request.action_category.value,
                approval_required=perm_request.requires_approval,
                duration_ms=duration_ms,
            )
            # Paginate oversized output (skip for read_output_page itself)
            if (
                len(result_text) > self._output_cap
                and tool_call.name != "read_output_page"
            ):
                from assistant.tools.page_cache import get_page_cache

                cache = get_page_cache()
                page_id, total_pages = cache.store(result_text)
                first_page = cache.get_page(page_id, 1)
                assert first_page is not None
                page_text, _ = first_page
                result_text = (
                    f"[Page 1/{total_pages}] Output was {len(result_text):,} chars, "
                    f"paginated into {total_pages} pages.\n"
                    f"Use read_output_page(page_id={page_id!r}, page=N) to read more.\n\n"
                    f"{page_text}"
                )

            return ToolResult(tool_use_id=tool_call.id, content=result_text)
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            error_msg = str(e)
            logger.warning(
                "Tool error: %s -> %dms, %s", tool_call.name, duration_ms, error_msg,
            )
            self._audit.log(
                "tool_error",
                session_id=session_id,
                tool_name=tool_call.name,
                input_data=tool_call.input,
                error=error_msg,
                action_category=perm_request.action_category.value,
                duration_ms=duration_ms,
            )
            return ToolResult(
                tool_use_id=tool_call.id,
                content=f"Error: {error_msg}",
                is_error=True,
            )
