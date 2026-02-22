"""SQLite FTS5 search for conversation history."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlite_utils


class SearchIndex:
    """Full-text search over conversation history using SQLite FTS5."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._ensure_table()

    def _ensure_table(self) -> None:
        if "messages" not in self._db.table_names():
            self._db["messages"].create(
                {
                    "id": int,
                    "timestamp": str,
                    "role": str,
                    "content": str,
                    "session_id": str,
                },
                pk="id",
            )
            self._db["messages"].enable_fts(["content", "role"], create_triggers=True)

    def index_message(
        self, role: str, content: str, session_id: str = ""
    ) -> int | None:
        """Index a message. Returns the row ID or None on failure."""
        result = self._db["messages"].insert(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "role": role,
                "content": content,
                "session_id": session_id,
            }
        )
        return result.last_pk

    def search(self, query: str, limit: int = 20) -> list[dict]:
        try:
            rows = list(
                self._db["messages"].search(query, limit=limit)
            )
            return rows
        except Exception:
            return []
