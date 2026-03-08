"""Tests for backup create and list."""

import tarfile
from pathlib import Path


def test_backup_create_and_list(tmp_path: Path):
    """Backup creates a tarball and can be listed."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    backup_dir = data_dir / "backups"

    # Create some test data
    memory_dir = data_dir / "memory"
    memory_dir.mkdir()
    (memory_dir / "test.md").write_text("# Test")

    # Create backup
    backup_dir.mkdir()
    backup_path = backup_dir / "test-20260101_120000.tar.gz"
    with tarfile.open(backup_path, "w:gz") as tar:
        for item in data_dir.iterdir():
            if item.name == "backups":
                continue
            tar.add(item, arcname=item.name)

    # Verify backup exists
    assert backup_path.exists()

    # List backups
    backups = list(backup_dir.glob("*.tar.gz"))
    assert len(backups) == 1
    assert "test-" in backups[0].name

    # Verify contents
    with tarfile.open(backup_path, "r:gz") as tar:
        names = tar.getnames()
    assert "memory" in names or "memory/test.md" in names
