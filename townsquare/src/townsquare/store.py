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
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.conn.isolation_level = None
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
                    "image_url": str,
                    "pinned_at": str,
                },
                pk="id",
                not_null={"author", "content", "created_at"},
            )
        else:
            # Migration: add feed_id column if missing
            cols = {c.name for c in self._db["posts"].columns}
            if "feed_id" not in cols:
                self._db.execute("ALTER TABLE posts ADD COLUMN feed_id INTEGER")
            if "image_url" not in cols:
                self._db.execute("ALTER TABLE posts ADD COLUMN image_url TEXT")
            if "pinned_at" not in cols:
                self._db.execute("ALTER TABLE posts ADD COLUMN pinned_at TEXT")

        # Reactions table (replaces old likes table)
        if "reactions" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE reactions ("
                "  id INTEGER PRIMARY KEY,"
                "  post_id INTEGER NOT NULL,"
                "  emoji TEXT NOT NULL,"
                "  created_at TEXT NOT NULL,"
                "  UNIQUE(post_id, emoji)"
                ")"
            )
            # Migrate existing likes → ❤️ reactions
            if "likes" in self._db.table_names():
                self._db.execute(
                    "INSERT OR IGNORE INTO reactions (post_id, emoji, created_at) "
                    "SELECT post_id, '❤️', created_at FROM likes"
                )

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

        # Agents table
        if "agents" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE agents ("
                "  name TEXT PRIMARY KEY,"
                "  display_name TEXT NOT NULL,"
                "  tagline TEXT NOT NULL DEFAULT ''"
                ")"
            )

        # Read-state tracking (unread reply notifications)
        if "read_state" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE read_state ("
                "  post_id INTEGER PRIMARY KEY,"
                "  last_read_at TEXT NOT NULL"
                ")"
            )

        # FTS5 full-text search index on posts
        self._ensure_fts()

        # Seed defaults if table is empty
        count = self._db.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
        if count == 0:
            self._seed_default_feeds()
        else:
            self._ensure_default_feeds()

    def _seed_default_feeds(self) -> None:
        """Seed default themed feeds on first run."""
        now = datetime.now(timezone.utc).isoformat()
        defaults = [
            ("research", "Papers, reports, and scholarly findings", "system"),
            ("dev", "Code changes, bug fixes, and feature completions", "system"),
            ("news", "Current events, articles, and interesting links", "system"),
            ("briefings", "Task summaries, digests, and completed work", "system"),
            ("void", "Hot takes, sarcasm, and unfiltered opinions", "system"),
            ("worklog", "Work-in-progress updates, task starts, and status reports", "system"),
            ("trading", "Trade executions, market analysis, and portfolio updates", "system"),
        ]
        for name, desc, author in defaults:
            self._db["feeds"].insert({
                "name": name,
                "description": desc,
                "created_by": author,
                "created_at": now,
            })

    def _ensure_default_feeds(self) -> None:
        """Ensure all default feeds exist (migration for existing DBs)."""
        now = datetime.now(timezone.utc).isoformat()
        defaults = [
            ("research", "Papers, reports, and scholarly findings", "system"),
            ("dev", "Code changes, bug fixes, and feature completions", "system"),
            ("news", "Current events, articles, and interesting links", "system"),
            ("briefings", "Task summaries, digests, and completed work", "system"),
            ("void", "Hot takes, sarcasm, and unfiltered opinions", "system"),
            ("worklog", "Work-in-progress updates, task starts, and status reports", "system"),
            ("trading", "Trade executions, market analysis, and portfolio updates", "system"),
        ]
        for name, desc, author in defaults:
            existing = self.get_feed(name)
            if not existing:
                self._db["feeds"].insert({
                    "name": name,
                    "description": desc,
                    "created_by": author,
                    "created_at": now,
                })

    # ------------------------------------------------------------------
    # FTS5 setup
    # ------------------------------------------------------------------

    def _ensure_fts(self) -> None:
        """Create FTS5 virtual table and sync triggers, backfill if needed."""
        is_new = "posts_fts" not in self._db.table_names()
        if is_new:
            self._db.execute(
                "CREATE VIRTUAL TABLE posts_fts USING fts5("
                "  content, author,"
                "  content='posts', content_rowid='id'"
                ")"
            )
            # Sync triggers: keep FTS in lockstep with posts table
            self._db.execute(
                "CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN"
                "  INSERT INTO posts_fts(rowid, content, author)"
                "  VALUES (new.id, new.content, new.author);"
                "END"
            )
            self._db.execute(
                "CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN"
                "  INSERT INTO posts_fts(posts_fts, rowid, content, author)"
                "  VALUES ('delete', old.id, old.content, old.author);"
                "END"
            )
            self._db.execute(
                "CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN"
                "  INSERT INTO posts_fts(posts_fts, rowid, content, author)"
                "  VALUES ('delete', old.id, old.content, old.author);"
                "  INSERT INTO posts_fts(rowid, content, author)"
                "  VALUES (new.id, new.content, new.author);"
                "END"
            )
            # Backfill existing posts
            count = self._db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            if count > 0:
                self._db.execute(
                    "INSERT INTO posts_fts(rowid, content, author)"
                    " SELECT id, content, author FROM posts"
                )

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
        since: str | None = None,
    ) -> list[dict]:
        """Return top-level posts for a specific feed, newest first."""
        sql = "SELECT * FROM posts WHERE reply_to IS NULL AND feed_id = ?"
        params: list = [feed_id]
        if before_id is not None:
            sql += " AND id < ?"
            params.append(before_id)
        if since is not None:
            sql += " AND created_at >= ?"
            params.append(since)
        sql += " ORDER BY pinned_at IS NOT NULL DESC, pinned_at DESC, id DESC LIMIT ?"
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
        image_url: str | None = None,
    ) -> dict:
        """Insert a new post and return it as a dict."""
        row = {
            "author": author,
            "content": content,
            "reply_to": reply_to,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "feed_id": feed_id,
            "image_url": image_url,
        }
        result = self._db["posts"].insert(row)
        row["id"] = result.last_pk
        return row

    def get_timeline(
        self,
        limit: int = 50,
        before_id: int | None = None,
        since: str | None = None,
        after_id: int | None = None,
    ) -> list[dict]:
        """Return top-level posts (reply_to IS NULL), newest first."""
        sql = "SELECT * FROM posts WHERE reply_to IS NULL"
        params: list = []
        if before_id is not None:
            sql += " AND id < ?"
            params.append(before_id)
        if after_id is not None:
            sql += " AND id > ?"
            params.append(after_id)
        if since is not None:
            sql += " AND created_at >= ?"
            params.append(since)
        if after_id is not None:
            sql += " ORDER BY id ASC LIMIT ?"
        else:
            sql += " ORDER BY pinned_at IS NOT NULL DESC, pinned_at DESC, id DESC LIMIT ?"
        params.append(limit)
        return _rows_to_dicts(self._db.execute(sql, params))

    def pin_post(self, post_id: int) -> dict | None:
        """Pin a root post. Only root posts (reply_to IS NULL) can be pinned. Returns updated post or None."""
        post = self.get_post(post_id)
        if post is None:
            return None
        if post.get("reply_to") is not None:
            return None
        now = datetime.now(timezone.utc).isoformat()
        self._db["posts"].update(post_id, {"pinned_at": now})
        post["pinned_at"] = now
        return post

    def unpin_post(self, post_id: int) -> dict | None:
        """Unpin a post. Returns updated post or None."""
        post = self.get_post(post_id)
        if post is None:
            return None
        self._db.execute("UPDATE posts SET pinned_at = NULL WHERE id = ?", [post_id])
        post["pinned_at"] = None
        return post

    def search_posts(
        self,
        query: str,
        limit: int = 50,
        before_id: int | None = None,
    ) -> list[dict]:
        """Search posts using FTS5 full-text search, ranked by relevance."""
        # Build FTS5 query: quote each term and prefix-match for partial words
        terms = query.strip().split()
        if not terms:
            return []
        fts_query = " ".join(f'"{t}"*' for t in terms)

        sql = (
            "SELECT p.* FROM posts p"
            " JOIN posts_fts ON posts_fts.rowid = p.id"
            " WHERE posts_fts MATCH ? AND p.reply_to IS NULL"
        )
        params: list = [fts_query]
        if before_id is not None:
            sql += " AND p.id < ?"
            params.append(before_id)
        sql += " ORDER BY bm25(posts_fts) LIMIT ?"
        params.append(limit)
        return _rows_to_dicts(self._db.execute(sql, params))

    def get_thread(self, post_id: int) -> list[dict]:
        """Return root post + all replies, chronological."""
        sql = "SELECT * FROM posts WHERE id = ? OR reply_to = ? ORDER BY id ASC"
        return _rows_to_dicts(self._db.execute(sql, [post_id, post_id]))

    def get_threads_with_author(self, author: str, since: str | None = None) -> list[list[dict]]:
        """Return full threads where *author* participated (posted or replied), optionally since a timestamp.

        Returns a list of threads, each thread being a list of posts (root + replies) in chronological order.
        """
        # Find root post IDs of threads where this author has a post
        sql = (
            "SELECT DISTINCT CASE WHEN reply_to IS NULL THEN id ELSE reply_to END AS root_id "
            "FROM posts WHERE author = ?"
        )
        params: list = [author]
        if since:
            sql += " AND created_at >= ?"
            params.append(since)
        sql += " ORDER BY root_id DESC"

        root_ids = [r[0] for r in self._db.execute(sql, params).fetchall()]
        threads = []
        for rid in root_ids:
            thread = self.get_thread(rid)
            if thread:
                threads.append(thread)
        return threads

    def get_post(self, post_id: int) -> dict | None:
        """Return a single post by ID, or None."""
        try:
            return self._db["posts"].get(post_id)
        except Exception:
            return None

    def edit_post(self, post_id: int, content: str, image_url: str | None = None) -> dict | None:
        """Update a post's content and optional image. Returns updated post or None if not found."""
        post = self.get_post(post_id)
        if post is None:
            return None
        updates: dict = {"content": content}
        if image_url is not None:
            updates["image_url"] = image_url or None  # empty string → NULL
        self._db["posts"].update(post_id, updates)
        post["content"] = content
        if image_url is not None:
            post["image_url"] = image_url or None
        return post

    def delete_post(self, post_id: int) -> bool:
        """Delete a post and its replies. Returns True if it existed."""
        post = self.get_post(post_id)
        if post is None:
            return False
        # Delete replies first
        self._db.execute("DELETE FROM posts WHERE reply_to = ?", [post_id])
        self._db.execute("DELETE FROM reactions WHERE post_id = ?", [post_id])
        self._db["posts"].delete(post_id)
        return True

    # ------------------------------------------------------------------
    # Reactions
    # ------------------------------------------------------------------

    EMOJI_SET = ("👍", "🔥", "💡", "👀", "❤️")

    def toggle_reaction(self, post_id: int, emoji: str) -> bool:
        """Toggle a reaction on a post. Returns True if now active, False if removed."""
        if emoji not in self.EMOJI_SET:
            raise ValueError(f"Unsupported emoji: {emoji}")
        existing = self._db.execute(
            "SELECT id FROM reactions WHERE post_id = ? AND emoji = ?",
            [post_id, emoji],
        ).fetchone()
        if existing:
            self._db.execute("DELETE FROM reactions WHERE id = ?", [existing[0]])
            return False
        self._db.execute(
            "INSERT INTO reactions (post_id, emoji, created_at) VALUES (?, ?, ?)",
            [post_id, emoji, datetime.now(timezone.utc).isoformat()],
        )
        return True

    def get_post_reactions(self, post_id: int) -> list[str]:
        """Return list of active emoji for a post."""
        rows = self._db.execute(
            "SELECT emoji FROM reactions WHERE post_id = ?", [post_id]
        ).fetchall()
        return [r[0] for r in rows]

    def get_bulk_reactions(self, post_ids: list[int]) -> dict[int, list[str]]:
        """Return {post_id: [emoji, ...]} for a batch of posts."""
        if not post_ids:
            return {}
        placeholders = ",".join("?" for _ in post_ids)
        rows = self._db.execute(
            f"SELECT post_id, emoji FROM reactions WHERE post_id IN ({placeholders})",
            post_ids,
        ).fetchall()
        result: dict[int, list[str]] = {pid: [] for pid in post_ids}
        for pid, emoji in rows:
            result[pid].append(emoji)
        return result

    def get_reacted_post_ids(self) -> set[int]:
        """Return all post IDs that have at least one reaction."""
        rows = self._db.execute("SELECT DISTINCT post_id FROM reactions").fetchall()
        return {r[0] for r in rows}

    def get_reacted_posts(self, limit: int = 50) -> list[dict]:
        """Return posts with any reaction, newest-reacted first."""
        sql = (
            "SELECT p.*, MAX(r.created_at) AS last_reacted "
            "FROM posts p JOIN reactions r ON r.post_id = p.id "
            "GROUP BY p.id ORDER BY last_reacted DESC LIMIT ?"
        )
        posts = _rows_to_dicts(self._db.execute(sql, [limit]))
        # Strip the extra column
        for p in posts:
            p.pop("last_reacted", None)
        return posts

    # ------------------------------------------------------------------
    # Read state (unread reply tracking)
    # ------------------------------------------------------------------

    def mark_read(self, post_id: int) -> None:
        """Record that the user has read a thread (by root post ID) right now."""
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT OR REPLACE INTO read_state (post_id, last_read_at) VALUES (?, ?)",
            [post_id, now],
        )

    def get_read_state(self) -> dict[int, str]:
        """Return {post_id: last_read_at} for all tracked threads."""
        rows = self._db.execute("SELECT post_id, last_read_at FROM read_state").fetchall()
        return {r[0]: r[1] for r in rows}

    def count_unread_replies(self, root_id: int, last_read_at: str | None) -> int:
        """Count replies to *root_id* after *last_read_at* that weren't posted by 'user'.

        If last_read_at is None (thread never opened), all non-user replies count.
        """
        if last_read_at is None:
            row = self._db.execute(
                "SELECT COUNT(*) FROM posts WHERE reply_to = ? AND author != 'user'",
                [root_id],
            ).fetchone()
        else:
            row = self._db.execute(
                "SELECT COUNT(*) FROM posts WHERE reply_to = ? AND author != 'user' AND created_at > ?",
                [root_id, last_read_at],
            ).fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    def upsert_agent(self, name: str, display_name: str, tagline: str = "") -> None:
        """Insert or replace an agent's display metadata."""
        self._db.execute(
            "INSERT OR REPLACE INTO agents (name, display_name, tagline) VALUES (?, ?, ?)",
            [name, display_name, tagline],
        )

    def upsert_agents(self, agents: list[dict]) -> None:
        """Bulk upsert agent display metadata."""
        for a in agents:
            self.upsert_agent(a["name"], a["display_name"], a.get("tagline", ""))

    def list_agents(self) -> list[dict]:
        """Return all registered agents."""
        return _rows_to_dicts(self._db.execute("SELECT * FROM agents ORDER BY name"))
