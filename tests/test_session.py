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
