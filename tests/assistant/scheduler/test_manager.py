"""Tests for the scheduler manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from assistant.core.notifications import NotificationDispatcher
from assistant.scheduler.store import JobStore


@pytest.mark.asyncio
async def test_scheduler_add_list_remove(tmp_path: Path):
    """SchedulerManager can add, list, and remove jobs."""
    from assistant.scheduler.manager import SchedulerManager

    store = JobStore(tmp_path / "scheduler.db")
    dispatcher = NotificationDispatcher()
    manager = SchedulerManager(
        job_store=store,
        dispatcher=dispatcher,
        timezone="UTC",
    )
    await manager.start()

    try:
        job_id = manager.add_reminder(
            description="Test reminder",
            trigger_type="cron",
            trigger_args={"hour": 9, "minute": 0},
            message="Good morning!",
        )
        assert job_id.startswith("reminder_")

        jobs = manager.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["id"] == job_id
        assert jobs[0]["description"] == "Test reminder"

        assert manager.remove_job(job_id)
        assert len(manager.list_jobs()) == 0
    finally:
        await manager.stop()
