"""Tests for configuration."""

from pathlib import Path

from assistant.core.config import Settings


def test_settings_defaults():
    s = Settings(anthropic_api_key="test")
    assert s.model == "claude-sonnet-4-20250514"
    assert s.max_tokens == 8192
    assert s.host == "127.0.0.1"
    assert s.port == 8000


def test_settings_paths(settings: Settings):
    assert settings.memory_dir == settings.data_dir / "memory"
    assert settings.daily_log_dir == settings.data_dir / "memory" / "daily"
    assert settings.identity_path == settings.data_dir / "memory" / "IDENTITY.md"
    assert settings.memory_path == settings.data_dir / "memory" / "MEMORY.md"
    assert settings.audit_log_path == settings.data_dir / "logs" / "audit.jsonl"
    assert settings.search_db_path == settings.data_dir / "db" / "search.db"
