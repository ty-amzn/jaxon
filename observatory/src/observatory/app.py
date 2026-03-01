"""Observatory FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from observatory.config import Settings
from observatory.routes import observe_router
from observatory.store import ObservatoryStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    logger.info("Observatory starting up (db=%s)", settings.db_path)

    observe_store = ObservatoryStore(settings.db_path)
    app.state.observe_store = observe_store

    raw_cleaned, events_deleted = observe_store.cleanup()
    if raw_cleaned or events_deleted:
        logger.info("Cleanup: %d raw content nulled, %d old events deleted", raw_cleaned, events_deleted)

    yield

    logger.info("Observatory shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Observatory",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(observe_router)
    return app