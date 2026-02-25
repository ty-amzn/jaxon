"""Webhook receiver for triggering workflows and jobs."""

from __future__ import annotations

import logging
import secrets
from typing import Any, TYPE_CHECKING

from fastapi import APIRouter, Header, HTTPException, Request

if TYPE_CHECKING:
    from assistant.core.notifications import NotificationDispatcher
    from assistant.scheduler.workflow import WorkflowManager, WorkflowRunner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Module-level references set during app startup
_webhook_secret: str = ""
_workflow_manager: WorkflowManager | None = None
_workflow_runner: WorkflowRunner | None = None
_dispatcher: NotificationDispatcher | None = None


def configure_webhooks(
    secret: str,
    workflow_manager: WorkflowManager,
    workflow_runner: WorkflowRunner,
    dispatcher: NotificationDispatcher,
) -> None:
    """Configure the webhook module with runtime dependencies."""
    global _webhook_secret, _workflow_manager, _workflow_runner, _dispatcher
    _webhook_secret = secret
    _workflow_manager = workflow_manager
    _workflow_runner = workflow_runner
    _dispatcher = dispatcher


def verify_bearer_token(token: str, secret: str) -> bool:
    """Verify a bearer token against the configured secret (constant-time)."""
    return secrets.compare_digest(token, secret)


@router.post("/{name}")
async def receive_webhook(
    name: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Receive a webhook and trigger the matching workflow."""
    # Validate bearer token if secret is configured
    if _webhook_secret:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization header")
        # Accept "Bearer <token>" or raw token
        token = authorization.removeprefix("Bearer ").strip()
        if not verify_bearer_token(token, _webhook_secret):
            raise HTTPException(status_code=403, detail="Invalid token")

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    if _workflow_manager is None or _workflow_runner is None:
        raise HTTPException(status_code=503, detail="Workflow system not initialized")

    # Look up workflow by name
    workflow = _workflow_manager.get(name)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"No workflow named '{name}'")

    if not workflow.enabled:
        raise HTTPException(status_code=409, detail=f"Workflow '{name}' is disabled")

    # Run the workflow with the webhook payload as context
    results = await _workflow_runner.run(workflow, context=payload)

    logger.info("Webhook '%s' triggered workflow '%s'", name, workflow.name)

    if _dispatcher:
        summary = "\n".join(f"  {r['step']}: {r['status']}" for r in results)
        await _dispatcher.send(f"Webhook '{name}' triggered workflow:\n{summary}")

    return {"status": "ok", "workflow": name, "results": results}
