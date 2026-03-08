"""Tests for the file monitor."""

from pathlib import Path

from assistant.core.notifications import NotificationDispatcher


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
