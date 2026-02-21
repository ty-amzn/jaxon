"""Application configuration via environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "ASSISTANT_", "env_file": ".env", "extra": "ignore"}

    # API keys — no prefix, so they match provider conventions
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    # Model
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192

    # Paths
    data_dir: Path = Path("./data")

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Logging
    log_level: str = "INFO"

    # Session
    max_context_messages: int = 50

    # Permissions
    auto_approve_reads: bool = True

    @property
    def memory_dir(self) -> Path:
        return self.data_dir / "memory"

    @property
    def daily_log_dir(self) -> Path:
        return self.memory_dir / "daily"

    @property
    def identity_path(self) -> Path:
        return self.memory_dir / "IDENTITY.md"

    @property
    def memory_path(self) -> Path:
        return self.memory_dir / "MEMORY.md"

    @property
    def audit_log_path(self) -> Path:
        return self.data_dir / "logs" / "audit.jsonl"

    @property
    def app_log_path(self) -> Path:
        return self.data_dir / "logs" / "app.log"

    @property
    def search_db_path(self) -> Path:
        return self.data_dir / "db" / "search.db"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
