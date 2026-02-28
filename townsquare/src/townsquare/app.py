"""Town Square FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from townsquare.config import Settings
from townsquare.routes import feed_router
from townsquare.store import FeedStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    logger.info("Town Square starting up (db=%s)", settings.db_path)

    feed_store = FeedStore(settings.db_path)
    app.state.feed_store = feed_store

    yield

    logger.info("Town Square shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Town Square",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(feed_router)
    return app
