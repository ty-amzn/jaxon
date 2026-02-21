"""App startup/shutdown lifecycle events."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from assistant.core.config import get_settings
from assistant.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    setup_logging(settings.log_level, settings.app_log_path)
    logger.info("Assistant API starting up")

    # Ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.daily_log_dir.mkdir(parents=True, exist_ok=True)
    settings.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    settings.search_db_path.parent.mkdir(parents=True, exist_ok=True)

    yield

    logger.info("Assistant API shutting down")
