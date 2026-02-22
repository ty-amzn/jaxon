"""Shared test fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from assistant.core.config import Settings


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory structure."""
    (tmp_path / "memory" / "daily").mkdir(parents=True)
    (tmp_path / "logs").mkdir()
    (tmp_path / "db").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "threads").mkdir()

    identity = tmp_path / "memory" / "IDENTITY.md"
    identity.write_text("# Test Identity\nYou are a test assistant.")

    memory = tmp_path / "memory" / "MEMORY.md"
    memory.write_text("# Durable Memory\n\n## User Preferences\n- (none yet)\n")

    return tmp_path


@pytest.fixture
def settings(tmp_data_dir: Path) -> Settings:
    """Create Settings pointing at temp directories."""
    return Settings(
        anthropic_api_key="sk-ant-test-key",
        data_dir=tmp_data_dir,
        log_level="DEBUG",
    )
