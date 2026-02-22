"""Tests for Phase 3: Telegram, Scheduler, Watchdog."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from assistant.core.config import Settings
from assistant.core.notifications import NotificationDispatcher
from assistant.gateway.permissions import ActionCategory, PermissionManager
from assistant.gateway.session import SessionManager
from assistant.scheduler.store import JobStore


# --- NotificationDispatcher ---


@pytest.mark.asyncio
async def test_dispatcher_multiple_sinks():
    """Dispatcher sends to all registered sinks."""
    dispatcher = NotificationDispatcher()
    received: list[str] = []

    async def sink1(msg: str) -> None:
        received.append(f"sink1:{msg}")

    async def sink2(msg: str) -> None:
        received.append(f"sink2:{msg}")

    dispatcher.register(sink1)
    dispatcher.register(sink2)
    await dispatcher.send("hello")

    assert received == ["sink1:hello", "sink2:hello"]


@pytest.mark.asyncio
async def test_dispatcher_failing_sink_isolation():
    """A failing sink does not prevent other sinks from receiving."""
    dispatcher = NotificationDispatcher()
    received: list[str] = []

    async def bad_sink(msg: str) -> None:
        raise RuntimeError("boom")

    async def good_sink(msg: str) -> None:
        received.append(msg)

    dispatcher.register(bad_sink)
    dispatcher.register(good_sink)
    await dispatcher.send("test")

    assert received == ["test"]


@pytest.mark.asyncio
async def test_dispatcher_unregister():
    """Unregistering a sink removes it."""
    dispatcher = NotificationDispatcher()
    received: list[str] = []

    async def sink(msg: str) -> None:
        received.append(msg)

    dispatcher.register(sink)
    await dispatcher.send("a")
    dispatcher.unregister(sink)
    await dispatcher.send("b")

    assert received == ["a"]


# --- JobStore ---


def test_jobstore_save_load_roundtrip(tmp_path: Path):
    """Jobs can be saved and loaded."""
    store = JobStore(tmp_path / "scheduler.db")

    store.save(
        job_id="test_1",
        description="Test reminder",
        trigger_type="date",
        trigger_args={"run_date": "2025-12-01T09:00:00"},
        job_type="notification",
        job_args={"message": "Hello!"},
    )

    jobs = store.load_all()
    assert len(jobs) == 1
    assert jobs[0]["id"] == "test_1"
    assert jobs[0]["description"] == "Test reminder"
    assert jobs[0]["trigger_type"] == "date"
    assert jobs[0]["trigger_args"] == {"run_date": "2025-12-01T09:00:00"}
    assert jobs[0]["job_args"] == {"message": "Hello!"}


def test_jobstore_delete(tmp_path: Path):
    """Jobs can be deleted."""
    store = JobStore(tmp_path / "scheduler.db")

    store.save("j1", "desc1", "date", {"run_date": "2025-01-01"}, "notification", {"message": "hi"})
    store.save("j2", "desc2", "cron", {"hour": 9}, "notification", {"message": "bye"})

    assert store.delete("j1")
    jobs = store.load_all()
    assert len(jobs) == 1
    assert jobs[0]["id"] == "j2"


def test_jobstore_get(tmp_path: Path):
    """Individual job can be fetched."""
    store = JobStore(tmp_path / "scheduler.db")
    store.save("j1", "desc1", "date", {"run_date": "2025-01-01"}, "notification", {"message": "hi"})

    job = store.get("j1")
    assert job is not None
    assert job["description"] == "desc1"

    assert store.get("nonexistent") is None


# --- SessionManager.get_or_create_keyed_session ---


def test_keyed_session_creates_and_reuses():
    """get_or_create_keyed_session creates a session and reuses it by key."""
    manager = SessionManager()

    session1 = manager.get_or_create_keyed_session("telegram_123")
    session2 = manager.get_or_create_keyed_session("telegram_123")
    session3 = manager.get_or_create_keyed_session("telegram_456")

    assert session1.id == session2.id
    assert session1.id != session3.id


def test_keyed_session_does_not_change_active():
    """Keyed sessions should not change the active session."""
    manager = SessionManager()
    active = manager.active_session  # Creates and sets active
    active_id = active.id

    _ = manager.get_or_create_keyed_session("external_key")
    assert manager.active_session.id == active_id


# --- FileMonitor ---


def test_file_monitor_add_remove_paths(tmp_path: Path):
    """FileMonitor can add and remove paths."""
    from assistant.watchdog_monitor.monitor import FileMonitor

    dispatcher = NotificationDispatcher()
    monitor = FileMonitor(dispatcher=dispatcher)

    watch_dir = tmp_path / "watched"
    watch_dir.mkdir()

    try:
        assert monitor.add_path(str(watch_dir))
        assert str(watch_dir) in monitor.watched_paths

        # Adding same path again returns False
        assert not monitor.add_path(str(watch_dir))

        assert monitor.remove_path(str(watch_dir))
        assert str(watch_dir) not in monitor.watched_paths

        # Removing non-watched path returns False
        assert not monitor.remove_path(str(watch_dir))
    finally:
        monitor.stop()


# --- SchedulerManager ---


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


# --- Permission classification ---


def test_schedule_reminder_classified_as_write():
    """schedule_reminder tool should be classified as WRITE."""
    async def noop_approval(req):
        return True

    pm = PermissionManager(noop_approval)
    request = pm.classify_tool_call(
        "schedule_reminder",
        {"description": "test", "trigger_type": "date", "trigger_args": {}, "message": "hi"},
    )
    assert request.action_category == ActionCategory.WRITE
    assert request.requires_approval


# --- Config ---


def test_phase3_config_defaults(tmp_path: Path):
    """Phase 3 config fields have correct defaults."""
    settings = Settings(
        anthropic_api_key="test",
        data_dir=tmp_path,
    )

    assert settings.telegram_enabled is False
    assert settings.telegram_bot_token == ""
    assert settings.telegram_allowed_user_ids == []
    assert settings.scheduler_enabled is False
    assert settings.scheduler_timezone == "UTC"
    assert settings.watchdog_enabled is False
    assert settings.watchdog_paths == []
    assert settings.watchdog_debounce_seconds == 2.0
    assert settings.watchdog_analyze is False
    assert settings.scheduler_db_path == tmp_path / "db" / "scheduler.db"
