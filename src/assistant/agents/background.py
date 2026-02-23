"""Background task management for async agent delegation."""

from __future__ import annotations

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

# ContextVar carries the channel's delivery callback into tool handlers.
# Each asyncio task gets its own copy — no race conditions.
current_delivery: ContextVar[DeliveryCallback | None] = ContextVar(
    "current_delivery", default=None
)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


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
    _deliver: DeliveryCallback | None = field(default=None, repr=False)


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
    ) -> BackgroundTask:
        """Create a new background task with an 8-char hex ID."""
        task_id = os.urandom(4).hex()
        bt = BackgroundTask(
            id=task_id,
            agent_name=agent_name,
            task_description=task_description,
            _deliver=deliver,
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

    def list_all(self) -> list[BackgroundTask]:
        return [self._tasks[tid] for tid in self._order if tid in self._tasks]
