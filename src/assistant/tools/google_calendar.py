"""Google Calendar API client using httpx + google-auth."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from google.oauth2.credentials import Credentials

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

CALENDAR_API = "https://www.googleapis.com/calendar/v3"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    """Lightweight Google Calendar v3 client using httpx."""

    def __init__(
        self,
        credentials_path: Path,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._credentials_path = credentials_path
        self._client_id = client_id
        self._client_secret = client_secret
        self._creds: Credentials | None = None

    def _load_credentials(self) -> Credentials:
        """Load saved credentials from JSON file."""
        if not self._credentials_path.exists():
            raise FileNotFoundError(
                "Google Calendar credentials not found. "
                "Run `assistant google-auth` to authenticate."
            )
        data = json.loads(self._credentials_path.read_text())
        return Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=SCOPES,
        )

    def _save_credentials(self, creds: Credentials) -> None:
        """Persist refreshed credentials."""
        self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
        }
        self._credentials_path.write_text(json.dumps(data))

    def _ensure_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._creds is None:
            self._creds = self._load_credentials()

        if self._creds.expired and self._creds.refresh_token:
            from google.auth.transport.requests import Request

            self._creds.refresh(Request())
            self._save_credentials(self._creds)

        return self._creds.token

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make an authenticated request to the Calendar API."""
        token = self._ensure_token()
        url = f"{CALENDAR_API}{path}"
        headers = {"Authorization": f"Bearer {token}"}

        async with make_httpx_client(timeout=30) as client:
            resp = await client.request(
                method, url, headers=headers, params=params, json=json_body
            )
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()

    # -- Calendar list -------------------------------------------------------

    async def list_calendars(self) -> list[dict[str, Any]]:
        """List all calendars visible to this account."""
        data = await self._request("GET", "/users/me/calendarList")
        return data.get("items", [])

    # -- Events --------------------------------------------------------------

    async def list_events(
        self,
        time_min: str,
        time_max: str,
        calendar_id: str = "primary",
    ) -> list[dict[str, Any]]:
        """List events from a single calendar in a time range."""
        # Ensure RFC 3339 format
        time_min = _ensure_rfc3339(time_min)
        time_max = _ensure_rfc3339(time_max)

        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "250",
        }
        data = await self._request("GET", f"/calendars/{calendar_id}/events", params=params)
        return data.get("items", [])

    async def list_all_events(
        self,
        time_min: str,
        time_max: str,
    ) -> list[dict[str, Any]]:
        """List events across all visible calendars."""
        calendars = await self.list_calendars()
        all_events: list[dict[str, Any]] = []
        for cal in calendars:
            cal_id = cal["id"]
            try:
                events = await self.list_events(time_min, time_max, calendar_id=cal_id)
                for ev in events:
                    ev["_calendar_name"] = cal.get("summary", cal_id)
                all_events.extend(events)
            except httpx.HTTPStatusError as exc:
                logger.warning("Failed to list events from %s: %s", cal_id, exc)
        # Sort by start time
        all_events.sort(key=lambda e: _event_start(e))
        return all_events

    async def create_event(
        self,
        summary: str,
        start: str,
        end: str | None = None,
        location: str | None = None,
        description: str | None = None,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Create a new calendar event."""
        body: dict[str, Any] = {"summary": summary}

        # Determine if all-day or timed
        if "T" in start:
            body["start"] = {"dateTime": _ensure_rfc3339(start)}
            if end:
                body["end"] = {"dateTime": _ensure_rfc3339(end)}
            else:
                # Default 1-hour duration
                from dateutil.parser import isoparse

                start_dt = isoparse(start)
                end_dt = start_dt + timedelta(hours=1)
                body["end"] = {"dateTime": _ensure_rfc3339(end_dt.isoformat())}
        else:
            body["start"] = {"date": start}
            body["end"] = {"date": end or start}

        if location:
            body["location"] = location
        if description:
            body["description"] = description

        return await self._request("POST", f"/calendars/{calendar_id}/events", json_body=body)

    async def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        **fields: Any,
    ) -> dict[str, Any]:
        """Update an existing event (PATCH)."""
        body: dict[str, Any] = {}
        if "summary" in fields and fields["summary"]:
            body["summary"] = fields["summary"]
        if "location" in fields and fields["location"]:
            body["location"] = fields["location"]
        if "description" in fields and fields["description"]:
            body["description"] = fields["description"]
        if "start" in fields and fields["start"]:
            start = fields["start"]
            if "T" in start:
                body["start"] = {"dateTime": _ensure_rfc3339(start)}
            else:
                body["start"] = {"date": start}
        if "end" in fields and fields["end"]:
            end = fields["end"]
            if "T" in end:
                body["end"] = {"dateTime": _ensure_rfc3339(end)}
            else:
                body["end"] = {"date": end}

        if not body:
            return await self._request("GET", f"/calendars/{calendar_id}/events/{event_id}")

        return await self._request(
            "PATCH", f"/calendars/{calendar_id}/events/{event_id}", json_body=body
        )

    async def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> bool:
        """Delete an event. Returns True on success."""
        try:
            await self._request("DELETE", f"/calendars/{calendar_id}/events/{event_id}")
            return True
        except httpx.HTTPStatusError as exc:
            logger.error("Failed to delete event %s: %s", event_id, exc)
            return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_rfc3339(dt_str: str) -> str:
    """Ensure a datetime string is RFC 3339 (with timezone offset)."""
    if dt_str.endswith("Z"):
        return dt_str
    # If it already has timezone info (+/- offset), keep it
    if "+" in dt_str[10:] or dt_str.endswith("Z"):
        return dt_str
    # Check for negative offset (but not the date separator dash)
    parts = dt_str.split("T")
    if len(parts) == 2 and "-" in parts[1]:
        return dt_str
    # Assume local time — append no offset marker for Google (it uses calendar TZ)
    # Google accepts datetimes without offset if the calendar has a timezone set
    return dt_str


def _event_start(event: dict[str, Any]) -> str:
    """Extract a sortable start string from a Google Calendar event."""
    start = event.get("start", {})
    return start.get("dateTime", start.get("date", ""))


def format_event(event: dict[str, Any]) -> dict[str, Any]:
    """Convert a Google Calendar event to a simplified dict for display."""
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event.get("id", ""),
        "title": event.get("summary", "(no title)"),
        "start": start.get("dateTime", start.get("date", "")),
        "end": end.get("dateTime", end.get("date", "")),
        "location": event.get("location", ""),
        "notes": event.get("description", ""),
        "calendar": event.get("_calendar_name", ""),
        "source": "google",
    }
