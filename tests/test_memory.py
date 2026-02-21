"""Tests for the memory system."""

from pathlib import Path

import pytest

from assistant.memory.daily_log import DailyLog
from assistant.memory.durable import DurableMemory
from assistant.memory.identity import IdentityLoader
from assistant.memory.manager import MemoryManager
from assistant.memory.search import SearchIndex


def test_identity_loader(tmp_data_dir: Path):
    loader = IdentityLoader(tmp_data_dir / "memory" / "IDENTITY.md")
    content = loader.load()
    assert "Test Identity" in content


def test_identity_loader_missing():
    loader = IdentityLoader(Path("/nonexistent/IDENTITY.md"))
    assert loader.load() == ""


def test_durable_memory_read(tmp_data_dir: Path):
    dm = DurableMemory(tmp_data_dir / "memory" / "MEMORY.md")
    content = dm.read()
    assert "Durable Memory" in content


@pytest.mark.asyncio
async def test_durable_memory_append(tmp_data_dir: Path):
    dm = DurableMemory(tmp_data_dir / "memory" / "MEMORY.md")
    await dm.append("User Preferences", "Prefers dark mode")
    content = dm.read()
    assert "Prefers dark mode" in content
    assert "(none yet)" not in content


@pytest.mark.asyncio
async def test_daily_log(tmp_data_dir: Path):
    log = DailyLog(tmp_data_dir / "memory" / "daily")
    await log.append_exchange("Hello", "Hi there!", [{"name": "test", "input": {}, "output": "ok"}])
    today = log.read_today()
    assert "Hello" in today
    assert "Hi there!" in today
    assert "test" in today


def test_search_index(tmp_data_dir: Path):
    idx = SearchIndex(tmp_data_dir / "db" / "search.db")
    idx.index_message("user", "How do I configure SSH?", "sess1")
    idx.index_message("assistant", "You can configure SSH by editing ~/.ssh/config", "sess1")
    results = idx.search("SSH")
    assert len(results) >= 1


def test_memory_manager_system_prompt(tmp_data_dir: Path):
    mm = MemoryManager(
        identity_path=tmp_data_dir / "memory" / "IDENTITY.md",
        memory_path=tmp_data_dir / "memory" / "MEMORY.md",
        daily_log_dir=tmp_data_dir / "memory" / "daily",
        search_db_path=tmp_data_dir / "db" / "search.db",
    )
    prompt = mm.get_system_prompt()
    assert "Test Identity" in prompt
    assert "Durable Memory" in prompt
