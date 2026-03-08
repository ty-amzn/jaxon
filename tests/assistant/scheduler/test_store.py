"""Tests for the scheduler job store."""

from pathlib import Path

from assistant.scheduler.store import JobStore


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
