"""Tests for the notification dispatcher and DND."""

from __future__ import annotations

from datetime import time

import pytest

from assistant.core.notifications import NotificationDispatcher, in_dnd_window, parse_time


# --- NotificationDispatcher ---


@pytest.mark.asyncio
async def test_dispatcher_multiple_sinks():
    """Dispatcher sends to all registered sinks."""
    dispatcher = NotificationDispatcher()
    received: list[str] = []

    async def sink1(msg: str) -> None:
        received.append(f"sink1:{msg}")

    async def sink2(msg: str) -> None:
        received.append(f"sink2:{msg}")

    dispatcher.register(sink1)
    dispatcher.register(sink2)
    await dispatcher.send("hello")

    assert received == ["sink1:hello", "sink2:hello"]


@pytest.mark.asyncio
async def test_dispatcher_failing_sink_isolation():
    """A failing sink does not prevent other sinks from receiving."""
    dispatcher = NotificationDispatcher()
    received: list[str] = []

    async def bad_sink(msg: str) -> None:
        raise RuntimeError("boom")

    async def good_sink(msg: str) -> None:
        received.append(msg)

    dispatcher.register(bad_sink)
    dispatcher.register(good_sink)
    await dispatcher.send("test")

    assert received == ["test"]


@pytest.mark.asyncio
async def test_dispatcher_unregister():
    """Unregistering a sink removes it."""
    dispatcher = NotificationDispatcher()
    received: list[str] = []

    async def sink(msg: str) -> None:
        received.append(msg)

    dispatcher.register(sink)
    await dispatcher.send("a")
    dispatcher.unregister(sink)
    await dispatcher.send("b")

    assert received == ["a"]


# --- DND ---


def test_parse_time():
    """parse_time correctly parses HH:MM strings."""
    assert parse_time("23:00") == time(23, 0)
    assert parse_time("07:30") == time(7, 30)
    assert parse_time("00:00") == time(0, 0)


def test_in_dnd_window_no_midnight_cross():
    """DND window within same day (e.g. 09:00 - 17:00)."""
    start = time(9, 0)
    end = time(17, 0)

    assert in_dnd_window(time(12, 0), start, end) is True
    assert in_dnd_window(time(8, 0), start, end) is False
    assert in_dnd_window(time(17, 0), start, end) is False


def test_in_dnd_window_midnight_cross():
    """DND window crossing midnight (e.g. 23:00 - 07:00)."""
    start = time(23, 0)
    end = time(7, 0)

    assert in_dnd_window(time(23, 30), start, end) is True
    assert in_dnd_window(time(2, 0), start, end) is True
    assert in_dnd_window(time(12, 0), start, end) is False
    assert in_dnd_window(time(7, 0), start, end) is False


@pytest.mark.asyncio
async def test_dispatcher_dnd_queues_messages():
    """Messages are queued during DND window."""
    dispatcher = NotificationDispatcher(
        dnd_enabled=True,
        dnd_start="00:00",
        dnd_end="23:59",  # Always in DND
    )
    received: list[str] = []

    async def sink(msg: str) -> None:
        received.append(msg)

    dispatcher.register(sink)
    await dispatcher.send("hello")

    assert received == []
    assert dispatcher.queued_count == 1


@pytest.mark.asyncio
async def test_dispatcher_dnd_allows_urgent():
    """Urgent messages bypass DND."""
    dispatcher = NotificationDispatcher(
        dnd_enabled=True,
        dnd_start="00:00",
        dnd_end="23:59",
        allow_urgent=True,
    )
    received: list[str] = []

    async def sink(msg: str) -> None:
        received.append(msg)

    dispatcher.register(sink)
    await dispatcher.send("urgent!", urgent=True)

    assert received == ["urgent!"]
    assert dispatcher.queued_count == 0


@pytest.mark.asyncio
async def test_dispatcher_flush_queue():
    """Queued messages can be flushed."""
    dispatcher = NotificationDispatcher(
        dnd_enabled=True,
        dnd_start="00:00",
        dnd_end="23:59",
    )
    received: list[str] = []

    async def sink(msg: str) -> None:
        received.append(msg)

    dispatcher.register(sink)
    await dispatcher.send("msg1")
    await dispatcher.send("msg2")

    assert dispatcher.queued_count == 2

    count = await dispatcher.flush_queue()
    assert count == 2
    assert received == ["msg1", "msg2"]
    assert dispatcher.queued_count == 0


@pytest.mark.asyncio
async def test_dispatcher_no_dnd_sends_immediately():
    """Without DND, messages are sent immediately (backward compatible)."""
    dispatcher = NotificationDispatcher()
    received: list[str] = []

    async def sink(msg: str) -> None:
        received.append(msg)

    dispatcher.register(sink)
    await dispatcher.send("hello")

    assert received == ["hello"]
