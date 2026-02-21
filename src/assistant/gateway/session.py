"""In-memory conversation session manager."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from assistant.llm.types import Message, Role


@dataclass
class Session:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[Message] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)

    def add_message(self, role: Role | str, content: str) -> None:
        if isinstance(role, str):
            role = Role(role)
        self.messages.append(Message(role=role, content=content))

    def add_tool_call(self, tool_call_info: dict) -> None:
        self.tool_calls.append(tool_call_info)

    def get_context_messages(self, max_messages: int = 50) -> list[Message]:
        return self.messages[-max_messages:]

    @property
    def last_tool_calls(self) -> list[dict]:
        """Tool calls from the most recent exchange (since last user message)."""
        recent: list[dict] = []
        for tc in reversed(self.tool_calls):
            recent.append(tc)
        return list(reversed(recent))

    def clear_tool_calls(self) -> None:
        self.tool_calls.clear()


class SessionManager:
    """Manages conversation sessions (in-memory)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._active_session_id: str | None = None

    def create_session(self) -> Session:
        session = Session()
        self._sessions[session.id] = session
        self._active_session_id = session.id
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    @property
    def active_session(self) -> Session:
        if self._active_session_id and self._active_session_id in self._sessions:
            return self._sessions[self._active_session_id]
        return self.create_session()

    @property
    def session_count(self) -> int:
        return len(self._sessions)
