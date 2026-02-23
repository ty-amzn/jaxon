"""WhatsApp-based permission approval via text reply."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from assistant.gateway.permissions import PermissionRequest

if TYPE_CHECKING:
    from assistant.whatsapp.bot import WhatsAppBot

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUT = 600  # seconds (10 minutes)
APPROVE_WORDS = {"y", "yes", "ok", "approve", "sure", "yep", "yeah", "go ahead"}


class WhatsAppApprovalCallback:
    """Sends a permission prompt via WhatsApp, waits for a text reply."""

    def __init__(self, bot: "WhatsAppBot", sender_number: str) -> None:
        self._bot = bot
        self._number = sender_number
        # Pending futures keyed by request_id
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def __call__(self, request: PermissionRequest) -> bool:
        request_id = f"perm_{id(request)}"
        future: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        await self._bot.send_message(
            self._number,
            f"🔒 Permission needed [{request.action_category.value}]:\n"
            f"{request.description}\n\n"
            f"Reply YES to approve or NO to deny.",
        )

        try:
            return await asyncio.wait_for(future, timeout=APPROVAL_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("WhatsApp permission timed out for %s", request.description)
            await self._bot.send_message(
                self._number, "Permission timed out — denied."
            )
            return False
        finally:
            self._pending.pop(request_id, None)

    def try_resolve(self, text: str) -> bool:
        """Try to resolve the oldest pending approval with this text.

        Returns True if the text was consumed as an approval response.
        """
        if not self._pending:
            return False

        # Resolve the oldest pending request
        request_id = next(iter(self._pending))
        future = self._pending.get(request_id)
        if future and not future.done():
            approved = text.strip().lower() in APPROVE_WORDS
            future.set_result(approved)
            return True
        return False
