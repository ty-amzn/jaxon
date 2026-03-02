"""SQLite store for LLM inference events and tool call events."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sqlite_utils


def _rows_to_dicts(cursor) -> list[dict]:
    """Convert raw cursor rows to list of dicts."""
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


class ObservatoryStore:
    """Persistent store for LLM inference metrics."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._ensure_table()

    _NEW_COLUMNS = {
        "input_tokens": int,
        "output_tokens": int,
        "stop_reason": str,
        "raw_prompt": str,
        "raw_response": str,
    }

    def _ensure_table(self) -> None:
        self._ensure_tool_events_table()
        if "inference_events" not in self._db.table_names():
            self._db["inference_events"].create(
                {
                    "id": int,
                    "timestamp": str,
                    "provider": str,
                    "model": str,
                    "duration_ms": int,
                    "success": int,
                    "error_message": str,
                    "session_id": str,
                    "agent_name": str,
                    "tool_rounds": int,
                    "has_tools": int,
                    "routed_from": str,
                    "input_tokens": int,
                    "output_tokens": int,
                    "stop_reason": str,
                    "raw_prompt": str,
                    "raw_response": str,
                },
                pk="id",
                not_null={"timestamp", "provider", "model", "duration_ms", "success"},
            )
            # Indexes for common queries
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON inference_events(timestamp DESC)"
            )
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_provider ON inference_events(provider)"
            )
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_model ON inference_events(model)"
            )
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_session ON inference_events(session_id)"
            )
        else:
            # Auto-migrate: add missing columns to existing DBs
            existing = {col.name for col in self._db["inference_events"].columns}
            for col_name, col_type in self._NEW_COLUMNS.items():
                if col_name not in existing:
                    self._db.execute(
                        f"ALTER TABLE inference_events ADD COLUMN {col_name} {'INTEGER' if col_type is int else 'TEXT'}"
                    )

    def _ensure_tool_events_table(self) -> None:
        if "tool_events" not in self._db.table_names():
            self._db["tool_events"].create(
                {
                    "id": int,
                    "timestamp": str,
                    "tool_name": str,
                    "duration_ms": int,
                    "success": int,
                    "error_message": str,
                    "session_id": str,
                    "agent_name": str,
                    "action_category": str,
                },
                pk="id",
                not_null={"timestamp", "tool_name", "duration_ms", "success"},
            )
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_tool_events_timestamp ON tool_events(timestamp DESC)"
            )
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_tool_events_tool_name ON tool_events(tool_name)"
            )

    # ------------------------------------------------------------------
    # Inference Events
    # ------------------------------------------------------------------

    def log_event(self, event: dict[str, Any]) -> dict:
        """Insert an inference event and return it with ID."""
        row = {
            "timestamp": event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "provider": event["provider"],
            "model": event["model"],
            "duration_ms": event["duration_ms"],
            "success": 1 if event.get("success", True) else 0,
            "error_message": event.get("error_message"),
            "session_id": event.get("session_id"),
            "agent_name": event.get("agent_name"),
            "tool_rounds": event.get("tool_rounds", 0),
            "has_tools": 1 if event.get("has_tools", False) else 0,
            "routed_from": event.get("routed_from"),
            "input_tokens": event.get("input_tokens", 0),
            "output_tokens": event.get("output_tokens", 0),
            "stop_reason": event.get("stop_reason", ""),
            "raw_prompt": event.get("raw_prompt"),
            "raw_response": event.get("raw_response"),
        }
        result = self._db["inference_events"].insert(row)
        row["id"] = result.last_pk
        return row

    def get_events(
        self,
        limit: int = 100,
        before_id: int | None = None,
        provider: str | None = None,
        model: str | None = None,
        session_id: str | None = None,
        success: bool | None = None,
        agent_name: str | None = None,
    ) -> list[dict]:
        """Return events matching filters, newest first."""
        sql = "SELECT * FROM inference_events WHERE 1=1"
        params: list = []

        if before_id is not None:
            sql += " AND id < ?"
            params.append(before_id)
        if provider:
            sql += " AND provider = ?"
            params.append(provider)
        if model:
            sql += " AND model = ?"
            params.append(model)
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if success is not None:
            sql += " AND success = ?"
            params.append(1 if success else 0)
        if agent_name:
            sql += " AND agent_name = ?"
            params.append(agent_name)

        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return _rows_to_dicts(self._db.execute(sql, params))

    def get_event(self, event_id: int) -> dict | None:
        """Return a single event by ID."""
        try:
            return self._db["inference_events"].get(event_id)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self, period_hours: int = 24) -> dict:
        """Return aggregate statistics for the given period."""
        from datetime import timedelta

        cutoff_str = (datetime.now(timezone.utc) - timedelta(hours=period_hours)).isoformat()

        # Total calls
        total_row = self._db.execute(
            "SELECT COUNT(*) FROM inference_events WHERE timestamp >= ?",
            [cutoff_str],
        ).fetchone()
        total_calls = total_row[0] if total_row else 0

        # Error rate
        error_row = self._db.execute(
            "SELECT COUNT(*) FROM inference_events WHERE timestamp >= ? AND success = 0",
            [cutoff_str],
        ).fetchone()
        error_count = error_row[0] if error_row else 0
        error_rate = (error_count / total_calls * 100) if total_calls > 0 else 0

        # Average latency
        avg_row = self._db.execute(
            "SELECT AVG(duration_ms) FROM inference_events WHERE timestamp >= ?",
            [cutoff_str],
        ).fetchone()
        avg_latency_ms = round(avg_row[0]) if avg_row and avg_row[0] else 0

        # Calls by provider
        provider_rows = self._db.execute(
            "SELECT provider, COUNT(*) as count FROM inference_events WHERE timestamp >= ? GROUP BY provider",
            [cutoff_str],
        ).fetchall()
        calls_by_provider = {row[0]: row[1] for row in provider_rows}

        # Calls by model
        model_rows = self._db.execute(
            "SELECT model, COUNT(*) as count FROM inference_events WHERE timestamp >= ? GROUP BY model",
            [cutoff_str],
        ).fetchall()
        calls_by_model = {row[0]: row[1] for row in model_rows}

        # Calls per hour (timeline)
        hourly_rows = self._db.execute(
            "SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour, COUNT(*) as count "
            "FROM inference_events WHERE timestamp >= ? GROUP BY hour ORDER BY hour",
            [cutoff_str],
        ).fetchall()
        calls_per_hour = [{"hour": row[0], "count": row[1]} for row in hourly_rows]

        # Total tokens
        token_row = self._db.execute(
            "SELECT COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0) "
            "FROM inference_events WHERE timestamp >= ?",
            [cutoff_str],
        ).fetchone()
        total_input_tokens = token_row[0] if token_row else 0
        total_output_tokens = token_row[1] if token_row else 0

        # Tokens by model
        tokens_by_model_rows = self._db.execute(
            "SELECT model, COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0) "
            "FROM inference_events WHERE timestamp >= ? GROUP BY model",
            [cutoff_str],
        ).fetchall()
        tokens_by_model = {
            row[0]: {"input": row[1], "output": row[2]}
            for row in tokens_by_model_rows
        }

        # Calls by agent
        agent_rows = self._db.execute(
            "SELECT COALESCE(agent_name, 'jax') as agent, COUNT(*) as count "
            "FROM inference_events WHERE timestamp >= ? GROUP BY agent",
            [cutoff_str],
        ).fetchall()
        calls_by_agent = {row[0]: row[1] for row in agent_rows}

        return {
            "period_hours": period_hours,
            "total_calls": total_calls,
            "error_count": error_count,
            "error_rate": round(error_rate, 2),
            "avg_latency_ms": avg_latency_ms,
            "calls_by_provider": calls_by_provider,
            "calls_by_model": calls_by_model,
            "calls_by_agent": calls_by_agent,
            "calls_per_hour": calls_per_hour,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "tokens_by_model": tokens_by_model,
        }

    def cleanup(self, raw_retention_days: int = 30, event_retention_days: int = 180) -> tuple[int, int]:
        """Clean up old data. Returns (raw_cleaned, events_deleted)."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)

        # NULL out raw prompt/response after 30 days
        raw_cutoff = (now - timedelta(days=raw_retention_days)).isoformat()
        raw_cursor = self._db.execute(
            "UPDATE inference_events SET raw_prompt = NULL, raw_response = NULL "
            "WHERE timestamp < ? AND (raw_prompt IS NOT NULL OR raw_response IS NOT NULL)",
            [raw_cutoff],
        )
        raw_cleaned = raw_cursor.rowcount

        # Delete events older than 6 months
        event_cutoff = (now - timedelta(days=event_retention_days)).isoformat()
        event_cursor = self._db.execute(
            "DELETE FROM inference_events WHERE timestamp < ?",
            [event_cutoff],
        )
        events_deleted = event_cursor.rowcount

        # Delete old tool events (same retention as inference events)
        tool_cursor = self._db.execute(
            "DELETE FROM tool_events WHERE timestamp < ?",
            [event_cutoff],
        )
        tool_events_deleted = tool_cursor.rowcount

        return raw_cleaned, events_deleted + tool_events_deleted

    # ------------------------------------------------------------------
    # Tool Events
    # ------------------------------------------------------------------

    def log_tool_event(self, event: dict[str, Any]) -> dict:
        """Insert a tool call event and return it with ID."""
        row = {
            "timestamp": event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "tool_name": event["tool_name"],
            "duration_ms": event["duration_ms"],
            "success": 1 if event.get("success", True) else 0,
            "error_message": event.get("error_message"),
            "session_id": event.get("session_id"),
            "agent_name": event.get("agent_name"),
            "action_category": event.get("action_category"),
        }
        result = self._db["tool_events"].insert(row)
        row["id"] = result.last_pk
        return row

    def get_tool_events(
        self,
        limit: int = 100,
        before_id: int | None = None,
        tool_name: str | None = None,
        agent_name: str | None = None,
        success: bool | None = None,
    ) -> list[dict]:
        """Return tool events matching filters, newest first."""
        sql = "SELECT * FROM tool_events WHERE 1=1"
        params: list = []

        if before_id is not None:
            sql += " AND id < ?"
            params.append(before_id)
        if tool_name:
            sql += " AND tool_name = ?"
            params.append(tool_name)
        if agent_name:
            sql += " AND agent_name = ?"
            params.append(agent_name)
        if success is not None:
            sql += " AND success = ?"
            params.append(1 if success else 0)

        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return _rows_to_dicts(self._db.execute(sql, params))

    def get_tool_stats(self, period_hours: int = 24) -> dict:
        """Return aggregate tool call statistics for the given period."""
        from datetime import timedelta

        cutoff_str = (datetime.now(timezone.utc) - timedelta(hours=period_hours)).isoformat()

        # Total calls
        total_row = self._db.execute(
            "SELECT COUNT(*) FROM tool_events WHERE timestamp >= ?",
            [cutoff_str],
        ).fetchone()
        total_calls = total_row[0] if total_row else 0

        # Error rate
        error_row = self._db.execute(
            "SELECT COUNT(*) FROM tool_events WHERE timestamp >= ? AND success = 0",
            [cutoff_str],
        ).fetchone()
        error_count = error_row[0] if error_row else 0
        error_rate = (error_count / total_calls * 100) if total_calls > 0 else 0

        # Average duration
        avg_row = self._db.execute(
            "SELECT AVG(duration_ms) FROM tool_events WHERE timestamp >= ?",
            [cutoff_str],
        ).fetchone()
        avg_duration_ms = round(avg_row[0]) if avg_row and avg_row[0] else 0

        # Calls by tool
        tool_rows = self._db.execute(
            "SELECT tool_name, COUNT(*) as count FROM tool_events WHERE timestamp >= ? GROUP BY tool_name ORDER BY count DESC",
            [cutoff_str],
        ).fetchall()
        calls_by_tool = {row[0]: row[1] for row in tool_rows}

        # Average duration by tool
        avg_by_tool_rows = self._db.execute(
            "SELECT tool_name, AVG(duration_ms) FROM tool_events WHERE timestamp >= ? GROUP BY tool_name",
            [cutoff_str],
        ).fetchall()
        avg_duration_by_tool = {row[0]: round(row[1]) for row in avg_by_tool_rows}

        # Calls per hour
        hourly_rows = self._db.execute(
            "SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour, COUNT(*) as count "
            "FROM tool_events WHERE timestamp >= ? GROUP BY hour ORDER BY hour",
            [cutoff_str],
        ).fetchall()
        calls_per_hour = [{"hour": row[0], "count": row[1]} for row in hourly_rows]

        return {
            "period_hours": period_hours,
            "total_calls": total_calls,
            "error_count": error_count,
            "error_rate": round(error_rate, 2),
            "avg_duration_ms": avg_duration_ms,
            "calls_by_tool": calls_by_tool,
            "avg_duration_by_tool": avg_duration_by_tool,
            "calls_per_hour": calls_per_hour,
        }