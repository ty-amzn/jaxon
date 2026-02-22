"""Scheduler manager wrapping APScheduler with persistence."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from assistant.scheduler.store import JobStore

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface
    from assistant.core.notifications import NotificationDispatcher

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages scheduled jobs with APScheduler and SQLite persistence."""

    def __init__(
        self,
        job_store: JobStore,
        dispatcher: NotificationDispatcher,
        chat_interface: ChatInterface | None = None,
        timezone: str = "UTC",
    ) -> None:
        self._store = job_store
        self._dispatcher = dispatcher
        self._chat_interface = chat_interface
        self._scheduler = AsyncIOScheduler(timezone=timezone)

    async def start(self) -> None:
        """Start the scheduler and load persisted jobs."""
        self._load_persisted_jobs()
        self._scheduler.start()
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    def _load_persisted_jobs(self) -> None:
        """Re-register persisted jobs with APScheduler."""
        jobs = self._store.load_all()
        for job_data in jobs:
            try:
                self._register_job_from_data(job_data)
                logger.info("Loaded persisted job: %s", job_data["id"])
            except Exception:
                logger.exception("Failed to load job %s", job_data["id"])

    def _register_job_from_data(self, job_data: dict) -> None:
        """Register a job with APScheduler from stored data."""
        trigger = self._build_trigger(job_data["trigger_type"], job_data["trigger_args"])
        if trigger is None:
            return

        from assistant.scheduler.jobs import run_notification_job, run_assistant_job

        if job_data["job_type"] == "notification":
            self._scheduler.add_job(
                run_notification_job,
                trigger=trigger,
                id=job_data["id"],
                replace_existing=True,
                kwargs={
                    "dispatcher": self._dispatcher,
                    "message": job_data["job_args"].get("message", ""),
                },
            )
        elif job_data["job_type"] == "assistant" and self._chat_interface:
            self._scheduler.add_job(
                run_assistant_job,
                trigger=trigger,
                id=job_data["id"],
                replace_existing=True,
                kwargs={
                    "chat_interface": self._chat_interface,
                    "session_id": job_data["job_args"].get("session_id", "scheduler"),
                    "prompt": job_data["job_args"].get("prompt", ""),
                    "dispatcher": self._dispatcher,
                },
            )

    def _build_trigger(self, trigger_type: str, trigger_args: dict) -> Any:
        if trigger_type == "date":
            run_date = trigger_args.get("run_date")
            if isinstance(run_date, str):
                run_date = datetime.fromisoformat(run_date)
            return DateTrigger(run_date=run_date)
        elif trigger_type == "cron":
            return CronTrigger(**trigger_args)
        elif trigger_type == "interval":
            return IntervalTrigger(**trigger_args)
        else:
            logger.error("Unknown trigger type: %s", trigger_type)
            return None

    def add_reminder(
        self,
        description: str,
        trigger_type: str,
        trigger_args: dict,
        message: str | None = None,
    ) -> str:
        """Add a notification reminder. Returns job ID."""
        job_id = f"reminder_{uuid.uuid4().hex[:8]}"

        self._store.save(
            job_id=job_id,
            description=description,
            trigger_type=trigger_type,
            trigger_args=trigger_args,
            job_type="notification",
            job_args={"message": message or description},
        )

        self._register_job_from_data({
            "id": job_id,
            "description": description,
            "trigger_type": trigger_type,
            "trigger_args": trigger_args,
            "job_type": "notification",
            "job_args": {"message": message or description},
        })

        logger.info("Added reminder %s: %s", job_id, description)
        return job_id

    def add_assistant_job(
        self,
        description: str,
        trigger_type: str,
        trigger_args: dict,
        prompt: str,
        session_id: str = "scheduler",
    ) -> str:
        """Add a job that runs a prompt through the assistant. Returns job ID."""
        job_id = f"assistant_{uuid.uuid4().hex[:8]}"

        job_args = {"prompt": prompt, "session_id": session_id}
        self._store.save(
            job_id=job_id,
            description=description,
            trigger_type=trigger_type,
            trigger_args=trigger_args,
            job_type="assistant",
            job_args=job_args,
        )

        self._register_job_from_data({
            "id": job_id,
            "description": description,
            "trigger_type": trigger_type,
            "trigger_args": trigger_args,
            "job_type": "assistant",
            "job_args": job_args,
        })

        logger.info("Added assistant job %s: %s", job_id, description)
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass  # Job may not be in scheduler (already fired)
        return self._store.delete(job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all persisted jobs."""
        jobs = self._store.load_all()
        result = []
        for j in jobs:
            result.append({
                "id": j["id"],
                "description": j["description"],
                "trigger": f"{j['trigger_type']}({j['trigger_args']})",
                "type": j["job_type"],
            })
        return result
