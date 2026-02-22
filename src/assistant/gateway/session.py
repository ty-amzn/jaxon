"""In-memory conversation session manager with thread support."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from assistant.gateway.thread_store import Thread, ThreadStore
from assistant.llm.types import Message, Role


@dataclass
class Session:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[Message] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    thread_id: str | None = None
    thread_name: str | None = None

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

    def to_thread_dict(self) -> dict[str, Any]:
        """Export session as a thread-compatible dict."""
        return {
            "thread_id": self.thread_id,
            "thread_name": self.thread_name,
            "messages": [m.to_api() for m in self.messages],
            "tool_calls": self.tool_calls,
        }

    def load_from_thread(self, thread: Thread) -> None:
        """Load messages from a thread into this session."""
        self.thread_id = thread.id
        self.thread_name = thread.name
        self.messages.clear()
        self.tool_calls.clear()
        for msg in thread.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self.messages.append(Message(role=Role(role), content=content))


class SessionManager:
    """Manages conversation sessions (in-memory) with optional thread persistence."""

    def __init__(self, thread_store: ThreadStore | None = None) -> None:
        self._sessions: dict[str, Session] = {}
        self._active_session_id: str | None = None
        self._keyed_sessions: dict[str, str] = {}  # external key -> session id
        self._thread_store = thread_store

    def create_session(self, name: str | None = None) -> Session:
        session = Session()
        if name:
            session.thread_name = name
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

    def get_or_create_keyed_session(self, key: str) -> Session:
        """Get or create a session by an external key (e.g. Telegram chat_id).

        Unlike create_session, this does NOT change the active session.
        """
        # Check if we already have a session mapped to this key
        if key in self._keyed_sessions:
            session_id = self._keyed_sessions[key]
            session = self._sessions.get(session_id)
            if session:
                return session

        # Create a new session without changing active
        session = Session()
        self._sessions[session.id] = session
        self._keyed_sessions[key] = session.id
        return session

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    def save_current_thread(self) -> Thread | None:
        """Save the current session as a thread."""
        if not self._thread_store:
            return None

        session = self.active_session
        if not session.messages:
            return None

        # Create or update thread
        if session.thread_id:
            thread = self._thread_store.load(session.thread_id)
            if thread:
                thread.messages = [m.to_api() for m in session.messages]
            else:
                thread = self._thread_store.create_thread(
                    name=session.thread_name or f"Thread {session.thread_id}",
                    thread_id=session.thread_id,
                )
                thread.messages = [m.to_api() for m in session.messages]
        else:
            thread = self._thread_store.create_thread(
                name=session.thread_name or f"Session {session.id}"
            )
            thread.messages = [m.to_api() for m in session.messages]
            session.thread_id = thread.id
            session.thread_name = thread.name

        self._thread_store.save(thread)
        return thread

    def load_thread(self, thread_id: str) -> Session | None:
        """Load a thread into a new session."""
        if not self._thread_store:
            return None

        thread = self._thread_store.load(thread_id)
        if not thread:
            return None

        session = self.create_session(name=thread.name)
        session.load_from_thread(thread)
        return session

    def load_thread_by_name(self, name: str) -> Session | None:
        """Load a thread by name into a new session."""
        if not self._thread_store:
            return None

        thread = self._thread_store.load_by_name(name)
        if not thread:
            return None

        return self.load_thread(thread.id)

    def list_threads(self) -> list[Thread]:
        """List all saved threads."""
        if not self._thread_store:
            return []
        return self._thread_store.list_threads()