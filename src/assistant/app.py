"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI

from assistant.api.routes import router
from assistant.core.events import lifespan


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Assistant",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app
