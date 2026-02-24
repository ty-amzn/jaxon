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
        self._tool_categories: dict[str, ActionCategory] = {}

    @staticmethod
    def _is_google_calendar_enabled() -> bool:
        try:
            from assistant.core.config import get_settings
            return get_settings().google_calendar_enabled
        except Exception:
            return False

    def register_tool_category(self, tool_name: str, category: str | ActionCategory) -> None:
        """Register the action category for a plugin/dynamic tool."""
        if isinstance(category, str):
            category = ActionCategory(category)
        self._tool_categories[tool_name] = category

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
        elif tool_name == "memory_search":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.READ,
                details=tool_input,
                description=f"Memory search: {tool_input.get('query', '')}",
            )
        elif tool_name == "memory_store":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.WRITE,
                details=tool_input,
                description=f"Memory store [{tool_input.get('section', '')}]: {tool_input.get('fact', '')}",
            )
        elif tool_name == "update_identity":
            action = tool_input.get("action", "read")
            if action == "read":
                cat = ActionCategory.READ
            else:
                cat = ActionCategory.WRITE
            return PermissionRequest(
                tool_name=tool_name,
                action_category=cat,
                details=tool_input,
                description=f"Identity {action}",
            )
        elif tool_name == "memory_forget":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.DELETE,
                details=tool_input,
                description=f"Memory forget: {tool_input.get('query', '')} (scope={tool_input.get('scope', 'topic')})",
            )
        elif tool_name == "manage_skill":
            action = tool_input.get("action", "list")
            if action == "list":
                cat = ActionCategory.READ
            else:
                cat = ActionCategory.WRITE
            return PermissionRequest(
                tool_name=tool_name,
                action_category=cat,
                details=tool_input,
                description=f"Skill {action}: {tool_input.get('name', '')}",
            )
        elif tool_name == "manage_agent":
            action = tool_input.get("action", "list")
            if action in ("list", "reload"):
                cat = ActionCategory.READ
            elif action == "delete":
                cat = ActionCategory.DELETE
            else:
                cat = ActionCategory.WRITE
            return PermissionRequest(
                tool_name=tool_name,
                action_category=cat,
                details=tool_input,
                description=f"Agent {action}: {tool_input.get('name', '')}",
            )
        elif tool_name == "browse_web":
            action = tool_input.get("action", "extract")
            if action in ("click", "fill"):
                cat = ActionCategory.NETWORK_WRITE
            else:
                cat = ActionCategory.NETWORK_READ
            return PermissionRequest(
                tool_name=tool_name,
                action_category=cat,
                details=tool_input,
                description=f"Browse ({action}): {tool_input.get('url', '')}",
            )
        elif tool_name == "web_fetch":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.NETWORK_READ,
                details=tool_input,
                description=f"Fetch: {tool_input.get('url', '')}",
            )
        elif tool_name == "pdf_read":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.NETWORK_READ,
                details=tool_input,
                description=f"PDF: {tool_input.get('url', '')}",
            )
        elif tool_name == "arxiv_search":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.NETWORK_READ,
                details=tool_input,
                description=f"arXiv: {tool_input.get('query', '')}",
            )
        elif tool_name == "get_weather":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.NETWORK_READ,
                details=tool_input,
                description=f"Weather: {tool_input.get('location', '')}",
            )
        elif tool_name == "task_status":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.READ,
                details=tool_input,
                description=f"Check task: {tool_input.get('task_id', '')}",
            )
        elif tool_name == "web_search":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.NETWORK_READ,
                details=tool_input,
                description=f"Search: {tool_input.get('query', '')}",
            )
        elif tool_name == "schedule_reminder":
            action = tool_input.get("action", "create")
            if action == "list":
                cat = ActionCategory.READ
                desc = "List reminders"
            elif action == "cancel":
                cat = ActionCategory.DELETE
                desc = f"Cancel reminder: {tool_input.get('job_id', '')}"
            else:
                cat = ActionCategory.WRITE
                desc = f"Schedule: {tool_input.get('description', '')}"
            return PermissionRequest(
                tool_name=tool_name,
                action_category=cat,
                details=tool_input,
                description=desc,
            )
        elif tool_name == "calendar":
            action = tool_input.get("action", "list")
            google_enabled = self._is_google_calendar_enabled()
            if google_enabled:
                # Google Calendar: all actions hit the network
                if action in ("list", "today"):
                    cat = ActionCategory.NETWORK_READ
                elif action == "delete":
                    cat = ActionCategory.NETWORK_WRITE
                elif action in ("add_feed", "remove_feed", "sync_feeds"):
                    cat = ActionCategory.NETWORK_READ  # just returns info message
                else:
                    cat = ActionCategory.NETWORK_WRITE
            else:
                # SQLite mode: local operations
                if action in ("list", "today"):
                    cat = ActionCategory.READ
                elif action in ("add_feed", "sync_feeds"):
                    cat = ActionCategory.NETWORK_READ
                elif action == "delete":
                    cat = ActionCategory.DELETE
                else:
                    cat = ActionCategory.WRITE
            return PermissionRequest(
                tool_name=tool_name,
                action_category=cat,
                details=tool_input,
                description=f"Calendar {action}: {tool_input.get('title', tool_input.get('event_id', tool_input.get('url', '')))}",
            )
        elif tool_name == "contacts":
            action = tool_input.get("action", "list")
            if action in ("list", "get", "search"):
                cat = ActionCategory.READ
            elif action == "delete":
                cat = ActionCategory.DELETE
            else:
                cat = ActionCategory.WRITE
            return PermissionRequest(
                tool_name=tool_name,
                action_category=cat,
                details=tool_input,
                description=f"Contacts {action}: {tool_input.get('name', tool_input.get('contact_id', tool_input.get('query', '')))}",
            )
        elif tool_name == "send_email":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.NETWORK_READ,
                details=tool_input,
                description=f"Email: {tool_input.get('title', '')}",
            )
        elif tool_name == "run_workflow":
            return PermissionRequest(
                tool_name=tool_name,
                action_category=ActionCategory.WRITE,
                details=tool_input,
                description=f"Run workflow: {tool_input.get('name', '')}",
            )
        elif tool_name in self._tool_categories:
            category = self._tool_categories[tool_name]
            return PermissionRequest(
                tool_name=tool_name,
                action_category=category,
                details=tool_input,
                description=f"Plugin tool: {tool_name}",
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
