"""SQLite store for the internal feed ("Town Square")."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlite_utils

_COLUMNS = ("id", "author", "content", "reply_to", "created_at")


def _rows_to_dicts(cursor) -> list[dict]:
    """Convert raw cursor rows to list of dicts."""
    return [dict(zip(_COLUMNS, row)) for row in cursor.fetchall()]


class FeedStore:
    """Persistent feed backed by SQLite."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._ensure_table()

    def _ensure_table(self) -> None:
        if "posts" not in self._db.table_names():
            self._db["posts"].create(
                {
                    "id": int,
                    "author": str,
                    "content": str,
                    "reply_to": int,
                    "created_at": str,
                },
                pk="id",
                not_null={"author", "content", "created_at"},
            )

    def create_post(
        self,
        author: str,
        content: str,
        reply_to: int | None = None,
    ) -> dict:
        """Insert a new post and return it as a dict."""
        row = {
            "author": author,
            "content": content,
            "reply_to": reply_to,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self._db["posts"].insert(row)
        row["id"] = result.last_pk
        return row

    def get_timeline(
        self,
        limit: int = 50,
        before_id: int | None = None,
    ) -> list[dict]:
        """Return top-level posts (reply_to IS NULL), newest first."""
        sql = "SELECT * FROM posts WHERE reply_to IS NULL"
        params: list = []
        if before_id is not None:
            sql += " AND id < ?"
            params.append(before_id)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return _rows_to_dicts(self._db.execute(sql, params))

    def get_thread(self, post_id: int) -> list[dict]:
        """Return root post + all replies, chronological."""
        sql = "SELECT * FROM posts WHERE id = ? OR reply_to = ? ORDER BY id ASC"
        return _rows_to_dicts(self._db.execute(sql, [post_id, post_id]))

    def get_post(self, post_id: int) -> dict | None:
        """Return a single post by ID, or None."""
        try:
            return self._db["posts"].get(post_id)
        except Exception:
            return None

    def delete_post(self, post_id: int) -> bool:
        """Delete a post. Returns True if it existed."""
        post = self.get_post(post_id)
        if post is None:
            return False
        self._db["posts"].delete(post_id)
        return True
