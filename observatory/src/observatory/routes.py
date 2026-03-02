"""Observatory API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from observatory.ui import APP_ICON_SVG, DASHBOARD_HTML, MANIFEST_JSON, SERVICE_WORKER_JS

observe_router = APIRouter(prefix="/observe", tags=["observe"])


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
async def get_stats(request: Request, period_hours: int = 24):
    store = request.app.state.observe_store
    stats = store.get_stats(period_hours=period_hours)
    return stats


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