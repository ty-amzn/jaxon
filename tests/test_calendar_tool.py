"""Tests for the calendar tool and CalendarStore."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from unittest.mock import MagicMock, patch

from assistant.tools.calendar_tool import (
    CalendarStore,
    calendar_tool,
    set_caldav_client,
    set_store,
)


@pytest.fixture(autouse=True)
def _force_sqlite_mode():
    """Ensure all tests in this module use the SQLite backend by default."""
    with patch("assistant.tools.calendar_tool._is_caldav_enabled", return_value=False):
        yield


@pytest.fixture()
def store(tmp_path: Path) -> CalendarStore:
    s = CalendarStore(tmp_path / "calendar.db")
    set_store(s)
    return s


# ---------------------------------------------------------------------------
# CalendarStore unit tests
# ---------------------------------------------------------------------------


class TestCalendarStore:
    def test_create_and_get(self, store: CalendarStore) -> None:
        ev = store.create_event("Dentist", "2025-03-10T09:00:00")
        assert ev["title"] == "Dentist"
        assert ev["source"] == "local"
        fetched = store.get_event(ev["id"])
        assert fetched is not None
        assert fetched["title"] == "Dentist"

    def test_update(self, store: CalendarStore) -> None:
        ev = store.create_event("Meeting", "2025-03-10T14:00:00")
        updated = store.update_event(ev["id"], title="Team Sync", location="Room 4")
        assert updated is not None
        assert updated["title"] == "Team Sync"
        assert updated["location"] == "Room 4"

    def test_update_nonexistent(self, store: CalendarStore) -> None:
        assert store.update_event("no-such-id", title="X") is None

    def test_delete(self, store: CalendarStore) -> None:
        ev = store.create_event("Delete Me", "2025-03-10T10:00:00")
        assert store.delete_event(ev["id"]) is True
        assert store.get_event(ev["id"]) is None

    def test_delete_nonexistent(self, store: CalendarStore) -> None:
        assert store.delete_event("no-such-id") is False

    def test_list_events_range(self, store: CalendarStore) -> None:
        store.create_event("A", "2025-03-10T09:00:00")
        store.create_event("B", "2025-03-11T09:00:00")
        store.create_event("C", "2025-03-15T09:00:00")
        events = store.list_events("2025-03-10", "2025-03-12")
        titles = [e["title"] for e in events]
        assert "A" in titles
        assert "B" in titles
        assert "C" not in titles

    def test_feed_lifecycle(self, store: CalendarStore) -> None:
        store.add_feed("https://example.com/cal.ics", "Test Cal")
        feeds = store.list_feeds()
        assert len(feeds) == 1
        assert feeds[0]["name"] == "Test Cal"

        assert store.remove_feed("https://example.com/cal.ics") is True
        assert store.list_feeds() == []

    def test_cannot_edit_feed_events(self, store: CalendarStore) -> None:
        """Events from feeds should be read-only."""
        store.add_feed("https://example.com/cal.ics", "Test")
        # Manually insert a feed event
        store._db["events"].insert({
            "id": "feed-ev-1",
            "title": "External Meeting",
            "start": "2025-03-10T10:00:00",
            "end": "",
            "location": "",
            "notes": "",
            "source": "https://example.com/cal.ics",
            "created_at": datetime.now().isoformat(),
        })
        assert store.update_event("feed-ev-1", title="Hacked") is None
        assert store.delete_event("feed-ev-1") is False

    def test_replace_feed_events(self, store: CalendarStore) -> None:
        store.add_feed("https://example.com/cal.ics", "Test")
        # Insert initial events
        store._replace_feed_events("https://example.com/cal.ics", [
            {
                "id": "ev1",
                "title": "Old Event",
                "start": "2025-03-10T10:00:00",
                "end": "",
                "location": "",
                "notes": "",
                "created_at": datetime.now().isoformat(),
            },
        ])
        assert len(store.list_events("2025-03-10", "2025-03-11")) == 1

        # Replace with new set
        store._replace_feed_events("https://example.com/cal.ics", [
            {
                "id": "ev2",
                "title": "New Event A",
                "start": "2025-03-10T10:00:00",
                "end": "",
                "location": "",
                "notes": "",
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": "ev3",
                "title": "New Event B",
                "start": "2025-03-10T11:00:00",
                "end": "",
                "location": "",
                "notes": "",
                "created_at": datetime.now().isoformat(),
            },
        ])
        events = store.list_events("2025-03-10", "2025-03-11")
        assert len(events) == 2
        titles = {e["title"] for e in events}
        assert titles == {"New Event A", "New Event B"}


# ---------------------------------------------------------------------------
# Tool handler tests
# ---------------------------------------------------------------------------


class TestCalendarToolHandler:
    @pytest.mark.asyncio
    async def test_create_event(self, store: CalendarStore) -> None:
        result = await calendar_tool({
            "action": "create",
            "title": "Standup",
            "start": "2025-03-10T09:30:00",
        })
        assert "Event created" in result
        assert "Standup" in result

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, store: CalendarStore) -> None:
        result = await calendar_tool({"action": "create"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_list_empty(self, store: CalendarStore) -> None:
        result = await calendar_tool({"action": "list"})
        assert "No events" in result

    @pytest.mark.asyncio
    async def test_today_empty(self, store: CalendarStore) -> None:
        result = await calendar_tool({"action": "today"})
        assert "No events" in result

    @pytest.mark.asyncio
    async def test_delete_event(self, store: CalendarStore) -> None:
        ev = store.create_event("To Delete", "2025-03-10T10:00:00")
        result = await calendar_tool({"action": "delete", "event_id": ev["id"]})
        assert "deleted" in result

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, store: CalendarStore) -> None:
        result = await calendar_tool({"action": "delete"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_update_event(self, store: CalendarStore) -> None:
        ev = store.create_event("Original", "2025-03-10T10:00:00")
        result = await calendar_tool({
            "action": "update",
            "event_id": ev["id"],
            "title": "Updated",
        })
        assert "Updated" in result

    @pytest.mark.asyncio
    async def test_sync_no_feeds(self, store: CalendarStore) -> None:
        result = await calendar_tool({"action": "sync_feeds"})
        assert "No feeds" in result

    @pytest.mark.asyncio
    async def test_add_feed_missing_url(self, store: CalendarStore) -> None:
        result = await calendar_tool({"action": "add_feed"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_remove_feed_missing_url(self, store: CalendarStore) -> None:
        result = await calendar_tool({"action": "remove_feed"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, store: CalendarStore) -> None:
        result = await calendar_tool({"action": "explode"})
        assert "Unknown" in result


# ---------------------------------------------------------------------------
# ICS parsing test
# ---------------------------------------------------------------------------


class TestICSParsing:
    @pytest.mark.asyncio
    async def test_sync_feed_parses_ics(self, store: CalendarStore, monkeypatch) -> None:
        """Test that .ics content is correctly parsed into events."""
        ics_content = """\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20250315T100000Z
DTEND:20250315T110000Z
SUMMARY:Team Standup
LOCATION:Zoom
UID:test-uid-123
END:VEVENT
BEGIN:VEVENT
DTSTART:20250316T140000Z
SUMMARY:1:1 with Manager
UID:test-uid-456
END:VEVENT
END:VCALENDAR"""

        class FakeResponse:
            status_code = 200
            text = ics_content
            def raise_for_status(self):
                pass

        class FakeClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def get(self, url):
                return FakeResponse()

        monkeypatch.setattr("assistant.tools.calendar_tool.make_httpx_client", lambda **kw: FakeClient())

        store.add_feed("https://example.com/test.ics", "Test")
        count = await store.sync_feed("https://example.com/test.ics")
        assert count == 2

        events = store.list_events("2025-03-15", "2025-03-17")
        assert len(events) == 2
        titles = {e["title"] for e in events}
        assert "Team Standup" in titles
        assert "1:1 with Manager" in titles


# ---------------------------------------------------------------------------
# CalDAV handler tests
# ---------------------------------------------------------------------------


class _MockCalDAVClient:
    """Mock CalDAV client for testing the handler."""

    def __init__(self):
        self._events: dict[str, dict] = {}

    def create_event(self, title, start, end=None, location=None, notes=None):
        import uuid
        eid = uuid.uuid4().hex[:12]
        ev = {
            "id": eid,
            "title": title,
            "start": start,
            "end": end or "",
            "location": location or "",
            "notes": notes or "",
            "source": "caldav",
        }
        self._events[eid] = ev
        return ev

    def list_events(self, start, end):
        return [
            e for e in self._events.values()
            if e["start"] >= start and e["start"] <= end
        ]

    def update_event(self, event_id, title=None, start=None, end=None, location=None, notes=None):
        ev = self._events.get(event_id)
        if ev is None:
            return None
        if title:
            ev["title"] = title
        if start:
            ev["start"] = start
        if end:
            ev["end"] = end
        if location is not None:
            ev["location"] = location
        if notes is not None:
            ev["notes"] = notes
        return ev

    def delete_event(self, event_id):
        if event_id in self._events:
            del self._events[event_id]
            return True
        return False


class TestCalDAVHandler:
    @pytest.fixture(autouse=True)
    def _caldav_mode(self, store):
        """Enable CalDAV mode with a mock client."""
        mock_client = _MockCalDAVClient()
        set_caldav_client(mock_client)
        self._client = mock_client
        with patch("assistant.tools.calendar_tool._is_caldav_enabled", return_value=True):
            yield
        set_caldav_client(None)

    @pytest.mark.asyncio
    async def test_create_event(self, store):
        result = await calendar_tool({
            "action": "create",
            "title": "CalDAV Meeting",
            "start": "2025-03-10T10:00:00",
        })
        assert "Event created" in result
        assert "CalDAV Meeting" in result

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, store):
        result = await calendar_tool({"action": "create"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_list_events(self, store):
        self._client.create_event("Lunch", "2025-03-10T12:00:00")
        result = await calendar_tool({
            "action": "list",
            "start": "2025-03-10T00:00:00",
            "end": "2025-03-10T23:59:59",
        })
        assert "Lunch" in result

    @pytest.mark.asyncio
    async def test_list_empty(self, store):
        result = await calendar_tool({
            "action": "list",
            "start": "2025-03-10T00:00:00",
            "end": "2025-03-10T23:59:59",
        })
        assert "No events" in result

    @pytest.mark.asyncio
    async def test_update_event(self, store):
        ev = self._client.create_event("Old Title", "2025-03-10T10:00:00")
        result = await calendar_tool({
            "action": "update",
            "event_id": ev["id"],
            "title": "New Title",
        })
        assert "New Title" in result

    @pytest.mark.asyncio
    async def test_update_not_found(self, store):
        result = await calendar_tool({
            "action": "update",
            "event_id": "nonexistent",
            "title": "X",
        })
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_delete_event(self, store):
        ev = self._client.create_event("Delete Me", "2025-03-10T10:00:00")
        result = await calendar_tool({
            "action": "delete",
            "event_id": ev["id"],
        })
        assert "deleted" in result

    @pytest.mark.asyncio
    async def test_delete_not_found(self, store):
        result = await calendar_tool({
            "action": "delete",
            "event_id": "nonexistent",
        })
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, store):
        result = await calendar_tool({"action": "delete"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, store):
        result = await calendar_tool({"action": "update"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, store):
        result = await calendar_tool({"action": "explode"})
        assert "Unknown" in result

    @pytest.mark.asyncio
    async def test_feed_actions_use_sqlite(self, store):
        """Feed actions should still work via SQLite even in CalDAV mode."""
        result = await calendar_tool({"action": "sync_feeds"})
        assert "No feeds" in result

        result = await calendar_tool({"action": "add_feed"})
        assert "Error" in result

        result = await calendar_tool({"action": "remove_feed"})
        assert "Error" in result
