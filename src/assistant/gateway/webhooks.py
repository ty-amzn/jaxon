"""Webhook receiver for triggering workflows and jobs."""

from __future__ import annotations

import hashlib
import hmac
import logging
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


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/{name}")
async def receive_webhook(
    name: str,
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, Any]:
    """Receive a webhook and trigger the matching workflow."""
    body = await request.body()

    # Validate HMAC if secret is configured
    if _webhook_secret:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing signature")
        if not verify_signature(body, x_hub_signature_256, _webhook_secret):
            raise HTTPException(status_code=403, detail="Invalid signature")

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
