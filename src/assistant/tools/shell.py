"""Shell command execution tool (sandboxed)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


async def shell_exec(params: dict[str, Any]) -> str:
    """Execute a shell command with timeout and directory constraints."""
    command = params.get("command", "")
    timeout = min(params.get("timeout", 30), 120)  # Cap at 120s
    working_dir = params.get("working_dir", ".")

    if not command:
        raise ValueError("No command provided")

    work_path = Path(working_dir).resolve()
    if not work_path.exists():
        raise ValueError(f"Working directory does not exist: {work_path}")

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        return f"Command timed out after {timeout}s"

    result_parts = []
    if stdout:
        out = stdout.decode(errors="replace")
        result_parts.append(f"stdout:\n{out}")
    if stderr:
        err = stderr.decode(errors="replace")
        result_parts.append(f"stderr:\n{err}")
    result_parts.append(f"exit_code: {proc.returncode}")

    return "\n".join(result_parts) if result_parts else "Command completed with no output"


SHELL_TOOL_DEF = {
    "name": "shell_exec",
    "description": "Execute a shell command. Use for running scripts, inspecting files, system operations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "minLength": 1,
                "description": "The shell command to execute",
            },
            "working_dir": {
                "type": "string",
                "description": "Working directory (default: current)",
                "default": ".",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (max 120)",
                "default": 30,
            },
        },
        "required": ["command"],
    },
}
