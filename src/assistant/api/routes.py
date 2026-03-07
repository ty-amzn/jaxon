"""API routes — health check and deep health dashboard."""

from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, Request

from assistant.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()


async def _ping(client: httpx.AsyncClient, url: str) -> dict:
    """Ping a service health endpoint, return status and latency."""
    if not url:
        return {"status": "not_configured"}
    try:
        start = time.monotonic()
        resp = await client.get(url)
        latency_ms = round((time.monotonic() - start) * 1000)
        if resp.status_code == 200:
            return {"status": "ok", "latency_ms": latency_ms}
        return {"status": "error", "http_status": resp.status_code, "latency_ms": latency_ms}
    except httpx.ConnectError:
        return {"status": "unreachable"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/health/deep")
async def deep_health(request: Request):
    """Aggregate health across all services."""
    settings = request.app.state.settings

    service_urls = {
        "jaxon": "/health",
        "townsquare": f"{settings.townsquare_url}/feed/health" if settings.townsquare_url else "",
        "observatory": f"{settings.observatory_url}/observe/health" if settings.observatory_url else "",
        "papertrader": f"{settings.paper_trading_url}/trading/health" if settings.paper_trading_url else "",
    }

    results = {}
    async with httpx.AsyncClient(timeout=5) as client:
        # Jaxon is always ok (we're serving this request)
        results["jaxon"] = {"status": "ok"}

        for name, url in service_urls.items():
            if name == "jaxon":
                continue
            results[name] = await _ping(client, url)

    all_ok = all(r["status"] in ("ok", "not_configured") for r in results.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "services": results,
    }
