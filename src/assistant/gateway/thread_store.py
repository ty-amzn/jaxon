"""Thread persistence for named conversation threads."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Thread:
    """A named conversation thread with messages."""

    id: str
    name: str
    created_at: str
    updated_at: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Thread":
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=data.get("messages", []),
            metadata=data.get("metadata", {}),
        )


class ThreadStore:
    """Persistent storage for conversation threads."""

    def __init__(self, threads_dir: Path) -> None:
        self._threads_dir = threads_dir
        self._threads_dir.mkdir(parents=True, exist_ok=True)

    def _get_thread_path(self, thread_id: str) -> Path:
        return self._threads_dir / f"{thread_id}.json"

    def _get_name_path(self, name: str) -> Path:
        # Create a safe filename from the name
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return self._threads_dir / f"{safe_name}.json"

    def save(self, thread: Thread) -> None:
        """Save a thread to disk."""
        thread.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._get_thread_path(thread.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(thread.to_dict(), f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved thread: {thread.name} ({thread.id})")

    def load(self, thread_id: str) -> Thread | None:
        """Load a thread by ID."""
        path = self._get_thread_path(thread_id)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return Thread.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load thread {thread_id}: {e}")
            return None

    def load_by_name(self, name: str) -> Thread | None:
        """Load a thread by name."""
        # First, try to find by listing all threads
        for thread in self.list_threads():
            if thread.name.lower() == name.lower():
                return thread
        return None

    def delete(self, thread_id: str) -> bool:
        """Delete a thread."""
        path = self._get_thread_path(thread_id)
        if path.exists():
            path.unlink()
            logger.debug(f"Deleted thread: {thread_id}")
            return True
        return False

    def list_threads(self) -> list[Thread]:
        """List all saved threads."""
        threads = []
        for path in self._threads_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                threads.append(Thread.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load thread from {path}: {e}")
        # Sort by updated_at descending
        threads.sort(key=lambda t: t.updated_at, reverse=True)
        return threads

    def create_thread(self, name: str, thread_id: str | None = None) -> Thread:
        """Create a new thread with the given name."""
        import uuid

        now = datetime.now(timezone.utc).isoformat()
        return Thread(
            id=thread_id or uuid.uuid4().hex[:12],
            name=name,
            created_at=now,
            updated_at=now,
        )

    def export_thread(self, thread: Thread, format: str = "json") -> str:
        """Export a thread in the specified format."""
        if format == "json":
            return json.dumps(thread.to_dict(), indent=2, ensure_ascii=False)
        elif format == "markdown" or format == "md":
            lines = [f"# {thread.name}", f"Created: {thread.created_at}", ""]
            for msg in thread.messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                lines.append(f"**{role.title()}:** {content}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown export format: {format}")