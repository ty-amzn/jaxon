"""API routes — health check and future webhooks."""

from __future__ import annotations

from fastapi import APIRouter

from assistant.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()
