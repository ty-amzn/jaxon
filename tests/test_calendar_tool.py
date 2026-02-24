"""Tests for the calendar tool and CalendarStore."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from assistant.tools.calendar_tool import CalendarStore, calendar_tool, set_store


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

        monkeypatch.setattr("assistant.tools.calendar_tool.httpx.AsyncClient", lambda **kw: FakeClient())

        store.add_feed("https://example.com/test.ics", "Test")
        count = await store.sync_feed("https://example.com/test.ics")
        assert count == 2

        events = store.list_events("2025-03-15", "2025-03-17")
        assert len(events) == 2
        titles = {e["title"] for e in events}
        assert "Team Standup" in titles
        assert "1:1 with Manager" in titles
