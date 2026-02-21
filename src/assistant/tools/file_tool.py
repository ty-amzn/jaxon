"""File read/write tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiofiles


async def read_file(params: dict[str, Any]) -> str:
    """Read a file's contents."""
    path = params.get("path", "")
    if not path:
        raise ValueError("No path provided")

    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"Not a file: {file_path}")

    async with aiofiles.open(file_path, "r") as f:
        content = await f.read()

    max_len = params.get("max_length", 50_000)
    if len(content) > max_len:
        content = content[:max_len] + f"\n... (truncated, {len(content)} total chars)"

    return content


async def write_file(params: dict[str, Any]) -> str:
    """Write content to a file."""
    path = params.get("path", "")
    content = params.get("content", "")
    if not path:
        raise ValueError("No path provided")

    file_path = Path(path).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(file_path, "w") as f:
        await f.write(content)

    return f"Written {len(content)} chars to {file_path}"


READ_FILE_DEF = {
    "name": "read_file",
    "description": "Read the contents of a file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
            "max_length": {
                "type": "integer",
                "description": "Max chars to return",
                "default": 50000,
            },
        },
        "required": ["path"],
    },
}

WRITE_FILE_DEF = {
    "name": "write_file",
    "description": "Write content to a file. Creates parent directories if needed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to write to"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
}
