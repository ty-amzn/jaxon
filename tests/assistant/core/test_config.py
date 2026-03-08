"""Tests for configuration."""

from pathlib import Path

from assistant.core.config import Settings


def test_settings_defaults():
    s = Settings(anthropic_api_key="test", _env_file=None)
    assert s.model == "claude-sonnet-4-20250514"
    assert s.max_tokens == 8192
    assert s.host == "127.0.0.1"
    assert s.port == 51430


def test_settings_paths():
    s = Settings(anthropic_api_key="test", _env_file=None)
    assert s.memory_dir == s.data_dir / "memory"
    assert s.daily_log_dir == s.data_dir / "memory" / "daily"
    assert s.identity_path == s.data_dir / "memory" / "IDENTITY.md"
    assert s.memory_path == s.data_dir / "memory" / "MEMORY.md"
    assert s.audit_log_path == s.data_dir / "logs" / "audit.jsonl"
    assert s.search_db_path == s.data_dir / "db" / "search.db"


def test_settings_phase2_paths():
    """Test Phase 2 configuration paths."""
    s = Settings(anthropic_api_key="test", _env_file=None)
    assert s.skills_dir == s.data_dir / "skills"
    assert s.threads_dir == s.data_dir / "threads"


def test_settings_phase2_defaults():
    """Test Phase 2 default settings."""
    s = Settings(anthropic_api_key="test", _env_file=None)
    # Ollama
    assert s.ollama_enabled is False
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.ollama_model == "llama3.2"
    # Routing
    assert s.local_model_threshold_tokens == 1000
    # Web Search
    assert s.web_search_enabled is False
    assert s.searxng_url == "http://localhost:8888"
    # Embedding model
    assert s.embedding_model == "nomic-embed-text"
    # Media
    assert s.max_media_size_mb == 10


def test_ollama_config():
    """Test Ollama configuration defaults."""
    s = Settings(anthropic_api_key="test", _env_file=None)

    assert s.ollama_enabled is False
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.ollama_model == "llama3.2"


def test_routing_config():
    """Test routing configuration defaults."""
    s = Settings(anthropic_api_key="test", _env_file=None)

    assert s.local_model_threshold_tokens == 1000


def test_web_search_config():
    """Test web search configuration defaults."""
    s = Settings(anthropic_api_key="test", _env_file=None)

    assert s.web_search_enabled is False
    assert s.searxng_url == "http://localhost:8888"


def test_embedding_config():
    """Test embedding configuration defaults."""
    s = Settings(anthropic_api_key="test", _env_file=None)

    assert s.embedding_model == "nomic-embed-text"


def test_media_config():
    """Test media configuration defaults."""
    s = Settings(anthropic_api_key="test", _env_file=None)

    assert s.max_media_size_mb == 10


def test_phase3_config_defaults(tmp_path: Path):
    """Phase 3 config fields have correct defaults."""
    settings = Settings(
        anthropic_api_key="test",
        data_dir=tmp_path,
        _env_file=None,
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


def test_phase4_config_defaults(tmp_path: Path):
    """Phase 4 config fields have correct defaults."""
    settings = Settings(anthropic_api_key="test", data_dir=tmp_path, _env_file=None)

    assert settings.webhook_enabled is False
    assert settings.webhook_secret == ""
    assert settings.dnd_enabled is False
    assert settings.dnd_start == "23:00"
    assert settings.dnd_end == "07:00"
    assert settings.dnd_allow_urgent is True
    assert settings.workflow_dir == tmp_path / "workflows"
    assert settings.backup_dir == tmp_path / "backups"
