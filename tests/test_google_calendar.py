"""Tests for Google Calendar integration with mocked API."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from assistant.tools.calendar_tool import calendar_tool, set_google_client
from assistant.tools.google_calendar import format_event


# ---------------------------------------------------------------------------
# Mock Google Calendar client
# ---------------------------------------------------------------------------


class MockGoogleCalendarClient:
    """In-memory mock of GoogleCalendarClient for testing."""

    def __init__(self) -> None:
        self._events: dict[str, dict[str, Any]] = {}
        self._next_id = 1

    async def list_calendars(self) -> list[dict[str, Any]]:
        return [{"id": "primary", "summary": "Main Calendar"}]

    async def list_events(
        self, time_min: str, time_max: str, calendar_id: str = "primary"
    ) -> list[dict[str, Any]]:
        results = []
        for ev in self._events.values():
            start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", ""))
            if start >= time_min[:19] and start <= time_max[:19]:
                results.append({**ev, "_calendar_name": "Main Calendar"})
        results.sort(key=lambda e: e.get("start", {}).get("dateTime", ""))
        return results

    async def list_all_events(
        self, time_min: str, time_max: str
    ) -> list[dict[str, Any]]:
        return await self.list_events(time_min, time_max)

    async def create_event(
        self,
        summary: str,
        start: str,
        end: str | None = None,
        location: str | None = None,
        description: str | None = None,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        event_id = f"gcal_{self._next_id}"
        self._next_id += 1
        event: dict[str, Any] = {
            "id": event_id,
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end or start},
        }
        if location:
            event["location"] = location
        if description:
            event["description"] = description
        self._events[event_id] = event
        return event

    async def update_event(
        self, event_id: str, calendar_id: str = "primary", **fields: Any
    ) -> dict[str, Any]:
        event = self._events.get(event_id)
        if not event:
            raise Exception(f"Event {event_id} not found")
        if fields.get("summary"):
            event["summary"] = fields["summary"]
        if fields.get("location"):
            event["location"] = fields["location"]
        if fields.get("description"):
            event["description"] = fields["description"]
        if fields.get("start"):
            event["start"] = {"dateTime": fields["start"]}
        if fields.get("end"):
            event["end"] = {"dateTime": fields["end"]}
        return event

    async def delete_event(
        self, event_id: str, calendar_id: str = "primary"
    ) -> bool:
        if event_id in self._events:
            del self._events[event_id]
            return True
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def gcal_client() -> MockGoogleCalendarClient:
    client = MockGoogleCalendarClient()
    set_google_client(client)
    return client


# ---------------------------------------------------------------------------
# format_event tests
# ---------------------------------------------------------------------------


class TestFormatEvent:
    def test_timed_event(self) -> None:
        raw = {
            "id": "abc123",
            "summary": "Team Sync",
            "start": {"dateTime": "2025-03-15T14:00:00-07:00"},
            "end": {"dateTime": "2025-03-15T15:00:00-07:00"},
            "location": "Room 4",
            "description": "Weekly sync",
            "_calendar_name": "Work",
        }
        result = format_event(raw)
        assert result["id"] == "abc123"
        assert result["title"] == "Team Sync"
        assert result["start"] == "2025-03-15T14:00:00-07:00"
        assert result["location"] == "Room 4"
        assert result["source"] == "google"
        assert result["calendar"] == "Work"

    def test_all_day_event(self) -> None:
        raw = {
            "id": "def456",
            "summary": "Holiday",
            "start": {"date": "2025-12-25"},
            "end": {"date": "2025-12-26"},
        }
        result = format_event(raw)
        assert result["start"] == "2025-12-25"
        assert result["title"] == "Holiday"

    def test_missing_fields(self) -> None:
        raw = {"id": "x", "start": {"dateTime": "2025-01-01T00:00:00"}}
        result = format_event(raw)
        assert result["title"] == "(no title)"
        assert result["location"] == ""


# ---------------------------------------------------------------------------
# Google Calendar tool handler tests
# ---------------------------------------------------------------------------


class TestGoogleCalendarHandler:
    @pytest.mark.asyncio
    async def test_create_event(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({
                "action": "create",
                "title": "Standup",
                "start": "2025-03-10T09:30:00",
            })
        assert "Event created" in result
        assert "Standup" in result
        assert "gcal_1" in result

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({"action": "create"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_list_empty(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({"action": "list"})
        assert "No events" in result

    @pytest.mark.asyncio
    async def test_list_with_events(self, gcal_client: MockGoogleCalendarClient) -> None:
        await gcal_client.create_event("Meeting", "2025-03-10T14:00:00")
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({
                "action": "list",
                "start": "2025-03-10T00:00:00",
                "end": "2025-03-11T00:00:00",
            })
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Meeting"

    @pytest.mark.asyncio
    async def test_today_empty(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({"action": "today"})
        assert "No events" in result

    @pytest.mark.asyncio
    async def test_update_event(self, gcal_client: MockGoogleCalendarClient) -> None:
        ev = await gcal_client.create_event("Original", "2025-03-10T10:00:00")
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({
                "action": "update",
                "event_id": ev["id"],
                "title": "Updated",
            })
        assert "Updated" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({"action": "update"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_delete_event(self, gcal_client: MockGoogleCalendarClient) -> None:
        ev = await gcal_client.create_event("To Delete", "2025-03-10T10:00:00")
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({"action": "delete", "event_id": ev["id"]})
        assert "deleted" in result

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({"action": "delete"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({"action": "delete", "event_id": "no-such-id"})
        assert "Error" in result or "failed" in result

    @pytest.mark.asyncio
    async def test_feed_actions_return_message(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            for action in ("add_feed", "remove_feed", "sync_feeds"):
                result = await calendar_tool({"action": action, "url": "https://example.com/cal.ics"})
                assert "Google Calendar" in result
                assert "natively" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, gcal_client: MockGoogleCalendarClient) -> None:
        with patch("assistant.tools.calendar_tool._is_google_enabled", return_value=True):
            result = await calendar_tool({"action": "explode"})
        assert "Unknown" in result
