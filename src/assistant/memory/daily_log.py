"""Append-only daily markdown logs."""

from __future__ import annotations

import aiofiles
from datetime import datetime, timezone
from pathlib import Path


class DailyLog:
    """Manages daily conversation logs as markdown files."""

    def __init__(self, log_dir: Path) -> None:
        self._dir = log_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, date: datetime | None = None) -> Path:
        dt = date or datetime.now(timezone.utc)
        return self._dir / f"{dt.strftime('%Y-%m-%d')}.md"

    def read_today(self, max_chars: int = 2000) -> str:
        path = self._path_for()
        if not path.exists():
            return ""
        content = path.read_text()
        if len(content) > max_chars:
            return f"...(earlier entries truncated)...\n{content[-max_chars:]}"
        return content

    async def append_exchange(
        self,
        user_message: str,
        assistant_response: str,
        tool_calls: list[dict] | None = None,
    ) -> None:
        path = self._path_for()
        now = datetime.now(timezone.utc)

        if not path.exists():
            header = f"# {now.strftime('%Y-%m-%d')}\n\n"
        else:
            header = ""

        parts = [
            f"{header}## {now.strftime('%H:%M:%S UTC')}",
            f"**User:** {user_message}",
            f"**Assistant:** {assistant_response}",
        ]

        if tool_calls:
            parts.append("### Tool Calls")
            for tc in tool_calls:
                name = tc.get("name", "unknown")
                inp = tc.get("input", {})
                output = tc.get("output", "")
                parts.append(f"- `{name}({inp})` → {output}")

        parts.append("---\n")

        async with aiofiles.open(path, "a") as f:
            await f.write("\n".join(parts) + "\n")
