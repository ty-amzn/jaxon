"""CalDAV client for Radicale calendar integration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class CalDAVClient:
    """Wrapper around the caldav library for event CRUD operations."""

    def __init__(self, url: str, username: str, password: str) -> None:
        self._url = url
        self._username = username
        self._password = password
        self._calendar: Any = None

    def _get_calendar(self) -> Any:
        """Lazily connect to the CalDAV calendar."""
        if self._calendar is None:
            import caldav

            client = caldav.DAVClient(
                url=self._url,
                username=self._username,
                password=self._password,
            )
            principal = client.principal()
            calendars = principal.calendars()
            if not calendars:
                raise RuntimeError(
                    f"No calendars found at {self._url}. "
                    "Create a calendar collection first."
                )
            # Use the first calendar (or match by URL if the URL points directly to one)
            self._calendar = calendars[0]
            logger.info("Connected to CalDAV calendar: %s", self._calendar.name)
        return self._calendar

    def list_events(self, start: str, end: str) -> list[dict[str, Any]]:
        """List events in a date range. start/end are ISO 8601 strings."""
        from icalendar import Calendar as iCalendar

        cal = self._get_calendar()
        start_dt = _parse_dt(start)
        end_dt = _parse_dt(end)

        results: list[dict[str, Any]] = []
        try:
            events = cal.date_search(start=start_dt, end=end_dt, expand=True)
        except Exception as exc:
            logger.error("CalDAV date_search failed: %s", exc)
            return []

        for event in events:
            try:
                ical = iCalendar.from_ical(event.data)
                for component in ical.walk():
                    if component.name != "VEVENT":
                        continue
                    results.append(_vevent_to_dict(component, event.url))
            except Exception as exc:
                logger.warning("Failed to parse CalDAV event: %s", exc)
        results.sort(key=lambda e: e["start"])
        return results

    def create_event(
        self,
        title: str,
        start: str,
        end: str | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a new calendar event. Returns the created event dict."""
        uid = uuid.uuid4().hex
        dtstart = _parse_dt(start)
        if end:
            dtend = _parse_dt(end)
        else:
            dtend = dtstart + timedelta(hours=1)

        vcal = _build_vcalendar(
            uid=uid,
            summary=title,
            dtstart=dtstart,
            dtend=dtend,
            location=location or "",
            description=notes or "",
        )

        cal = self._get_calendar()
        cal.save_event(vcal)
        logger.info("CalDAV event created: %s (%s)", title, uid)

        return {
            "id": uid,
            "title": title,
            "start": dtstart.isoformat(),
            "end": dtend.isoformat(),
            "location": location or "",
            "notes": notes or "",
            "source": "caldav",
        }

    def update_event(
        self,
        event_id: str,
        title: str | None = None,
        start: str | None = None,
        end: str | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an existing event by UID. Returns updated dict or None."""
        from icalendar import Calendar as iCalendar

        cal = self._get_calendar()
        event_obj = _find_event_by_uid(cal, event_id)
        if event_obj is None:
            return None

        ical = iCalendar.from_ical(event_obj.data)
        for component in ical.walk():
            if component.name != "VEVENT":
                continue
            if title:
                component["SUMMARY"] = title
            if start:
                component["DTSTART"].dt = _parse_dt(start)
            if end:
                component["DTEND"].dt = _parse_dt(end)
            if location is not None:
                component["LOCATION"] = location
            if notes is not None:
                component["DESCRIPTION"] = notes

        event_obj.data = ical.to_ical().decode("utf-8")
        event_obj.save()
        logger.info("CalDAV event updated: %s", event_id)

        # Return the updated event
        for component in ical.walk():
            if component.name == "VEVENT":
                return _vevent_to_dict(component, event_obj.url)
        return None

    def delete_event(self, event_id: str) -> bool:
        """Delete an event by UID. Returns True on success."""
        cal = self._get_calendar()
        event_obj = _find_event_by_uid(cal, event_id)
        if event_obj is None:
            return False
        event_obj.delete()
        logger.info("CalDAV event deleted: %s", event_id)
        return True

    # -- VTODO (Reminders) methods ------------------------------------------

    def list_todos(self, include_completed: bool = False) -> list[dict[str, Any]]:
        """List VTODOs from the calendar."""
        from icalendar import Calendar as iCalendar

        cal = self._get_calendar()
        results: list[dict[str, Any]] = []
        try:
            todos = cal.todos(include_completed=include_completed)
        except Exception as exc:
            logger.error("CalDAV todos() failed: %s", exc)
            return []

        for todo in todos:
            try:
                ical = iCalendar.from_ical(todo.data)
                for component in ical.walk():
                    if component.name != "VTODO":
                        continue
                    results.append(_vtodo_to_dict(component, todo.url))
            except Exception as exc:
                logger.warning("Failed to parse CalDAV VTODO: %s", exc)
        return results

    def create_todo(
        self,
        title: str,
        due: str | None = None,
        priority: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a new VTODO (reminder). Returns the created todo dict."""
        uid = uuid.uuid4().hex
        due_dt = _parse_dt(due) if due else None

        vcal = _build_vtodo(
            uid=uid,
            summary=title,
            due=due_dt,
            priority=priority,
            description=notes or "",
        )

        cal = self._get_calendar()
        cal.save_todo(vcal)
        logger.info("CalDAV todo created: %s (%s)", title, uid)

        return {
            "id": uid,
            "title": title,
            "due": due_dt.isoformat() if due_dt else "",
            "priority": priority or "",
            "notes": notes or "",
            "status": "NEEDS-ACTION",
            "source": "caldav",
        }

    def update_todo(
        self,
        todo_id: str,
        title: str | None = None,
        due: str | None = None,
        priority: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an existing VTODO by UID. Returns updated dict or None."""
        from icalendar import Calendar as iCalendar

        cal = self._get_calendar()
        todo_obj = _find_todo_by_uid(cal, todo_id)
        if todo_obj is None:
            return None

        ical = iCalendar.from_ical(todo_obj.data)
        for component in ical.walk():
            if component.name != "VTODO":
                continue
            if title:
                component["SUMMARY"] = title
            if due:
                from icalendar import vDatetime
                component["DUE"] = vDatetime(_parse_dt(due))
            if priority and priority in _PRIORITY_TO_ICAL:
                component["PRIORITY"] = _PRIORITY_TO_ICAL[priority]
            if notes is not None:
                component["DESCRIPTION"] = notes

        todo_obj.data = ical.to_ical().decode("utf-8")
        todo_obj.save()
        logger.info("CalDAV todo updated: %s", todo_id)

        for component in ical.walk():
            if component.name == "VTODO":
                return _vtodo_to_dict(component, todo_obj.url)
        return None

    def complete_todo(self, todo_id: str) -> dict[str, Any] | None:
        """Mark a VTODO as completed. Returns updated dict or None."""
        from icalendar import Calendar as iCalendar

        cal = self._get_calendar()
        todo_obj = _find_todo_by_uid(cal, todo_id)
        if todo_obj is None:
            return None

        ical = iCalendar.from_ical(todo_obj.data)
        for component in ical.walk():
            if component.name != "VTODO":
                continue
            component["STATUS"] = "COMPLETED"
            from icalendar import vDatetime
            component["COMPLETED"] = vDatetime(datetime.now())

        todo_obj.data = ical.to_ical().decode("utf-8")
        todo_obj.save()
        logger.info("CalDAV todo completed: %s", todo_id)

        for component in ical.walk():
            if component.name == "VTODO":
                return _vtodo_to_dict(component, todo_obj.url)
        return None

    def delete_todo(self, todo_id: str) -> bool:
        """Delete a VTODO by UID. Returns True on success."""
        cal = self._get_calendar()
        todo_obj = _find_todo_by_uid(cal, todo_id)
        if todo_obj is None:
            return False
        todo_obj.delete()
        logger.info("CalDAV todo deleted: %s", todo_id)
        return True

    def list_calendars(self) -> list[dict[str, str]]:
        """List available calendars."""
        import caldav

        client = caldav.DAVClient(
            url=self._url,
            username=self._username,
            password=self._password,
        )
        principal = client.principal()
        return [
            {"name": c.name or str(c.url), "url": str(c.url)}
            for c in principal.calendars()
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_dt(dt_str: str) -> datetime:
    """Parse an ISO 8601 string into a datetime."""
    # Handle date-only strings
    if "T" not in dt_str:
        return datetime.fromisoformat(dt_str + "T00:00:00")
    return datetime.fromisoformat(dt_str)


def _find_event_by_uid(calendar: Any, uid: str) -> Any:
    """Search for an event by UID in a CalDAV calendar."""
    try:
        return calendar.event_by_uid(uid)
    except Exception:
        logger.debug("Event not found by UID: %s", uid)
        return None


def _find_todo_by_uid(calendar: Any, uid: str) -> Any:
    """Search for a VTODO by UID in a CalDAV calendar."""
    try:
        return calendar.todo_by_uid(uid)
    except Exception:
        logger.debug("Todo not found by UID: %s", uid)
        return None


def _vevent_to_dict(component: Any, url: Any = None) -> dict[str, Any]:
    """Convert an icalendar VEVENT component to a flat dict."""
    dtstart = component.get("DTSTART")
    dtend = component.get("DTEND")
    uid = str(component.get("UID", ""))

    start_str = ""
    if dtstart:
        dt = dtstart.dt
        start_str = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

    end_str = ""
    if dtend:
        dt = dtend.dt
        end_str = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

    return {
        "id": uid,
        "title": str(component.get("SUMMARY", "(no title)")),
        "start": start_str,
        "end": end_str,
        "location": str(component.get("LOCATION", "")),
        "notes": str(component.get("DESCRIPTION", "")),
        "source": "caldav",
    }


def _build_vcalendar(
    uid: str,
    summary: str,
    dtstart: datetime,
    dtend: datetime,
    location: str = "",
    description: str = "",
) -> str:
    """Build a VCALENDAR string for a single event."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Assistant//CalDAV//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND:{dtend.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{summary}",
    ]
    if location:
        lines.append(f"LOCATION:{location}")
    if description:
        lines.append(f"DESCRIPTION:{description}")
    lines.append(f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}Z")
    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    return "\r\n".join(lines)


# ---------------------------------------------------------------------------
# VTODO helpers
# ---------------------------------------------------------------------------

# iOS Reminders priority mapping
_PRIORITY_TO_ICAL = {"high": 1, "medium": 5, "low": 9}
_ICAL_TO_PRIORITY = {1: "high", 2: "high", 3: "high", 4: "high",
                     5: "medium", 6: "low", 7: "low", 8: "low", 9: "low"}


def _vtodo_to_dict(component: Any, url: Any = None) -> dict[str, Any]:
    """Convert an icalendar VTODO component to a flat dict."""
    uid = str(component.get("UID", ""))
    due = component.get("DUE")
    due_str = ""
    if due:
        dt = due.dt
        due_str = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

    priority_val = component.get("PRIORITY")
    priority = ""
    if priority_val:
        priority = _ICAL_TO_PRIORITY.get(int(str(priority_val)), "medium")

    status = str(component.get("STATUS", "NEEDS-ACTION"))

    return {
        "id": uid,
        "title": str(component.get("SUMMARY", "(no title)")),
        "due": due_str,
        "priority": priority,
        "notes": str(component.get("DESCRIPTION", "")),
        "status": status,
        "source": "caldav",
    }


def _build_vtodo(
    uid: str,
    summary: str,
    due: datetime | None = None,
    priority: str | None = None,
    description: str = "",
    status: str = "NEEDS-ACTION",
    completed: datetime | None = None,
) -> str:
    """Build a VCALENDAR string containing a single VTODO."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Assistant//CalDAV//EN",
        "BEGIN:VTODO",
        f"UID:{uid}",
        f"SUMMARY:{summary}",
        f"STATUS:{status}",
    ]
    if due:
        lines.append(f"DUE:{due.strftime('%Y%m%dT%H%M%S')}")
    if priority and priority in _PRIORITY_TO_ICAL:
        lines.append(f"PRIORITY:{_PRIORITY_TO_ICAL[priority]}")
    if description:
        lines.append(f"DESCRIPTION:{description}")
    if completed:
        lines.append(f"COMPLETED:{completed.strftime('%Y%m%dT%H%M%S')}Z")
    lines.append(f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}Z")
    lines.extend(["END:VTODO", "END:VCALENDAR"])
    return "\r\n".join(lines)
