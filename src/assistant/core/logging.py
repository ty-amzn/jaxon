"""Structured logging and append-only JSONL audit trail."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_MAX_OUTPUT_LEN = 10_000


def _sanitize(value: Any) -> Any:
    """Strip ANSI escapes and truncate large strings."""
    if isinstance(value, str):
        cleaned = _ANSI_RE.sub("", value)
        if len(cleaned) > _MAX_OUTPUT_LEN:
            cleaned = cleaned[:_MAX_OUTPUT_LEN] + f"... (truncated, {len(cleaned)} total)"
        return cleaned
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


class AuditLogger:
    """Append-only JSONL audit logger."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event_type: str,
        *,
        session_id: str = "",
        tool_name: str = "",
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        action_category: str = "",
        approval_required: bool = False,
        duration_ms: int = 0,
        error: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
        }
        if session_id:
            entry["session_id"] = session_id
        if tool_name:
            entry["tool_name"] = tool_name
        if input_data:
            entry["input"] = _sanitize(input_data)
        if output_data:
            entry["output"] = _sanitize(output_data)
        if action_category:
            entry["action_category"] = action_category
        if approval_required:
            entry["approval_required"] = True
        if duration_ms:
            entry["duration_ms"] = duration_ms
        if error:
            entry["error"] = _sanitize(error)
        if extra:
            entry.update(_sanitize(extra))

        with open(self._path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")


def setup_logging(log_level: str = "INFO", app_log_path: Path | None = None) -> None:
    """Configure structured application logging."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if app_log_path:
        app_log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(app_log_path)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )
