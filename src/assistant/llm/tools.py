"""Tool definitions and registry setup for Anthropic API format."""

from __future__ import annotations

from assistant.core.logging import AuditLogger
from assistant.gateway.permissions import PermissionManager
from assistant.tools.file_tool import READ_FILE_DEF, WRITE_FILE_DEF, read_file, write_file
from assistant.tools.http_tool import HTTP_TOOL_DEF, http_request
from assistant.tools.registry import ToolRegistry
from assistant.tools.shell import SHELL_TOOL_DEF, shell_exec


def create_tool_registry(
    permission_manager: PermissionManager,
    audit_logger: AuditLogger,
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

    return registry
