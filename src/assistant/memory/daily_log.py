"""Append-only daily markdown logs."""

from __future__ import annotations

import aiofiles
from datetime import datetime, timedelta, timezone
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

    def read_recent(self, max_chars: int = 4000) -> str:
        """Read a rolling window of recent context from today and yesterday.

        Prioritises today's entries; fills remaining budget with yesterday's.
        """
        now = datetime.now(timezone.utc)
        today_path = self._path_for(now)
        yesterday_path = self._path_for(now - timedelta(days=1))

        today_content = today_path.read_text() if today_path.exists() else ""
        yesterday_content = yesterday_path.read_text() if yesterday_path.exists() else ""

        if not today_content and not yesterday_content:
            return ""

        # Today gets full budget; yesterday fills the remainder
        if len(today_content) >= max_chars:
            return f"...(earlier entries truncated)...\n{today_content[-max_chars:]}"

        remaining = max_chars - len(today_content)
        parts: list[str] = []

        if yesterday_content:
            if len(yesterday_content) > remaining:
                yesterday_content = f"...(earlier entries truncated)...\n{yesterday_content[-remaining:]}"
            parts.append(yesterday_content)

        if today_content:
            parts.append(today_content)

        return "\n".join(parts)

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

    def clear_today(self) -> None:
        """Delete today's log file."""
        path = self._path_for()
        if path.exists():
            path.unlink()

    def clear_all(self) -> None:
        """Delete all daily log files."""
        for path in self._dir.glob("*.md"):
            path.unlink()
