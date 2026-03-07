"""Observatory API routes."""

from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from observatory.ui import APP_ICON_SVG, DASHBOARD_HTML, MANIFEST_JSON, SERVICE_WORKER_JS

observe_router = APIRouter(prefix="/observe", tags=["observe"])


@observe_router.get("/health")
async def health_check():
    return {"status": "ok", "service": "observatory"}


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


@observe_router.get("/health/deep")
async def deep_health(request: Request):
    """Aggregate health across all services."""
    settings = request.app.state.settings
    service_urls = {
        "observatory": "",  # self — always ok
        "jaxon": f"{settings.jaxon_url}/health" if settings.jaxon_url else "",
        "townsquare": f"{settings.townsquare_url}/feed/health" if settings.townsquare_url else "",
        "papertrader": f"{settings.papertrader_url}/trading/health" if settings.papertrader_url else "",
    }

    results = {"observatory": {"status": "ok"}}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in service_urls.items():
            if name == "observatory":
                continue
            results[name] = await _ping(client, url)

    all_ok = all(r["status"] in ("ok", "not_configured") for r in results.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "services": results,
    }


class ToolEventBody(BaseModel):
    timestamp: str | None = None
    tool_name: str = Field(..., min_length=1)
    duration_ms: int = Field(..., ge=0)
    success: bool = True
    error_message: str | None = None
    session_id: str | None = None
    agent_name: str | None = None
    action_category: str | None = None


class InferenceEventBody(BaseModel):
    timestamp: str | None = None
    provider: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    duration_ms: int = Field(..., ge=0)
    success: bool = True
    error_message: str | None = None
    session_id: str | None = None
    agent_name: str | None = None
    tool_rounds: int = Field(0, ge=0)
    has_tools: bool = False
    routed_from: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    raw_prompt: str | None = None
    raw_response: str | None = None


# -- Static assets -----------------------------------------------------------

@observe_router.get("/ui", response_class=HTMLResponse)
async def observe_ui():
    return HTMLResponse(DASHBOARD_HTML)


@observe_router.get("/manifest.json")
async def observe_manifest():
    return Response(MANIFEST_JSON, media_type="application/manifest+json")


@observe_router.get("/sw.js")
async def observe_service_worker():
    return Response(
        SERVICE_WORKER_JS,
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/observe/"},
    )


@observe_router.get("/icon-192.svg")
async def observe_icon_192():
    return Response(APP_ICON_SVG, media_type="image/svg+xml")


@observe_router.get("/icon-512.svg")
async def observe_icon_512():
    return Response(APP_ICON_SVG, media_type="image/svg+xml")


# -- Events ------------------------------------------------------------------

@observe_router.post("/events")
async def log_event(request: Request, body: InferenceEventBody):
    store = request.app.state.observe_store
    event = store.log_event(body.model_dump())
    return {"ok": True, "id": event["id"]}


@observe_router.get("/events")
async def get_events(
    request: Request,
    limit: int = 100,
    before_id: int | None = None,
    provider: str | None = None,
    model: str | None = None,
    session_id: str | None = None,
    success: bool | None = None,
    agent_name: str | None = None,
):
    store = request.app.state.observe_store
    events = store.get_events(
        limit=limit,
        before_id=before_id,
        provider=provider,
        model=model,
        session_id=session_id,
        success=success,
        agent_name=agent_name,
    )
    return events


@observe_router.get("/events/{event_id}")
async def get_event(request: Request, event_id: int):
    store = request.app.state.observe_store
    event = store.get_event(event_id)
    if event is None:
        return {"error": "Event not found."}
    return event


@observe_router.get("/events/{event_id}/raw")
async def get_event_raw(request: Request, event_id: int):
    store = request.app.state.observe_store
    event = store.get_event(event_id)
    if event is None:
        return {"error": "Event not found."}
    return {
        "id": event.get("id"),
        "raw_prompt": event.get("raw_prompt"),
        "raw_response": event.get("raw_response"),
    }


# -- Statistics --------------------------------------------------------------

@observe_router.get("/stats")
async def get_stats(
    request: Request,
    period_hours: int = 24,
    provider: str | None = None,
    model: str | None = None,
):
    store = request.app.state.observe_store
    stats = store.get_stats(period_hours=period_hours, provider=provider, model=model)
    return stats


@observe_router.get("/timeline")
async def get_timeline(
    request: Request,
    period_hours: int = 24,
    offset_hours: int = 0,
    bucket_hours: int = 1,
):
    store = request.app.state.observe_store
    data = store.get_timeline(
        period_hours=period_hours,
        offset_hours=offset_hours,
        bucket_hours=bucket_hours,
    )
    return data


# -- Tool Events -------------------------------------------------------------

@observe_router.post("/tool-events")
async def log_tool_event(request: Request, body: ToolEventBody):
    store = request.app.state.observe_store
    event = store.log_tool_event(body.model_dump())
    return {"ok": True, "id": event["id"]}


@observe_router.get("/tool-events")
async def get_tool_events(
    request: Request,
    limit: int = 100,
    before_id: int | None = None,
    tool_name: str | None = None,
    agent_name: str | None = None,
    success: bool | None = None,
):
    store = request.app.state.observe_store
    return store.get_tool_events(
        limit=limit,
        before_id=before_id,
        tool_name=tool_name,
        agent_name=agent_name,
        success=success,
    )


@observe_router.get("/tool-stats")
async def get_tool_stats(request: Request, period_hours: int = 24):
    store = request.app.state.observe_store
    return store.get_tool_stats(period_hours=period_hours)


# -- Sessions ----------------------------------------------------------------

@observe_router.get("/sessions")
async def get_sessions(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    agent_name: str | None = None,
):
    store = request.app.state.observe_store
    return store.get_sessions(limit=limit, offset=offset, agent_name=agent_name)


@observe_router.get("/sessions/{session_id}")
async def get_session_trace(request: Request, session_id: str):
    store = request.app.state.observe_store
    trace = store.get_session_trace(session_id)
    if not trace:
        return {"error": "Session not found or has no events."}
    return trace


# -- Agents ------------------------------------------------------------------

@observe_router.get("/agent-summary")
async def get_agent_summary(request: Request, period_hours: int = 24):
    store = request.app.state.observe_store
    return store.get_agent_summary(period_hours=period_hours)