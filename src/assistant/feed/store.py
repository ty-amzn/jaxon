"""SQLite store for the internal feed ("Town Square")."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlite_utils

def _rows_to_dicts(cursor) -> list[dict]:
    """Convert raw cursor rows to list of dicts."""
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


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
                    "feed_id": int,
                },
                pk="id",
                not_null={"author", "content", "created_at"},
            )
        else:
            # Migration: add feed_id column if missing
            cols = {c.name for c in self._db["posts"].columns}
            if "feed_id" not in cols:
                self._db.execute("ALTER TABLE posts ADD COLUMN feed_id INTEGER")

        # Feeds table
        if "feeds" not in self._db.table_names():
            self._db["feeds"].create(
                {
                    "id": int,
                    "name": str,
                    "description": str,
                    "created_by": str,
                    "created_at": str,
                },
                pk="id",
                not_null={"name", "created_at"},
            )
            self._db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_feeds_name ON feeds(name)")

        # Seed defaults if table is empty
        count = self._db.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
        if count == 0:
            self._seed_default_feeds()

    def _seed_default_feeds(self) -> None:
        """Seed default themed feeds on first run."""
        now = datetime.now(timezone.utc).isoformat()
        defaults = [
            ("research", "Papers, reports, and scholarly findings", "system"),
            ("dev", "Code changes, bug fixes, and feature completions", "system"),
            ("news", "Current events, articles, and interesting links", "system"),
            ("briefings", "Task summaries, digests, and completed work", "system"),
            ("void", "Hot takes, sarcasm, and unfiltered opinions", "system"),
        ]
        for name, desc, author in defaults:
            self._db["feeds"].insert({
                "name": name,
                "description": desc,
                "created_by": author,
                "created_at": now,
            })

    # ------------------------------------------------------------------
    # Feed CRUD
    # ------------------------------------------------------------------

    def create_feed(self, name: str, description: str, created_by: str) -> dict:
        """Create a new themed feed. Raises ValueError if name already exists."""
        existing = self.get_feed(name)
        if existing:
            raise ValueError(f"Feed '{name}' already exists.")
        row = {
            "name": name,
            "description": description,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self._db["feeds"].insert(row)
        row["id"] = result.last_pk
        return row

    def list_feeds(self) -> list[dict]:
        """Return all feeds with post counts."""
        sql = (
            "SELECT f.id, f.name, f.description, f.created_by, f.created_at, "
            "COUNT(p.id) AS post_count "
            "FROM feeds f LEFT JOIN posts p ON p.feed_id = f.id AND p.reply_to IS NULL "
            "GROUP BY f.id ORDER BY f.name"
        )
        rows = self._db.execute(sql).fetchall()
        return [
            {"id": r[0], "name": r[1], "description": r[2], "created_by": r[3],
             "created_at": r[4], "post_count": r[5]}
            for r in rows
        ]

    def total_root_post_count(self) -> int:
        """Return total number of root (non-reply) posts across all feeds."""
        row = self._db.execute(
            "SELECT COUNT(*) FROM posts WHERE reply_to IS NULL"
        ).fetchone()
        return row[0] if row else 0

    def get_feed(self, name: str) -> dict | None:
        """Return a feed by slug name, or None."""
        rows = list(self._db["feeds"].rows_where("name = ?", [name]))
        return rows[0] if rows else None

    def delete_feed(self, name: str) -> bool:
        """Delete a feed by name. Orphaned posts become global. Returns True if existed."""
        feed = self.get_feed(name)
        if feed is None:
            return False
        # Unlink posts from this feed
        self._db.execute("UPDATE posts SET feed_id = NULL WHERE feed_id = ?", [feed["id"]])
        self._db["feeds"].delete(feed["id"])
        return True

    def get_feed_posts(
        self,
        feed_id: int,
        limit: int = 50,
        before_id: int | None = None,
    ) -> list[dict]:
        """Return top-level posts for a specific feed, newest first."""
        sql = "SELECT * FROM posts WHERE reply_to IS NULL AND feed_id = ?"
        params: list = [feed_id]
        if before_id is not None:
            sql += " AND id < ?"
            params.append(before_id)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return _rows_to_dicts(self._db.execute(sql, params))

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------

    def create_post(
        self,
        author: str,
        content: str,
        reply_to: int | None = None,
        feed_id: int | None = None,
    ) -> dict:
        """Insert a new post and return it as a dict."""
        row = {
            "author": author,
            "content": content,
            "reply_to": reply_to,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "feed_id": feed_id,
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

    def edit_post(self, post_id: int, content: str) -> dict | None:
        """Update a post's content. Returns updated post or None if not found."""
        post = self.get_post(post_id)
        if post is None:
            return None
        self._db["posts"].update(post_id, {"content": content})
        post["content"] = content
        return post

    def delete_post(self, post_id: int) -> bool:
        """Delete a post and its replies. Returns True if it existed."""
        post = self.get_post(post_id)
        if post is None:
            return False
        # Delete replies first
        self._db.execute("DELETE FROM posts WHERE reply_to = ?", [post_id])
        self._db["posts"].delete(post_id)
        return True
