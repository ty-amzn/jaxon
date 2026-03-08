"""Tests for session management."""

from assistant.gateway.session import Session, SessionManager
from assistant.llm.types import Role


def test_session_add_message():
    s = Session()
    s.add_message(Role.USER, "Hello")
    s.add_message(Role.ASSISTANT, "Hi")
    assert len(s.messages) == 2
    assert s.messages[0].role == Role.USER
    assert s.messages[1].content == "Hi"


def test_session_context_limit():
    s = Session()
    for i in range(100):
        s.add_message(Role.USER, f"msg {i}")
    context = s.get_context_messages(max_messages=10)
    assert len(context) == 10
    assert context[0].content == "msg 90"


def test_session_manager():
    sm = SessionManager()
    session = sm.active_session
    assert session is not None
    assert sm.session_count == 1

    same = sm.active_session
    assert same.id == session.id
    assert sm.session_count == 1


def test_session_manager_create():
    sm = SessionManager()
    s1 = sm.create_session()
    s2 = sm.create_session()
    assert s1.id != s2.id
    assert sm.session_count == 2
    assert sm.active_session.id == s2.id


def test_keyed_session_creates_and_reuses():
    """get_or_create_keyed_session creates a session and reuses it by key."""
    manager = SessionManager()

    session1 = manager.get_or_create_keyed_session("telegram_123")
    session2 = manager.get_or_create_keyed_session("telegram_123")
    session3 = manager.get_or_create_keyed_session("telegram_456")

    assert session1.id == session2.id
    assert session1.id != session3.id


def test_keyed_session_does_not_change_active():
    """Keyed sessions should not change the active session."""
    manager = SessionManager()
    active = manager.active_session  # Creates and sets active
    active_id = active.id

    _ = manager.get_or_create_keyed_session("external_key")
    assert manager.active_session.id == active_id
