"""Background task management for async agent delegation."""

from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from assistant.gateway.permissions import PermissionRequest

# Type alias for delivery callbacks (channel → user message sender)
DeliveryCallback = Callable[[str], Awaitable[None]]

# Review delivery: takes (raw_result, agent_name), routes through main agent
ReviewDeliveryCallback = Callable[[str, str], Awaitable[None]]

# ContextVar carries the channel's delivery callback into tool handlers.
# Each asyncio task gets its own copy — no race conditions.
current_delivery: ContextVar[DeliveryCallback | None] = ContextVar(
    "current_delivery", default=None
)

# ContextVar for review delivery callback (routes results through main agent).
current_review_delivery: ContextVar[ReviewDeliveryCallback | None] = ContextVar(
    "current_review_delivery", default=None
)

# ContextVar carries the current turn's images so delegation tools can
# automatically forward them to sub-agents without the LLM needing to
# reproduce base64 data in tool calls.
current_images: ContextVar[list[dict] | None] = ContextVar(
    "current_images", default=None
)

# ContextVar carries the name of the currently executing agent so tools
# (e.g. feed_tool) can attribute actions to the right author.
current_agent_name: ContextVar[str] = ContextVar(
    "current_agent_name", default="assistant"
)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    id: str
    agent_name: str
    task_description: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    result: str = ""
    error: str = ""
    silent: bool = False
    _deliver: DeliveryCallback | None = field(default=None, repr=False)
    _review_deliver: ReviewDeliveryCallback | None = field(default=None, repr=False)
    _asyncio_task: asyncio.Task | None = field(default=None, repr=False)


async def _auto_approve(request: PermissionRequest) -> bool:
    """Auto-approve all permission requests for background agents.

    Safety is enforced by the agent YAML's allowed_tools whitelist —
    don't give background agents write tools.
    """
    return True


class BackgroundTaskManager:
    """In-memory manager for background agent tasks with bounded eviction."""

    def __init__(self, maxlen: int = 50) -> None:
        self._tasks: dict[str, BackgroundTask] = {}
        self._order: deque[str] = deque(maxlen=maxlen)
        self._maxlen = maxlen

    def create(
        self,
        agent_name: str,
        task_description: str,
        deliver: DeliveryCallback | None = None,
        review_deliver: ReviewDeliveryCallback | None = None,
        silent: bool = False,
    ) -> BackgroundTask:
        """Create a new background task with an 8-char hex ID."""
        task_id = os.urandom(4).hex()
        bt = BackgroundTask(
            id=task_id,
            agent_name=agent_name,
            task_description=task_description,
            silent=silent,
            _deliver=deliver,
            _review_deliver=review_deliver,
        )
        # Evict oldest if at capacity
        if len(self._order) >= self._maxlen:
            evicted_id = self._order[0]  # will be auto-popped by deque
            self._tasks.pop(evicted_id, None)
        self._order.append(task_id)
        self._tasks[task_id] = bt
        return bt

    def get(self, task_id: str) -> BackgroundTask | None:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> tuple[bool, str]:
        """Cancel a background task. Returns (success, message)."""
        bt = self._tasks.get(task_id)
        if bt is None:
            return False, f"No task found with ID: {task_id}"
        if bt.status in (TaskStatus.DONE, TaskStatus.ERROR, TaskStatus.CANCELLED):
            return False, f"Task {task_id} already {bt.status.value}, cannot cancel."
        if bt._asyncio_task is not None:
            bt._asyncio_task.cancel()
        bt.status = TaskStatus.CANCELLED
        bt.finished_at = time.time()
        return True, f"Task {task_id} ({bt.agent_name}) cancelled."

    def list_all(self) -> list[BackgroundTask]:
        return [self._tasks[tid] for tid in self._order if tid in self._tasks]
