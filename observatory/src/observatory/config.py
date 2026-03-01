"""Observatory configuration via environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "OBSERVATORY_", "env_file": ".env", "extra": "ignore"}

    host: str = "127.0.0.1"
    port: int = 51432
    db_path: Path = Path("./data/observatory.db")