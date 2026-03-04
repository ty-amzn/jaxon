"""Paper Trading FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from papertrader.config import Settings
from papertrader.routes import trading_router
from papertrader.store import PaperTradingStore
from papertrader.ui import STATIC_DIR

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    logger.info("Paper Trading starting up (db=%s)", settings.db_path)

    store = PaperTradingStore(settings.db_path, settings.default_starting_cash)
    app.state.store = store

    yield

    logger.info("Paper Trading shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Paper Trading",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(trading_router)
    app.mount("/trading/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app
