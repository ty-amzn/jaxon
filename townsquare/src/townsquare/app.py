"""Town Square FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from townsquare.config import Settings
from townsquare.routes import feed_router
from townsquare.store import FeedStore
from townsquare.ui import STATIC_DIR

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
    app.mount("/feed/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app
