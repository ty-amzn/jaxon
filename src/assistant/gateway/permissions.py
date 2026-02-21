"""Permission manager with injected approval callback."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionCategory(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    NETWORK_READ = "network_read"
    NETWORK_WRITE = "network_write"


@dataclass
class PermissionRequest:
    tool_name: str
    action_category: ActionCategory
    details: dict[str, Any]
    description: str

    @property
    def requires_approval(self) -> bool:
        return self.action_category not in (
            ActionCategory.READ,
            ActionCategory.NETWORK_READ,
        )


# Read-only shell commands that are auto-approved
_READ_COMMANDS = re.compile(
    r"^(ls|cat|head|tail|wc|find|grep|rg|which|whoami|pwd|echo|date|file|stat|du|df|env|printenv|uname)\b"
)


ApprovalCallback = Callable[[PermissionRequest], Awaitable[bool]]


def classify_shell_command(command: str) -> ActionCategory:
    """Classify a shell command into an action category."""
    cmd = command.strip()
    if _READ_COMMANDS.match(cmd):
        return ActionCategory.READ
    if cmd.startswith(("rm ", "rm\t", "rmdir ")):
        return ActionCategory.DELETE
    return ActionCategory.WRITE


def classify_http_method(method: str) -> ActionCategory:
    if method.upper() == "GET":
        return ActionCategory.NETWORK_READ
    return ActionCategory.NETWORK_WRITE


class PermissionManager:
    """Checks permissions and calls approval callback when needed."""

    def __init__(self, approval_callback: ApprovalCallback) -> None:
        self._approve = approval_callback

    def classify_tool_call(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> PermissionRequest:
        if tool_name == "shell_exec":
            cmd = tool_input.get("command", "")
            category = classify_shell_command(cmd)
            return PermissionRequest(
                tool_name=tool_name,
                action_category=category,
                details=tool_input,
                description=f"Execute: {cmd}",
            )
        elif tool_name == "read_file":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.READ,
                details=tool_input,
                description=f"Read: {tool_input.get('path', '')}",
            )
        elif tool_name == "write_file":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.WRITE,
                details=tool_input,
                description=f"Write: {tool_input.get('path', '')}",
            )
        elif tool_name == "http_request":
            method = tool_input.get("method", "GET")
            category = classify_http_method(method)
            return PermissionRequest(
                tool_name=tool_name,
                action_category=category,
                details=tool_input,
                description=f"{method} {tool_input.get('url', '')}",
            )
        else:
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.WRITE,
                details=tool_input,
                description=f"Unknown tool: {tool_name}",
            )

    async def check(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> tuple[bool, PermissionRequest]:
        """Check if a tool call is allowed. Returns (allowed, request)."""
        request = self.classify_tool_call(tool_name, tool_input)
        if not request.requires_approval:
            return True, request
        allowed = await self._approve(request)
        return allowed, request
