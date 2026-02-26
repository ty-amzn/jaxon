"""SQLite persistence for scheduled jobs."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sqlite_utils

logger = logging.getLogger(__name__)


class JobStore:
    """Persists scheduled job metadata to SQLite."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._ensure_table()

    def _ensure_table(self) -> None:
        if "jobs" not in self._db.table_names():
            self._db["jobs"].create({
                "id": str,
                "description": str,
                "trigger_type": str,  # "date", "cron", "interval"
                "trigger_args": str,  # JSON
                "job_type": str,      # "notification" or "assistant"
                "job_args": str,      # JSON
            }, pk="id")

    def save(self, job_id: str, description: str, trigger_type: str,
             trigger_args: dict, job_type: str, job_args: dict) -> None:
        self._db["jobs"].upsert({
            "id": job_id,
            "description": description,
            "trigger_type": trigger_type,
            "trigger_args": json.dumps(trigger_args),
            "job_type": job_type,
            "job_args": json.dumps(job_args),
        }, pk="id")

    def load_all(self) -> list[dict[str, Any]]:
        rows = []
        for row in self._db["jobs"].rows:
            row["trigger_args"] = json.loads(row["trigger_args"])
            row["job_args"] = json.loads(row["job_args"])
            rows.append(row)
        return rows

    def delete(self, job_id: str) -> bool:
        try:
            self._db["jobs"].delete(job_id)
            return True
        except Exception:
            return False

    def prune_expired(self) -> int:
        """Delete one-time (date trigger) jobs whose run_date is in the past."""
        now = datetime.now(timezone.utc)
        expired_ids: list[str] = []
        for row in self._db["jobs"].rows_where("trigger_type = ?", ["date"]):
            try:
                args = json.loads(row["trigger_args"])
                run_date = datetime.fromisoformat(args["run_date"])
                if run_date.tzinfo is None:
                    run_date = run_date.replace(tzinfo=timezone.utc)
                if run_date < now:
                    expired_ids.append(row["id"])
            except (KeyError, ValueError, TypeError):
                continue
        for job_id in expired_ids:
            self._db["jobs"].delete(job_id)
        return len(expired_ids)

    def get(self, job_id: str) -> dict[str, Any] | None:
        try:
            row = self._db["jobs"].get(job_id)
            row["trigger_args"] = json.loads(row["trigger_args"])
            row["job_args"] = json.loads(row["job_args"])
            return row
        except Exception:
            return None
