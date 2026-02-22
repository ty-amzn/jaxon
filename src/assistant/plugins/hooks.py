"""HookDispatcher — dispatch hooks to registered plugin handlers."""

from __future__ import annotations

import logging
from typing import Any

from assistant.plugins.manager import PluginManager
from assistant.plugins.types import HookType

logger = logging.getLogger(__name__)


class HookDispatcher:
    """Dispatches hook events to all registered plugin handlers."""

    def __init__(self, plugin_manager: PluginManager) -> None:
        self._plugin_manager = plugin_manager

    async def dispatch(self, hook_type: HookType, **kwargs: Any) -> list[Any]:
        """Dispatch a hook event to all registered handlers.

        Returns list of results from handlers. Errors are logged and skipped.
        """
        all_hooks = self._plugin_manager.get_all_hooks()
        handlers = all_hooks.get(hook_type.value, [])
        results: list[Any] = []

        for plugin_name, handler in handlers:
            try:
                result = await handler(**kwargs)
                results.append(result)
            except Exception:
                logger.exception(
                    "Error in %s hook from plugin %s", hook_type.value, plugin_name
                )

        return results

    async def pre_message(self, message: str, session_id: str = "") -> str:
        """Dispatch PRE_MESSAGE hook. Returns potentially modified message."""
        results = await self.dispatch(
            HookType.PRE_MESSAGE, message=message, session_id=session_id
        )
        # If any hook returns a modified message string, use the last one
        for r in reversed(results):
            if isinstance(r, str):
                return r
        return message

    async def post_message(
        self, message: str, response: str, session_id: str = ""
    ) -> None:
        """Dispatch POST_MESSAGE hook."""
        await self.dispatch(
            HookType.POST_MESSAGE,
            message=message,
            response=response,
            session_id=session_id,
        )

    async def pre_tool_call(
        self, tool_name: str, tool_input: dict[str, Any], session_id: str = ""
    ) -> None:
        """Dispatch PRE_TOOL_CALL hook."""
        await self.dispatch(
            HookType.PRE_TOOL_CALL,
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=session_id,
        )

    async def post_tool_call(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        result: str,
        session_id: str = "",
    ) -> None:
        """Dispatch POST_TOOL_CALL hook."""
        await self.dispatch(
            HookType.POST_TOOL_CALL,
            tool_name=tool_name,
            tool_input=tool_input,
            result=result,
            session_id=session_id,
        )

    async def session_start(self, session_id: str = "") -> None:
        """Dispatch SESSION_START hook."""
        await self.dispatch(HookType.SESSION_START, session_id=session_id)

    async def session_end(self, session_id: str = "") -> None:
        """Dispatch SESSION_END hook."""
        await self.dispatch(HookType.SESSION_END, session_id=session_id)
