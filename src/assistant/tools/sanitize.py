"""Input sanitization for tool parameters."""

from __future__ import annotations

import os
import re
from typing import Any

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = [
    re.compile(r"<\|?(system|im_start|im_end)\|?>", re.IGNORECASE),
    re.compile(r"\bsystem\s*:", re.IGNORECASE),
    re.compile(r"\b(assistant|user)\s*:", re.IGNORECASE),
    re.compile(r"ignore\s+(previous|above|all)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+are\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+)?you\s+are\s+", re.IGNORECASE),
    re.compile(r"from\s+now\s+on,?\s+you\s+", re.IGNORECASE),
]


def strip_injection_patterns(value: str) -> str:
    """Remove common prompt injection markers from a string."""
    result = value
    for pattern in _INJECTION_PATTERNS:
        result = pattern.sub("", result)
    return result


def sanitize_path(path: str, workspace: str | None = None) -> str:
    """Sanitize a file path to prevent directory traversal.

    Resolves the path and ensures it doesn't escape the workspace.
    """
    # Normalize the path
    resolved = os.path.normpath(path)

    # Block traversal patterns — strip ".." components
    if ".." in resolved.split(os.sep):
        parts = [p for p in resolved.split(os.sep) if p != ".."]
        resolved = os.sep.join(parts) or "."

    if workspace:
        workspace = os.path.normpath(workspace)
        # Join with workspace and ensure it stays within
        abs_path = os.path.normpath(os.path.join(workspace, resolved))
        if not abs_path.startswith(workspace):
            return workspace  # Fall back to workspace root
        return abs_path

    return resolved


def sanitize_tool_input(params: dict[str, Any]) -> dict[str, Any]:
    """Sanitize all string values in tool input parameters.

    Applied at the ToolRegistry chokepoint before handler invocation.
    """
    sanitized: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            cleaned = strip_injection_patterns(value)
            # Sanitize paths for path-like keys
            if key in ("path", "file_path", "directory", "target"):
                cleaned = sanitize_path(cleaned)
            sanitized[key] = cleaned
        elif isinstance(value, dict):
            sanitized[key] = sanitize_tool_input(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_tool_input(item) if isinstance(item, dict)
                else strip_injection_patterns(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized
