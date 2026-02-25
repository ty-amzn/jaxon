"""Calendar tool — personal event management + .ics feed subscriptions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import sqlite_utils

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CalendarStore — SQLite persistence
# ---------------------------------------------------------------------------

class CalendarStore:
    """SQLite-backed calendar with local events and .ics feed imports."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        if "events" not in self._db.table_names():
            self._db["events"].create(
                {
                    "id": str,
                    "title": str,
                    "start": str,
                    "end": str,
                    "location": str,
                    "notes": str,
                    "source": str,
                    "created_at": str,
                },
                pk="id",
            )
        if "feeds" not in self._db.table_names():
            self._db["feeds"].create(
                {
                    "url": str,
                    "name": str,
                    "last_synced": str,
                    "origin": str,  # "config" or "manual"
                },
                pk="url",
            )
        else:
            # Migrate: add origin column if missing
            cols = {col.name for col in self._db["feeds"].columns}
            if "origin" not in cols:
                self._db.execute("ALTER TABLE feeds ADD COLUMN origin TEXT DEFAULT 'manual'")

    # -- Events CRUD --------------------------------------------------------

    def create_event(
        self,
        title: str,
        start: str,
        end: str | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": uuid.uuid4().hex[:12],
            "title": title,
            "start": start,
            "end": end or "",
            "location": location or "",
            "notes": notes or "",
            "source": "local",
            "created_at": datetime.now().isoformat(),
        }
        self._db["events"].insert(event)
        return event

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        try:
            return dict(self._db["events"].get(event_id))
        except Exception:
            return None

    def update_event(self, event_id: str, **fields: Any) -> dict[str, Any] | None:
        event = self.get_event(event_id)
        if not event:
            return None
        if event["source"] != "local":
            return None
        allowed = {"title", "start", "end", "location", "notes"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return event
        self._db["events"].update(event_id, updates)
        return {**event, **updates}

    def delete_event(self, event_id: str) -> bool:
        event = self.get_event(event_id)
        if not event or event["source"] != "local":
            return False
        self._db["events"].delete(event_id)
        return True

    def list_events(self, start: str, end: str) -> list[dict[str, Any]]:
        """Return events overlapping [start, end] range, sorted by start."""
        rows = list(
            self._db["events"].rows_where(
                "start <= ? AND (end >= ? OR end = '' OR start >= ?)",
                [end, start, start],
                order_by="start",
            )
        )
        return rows

    # -- Feed management ----------------------------------------------------

    def add_feed(self, url: str, name: str, origin: str = "manual") -> None:
        self._db["feeds"].upsert(
            {"url": url, "name": name, "last_synced": "", "origin": origin},
            pk="url",
        )

    def remove_feed(self, url: str) -> bool:
        try:
            self._db["feeds"].delete(url)
            # Remove all events from this feed
            self._db.execute("DELETE FROM events WHERE source = ?", [url])
            return True
        except Exception:
            return False

    def list_feeds(self) -> list[dict[str, Any]]:
        return list(self._db["feeds"].rows)

    def _replace_feed_events(self, feed_url: str, events: list[dict[str, Any]]) -> int:
        """Delete existing events from feed and insert new ones."""
        self._db.execute("DELETE FROM events WHERE source = ?", [feed_url])
        for ev in events:
            ev["source"] = feed_url
            self._db["events"].insert(ev)
        self._db["feeds"].update(feed_url, {"last_synced": datetime.now().isoformat()})
        return len(events)

    async def sync_feed(self, feed_url: str) -> int:
        """Fetch and parse a single .ics feed. Returns number of events imported."""
        try:
            from icalendar import Calendar
        except ImportError:
            logger.error("icalendar package not installed")
            return 0

        async with make_httpx_client(timeout=30, follow_redirects=True) as client:
            resp = await client.get(feed_url)
            resp.raise_for_status()

        cal = Calendar.from_ical(resp.text)
        events: list[dict[str, Any]] = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")
            summary = str(component.get("summary", ""))
            location = str(component.get("location", ""))

            start_dt = dtstart.dt if dtstart else None
            if start_dt is None:
                continue

            # Normalise to ISO string
            start_str = start_dt.isoformat() if hasattr(start_dt, "isoformat") else str(start_dt)
            end_str = ""
            if dtend:
                end_dt = dtend.dt
                end_str = end_dt.isoformat() if hasattr(end_dt, "isoformat") else str(end_dt)

            uid = str(component.get("uid", uuid.uuid4().hex[:12]))
            events.append(
                {
                    "id": uid[:64],
                    "title": summary,
                    "start": start_str,
                    "end": end_str,
                    "location": location,
                    "notes": "",
                    "created_at": datetime.now().isoformat(),
                }
            )

        return self._replace_feed_events(feed_url, events)

    async def sync_all_feeds(self) -> dict[str, int | str]:
        """Sync all feeds. Returns {url: count_or_error}."""
        results: dict[str, int | str] = {}
        for feed in self.list_feeds():
            try:
                count = await self.sync_feed(feed["url"])
                results[feed["url"]] = count
            except Exception as exc:
                results[feed["url"]] = f"error: {exc}"
        return results


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

CALENDAR_TOOL_DEF: dict[str, Any] = {
    "name": "calendar",
    "description": (
        "Manage the user's personal calendar. Actions:\n"
        "- create: add an event (title, start required; end, location, notes optional)\n"
        "- list: list events in a date range (defaults to next 7 days)\n"
        "- today: shortcut to list today's events\n"
        "- update: modify a local event by id\n"
        "- delete: remove a local event by id\n"
        "- add_feed: subscribe to an .ics calendar feed URL (manually added)\n"
        "- remove_feed: unsubscribe from a manually-added feed (config-managed feeds cannot be removed here — the user must edit .env)\n"
        "- sync_feeds: re-fetch all subscribed .ics feeds\n\n"
        "Feeds have two origins: 'config' (from ASSISTANT_CALENDAR_FEEDS in .env, managed automatically) "
        "and 'manual' (added via this tool). You can only add/remove manual feeds.\n\n"
        "All datetimes should be ISO 8601 (e.g. 2025-03-15T14:00:00)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "create",
                    "list",
                    "today",
                    "update",
                    "delete",
                    "add_feed",
                    "remove_feed",
                    "sync_feeds",
                ],
                "description": "The calendar action to perform.",
            },
            "title": {
                "type": "string",
                "description": "Event title (for create/update).",
            },
            "start": {
                "type": "string",
                "description": "Start datetime in ISO 8601 (for create/update/list).",
            },
            "end": {
                "type": "string",
                "description": "End datetime in ISO 8601 (for create/update/list).",
            },
            "location": {
                "type": "string",
                "description": "Event location (for create/update).",
            },
            "notes": {
                "type": "string",
                "description": "Event notes (for create/update).",
            },
            "event_id": {
                "type": "string",
                "description": "Event ID (for update/delete).",
            },
            "url": {
                "type": "string",
                "description": "ICS feed URL (for add_feed/remove_feed).",
            },
            "name": {
                "type": "string",
                "description": "Display name for the feed (for add_feed).",
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# Singleton store (lazily created)
# ---------------------------------------------------------------------------

_store: CalendarStore | None = None
_caldav_client: Any = None


def _get_store() -> CalendarStore:
    global _store
    if _store is None:
        from assistant.core.config import get_settings
        settings = get_settings()
        db_path = settings.data_dir / "db" / "calendar.db"
        _store = CalendarStore(db_path)
    return _store


def set_store(store: CalendarStore) -> None:
    """Override the store (for tests)."""
    global _store
    _store = store


def _is_caldav_enabled() -> bool:
    from assistant.core.config import get_settings
    return get_settings().caldav_enabled


def _get_caldav_client() -> Any:
    """Lazily create CalDAVClient if enabled."""
    global _caldav_client
    if _caldav_client is None:
        from assistant.core.config import get_settings
        from assistant.tools.caldav_client import CalDAVClient

        settings = get_settings()
        _caldav_client = CalDAVClient(
            url=settings.caldav_url,
            username=settings.caldav_username,
            password=settings.caldav_password,
        )
    return _caldav_client


def set_caldav_client(client: Any) -> None:
    """Override the CalDAV client (for tests)."""
    global _caldav_client
    _caldav_client = client


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------

async def calendar_tool(params: dict[str, Any]) -> str:
    """Handle calendar tool calls. Routes to CalDAV or SQLite."""
    action = params.get("action", "list")

    # Feed actions always use SQLite (read-only ICS imports)
    if action in ("add_feed", "remove_feed", "sync_feeds"):
        return await _sqlite_calendar_handler(params)

    if _is_caldav_enabled():
        return await _caldav_calendar_handler(params)
    return await _sqlite_calendar_handler(params)


async def _caldav_calendar_handler(params: dict[str, Any]) -> str:
    """Handle calendar actions via CalDAV (Radicale)."""
    import json

    client = _get_caldav_client()
    action = params.get("action", "list")

    if action == "create":
        title = params.get("title")
        start = params.get("start")
        if not title or not start:
            return "Error: 'title' and 'start' are required for create."
        event = client.create_event(
            title=title,
            start=start,
            end=params.get("end"),
            location=params.get("location"),
            notes=params.get("notes"),
        )
        return f"Event created: {event['title']} at {event['start']} (id: {event['id']})"

    elif action == "today":
        today = datetime.now().strftime("%Y-%m-%dT00:00:00")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        events = client.list_events(today, tomorrow)
        # Also include feed events from SQLite
        store = _get_store()
        feed_events = store.list_events(today, tomorrow)
        all_events = events + [e for e in feed_events if e.get("source", "local") != "local"]
        if not all_events:
            return "No events today."
        all_events.sort(key=lambda e: e["start"])
        return json.dumps(all_events, indent=2)

    elif action == "list":
        start = params.get("start", datetime.now().strftime("%Y-%m-%dT00:00:00"))
        end = params.get(
            "end",
            (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59"),
        )
        events = client.list_events(start, end)
        # Also include feed events from SQLite
        store = _get_store()
        feed_events = store.list_events(start, end)
        all_events = events + [e for e in feed_events if e.get("source", "local") != "local"]
        if not all_events:
            return f"No events between {start} and {end}."
        all_events.sort(key=lambda e: e["start"])
        return json.dumps(all_events, indent=2)

    elif action == "update":
        event_id = params.get("event_id")
        if not event_id:
            return "Error: 'event_id' is required for update."
        result = client.update_event(
            event_id,
            title=params.get("title"),
            start=params.get("start"),
            end=params.get("end"),
            location=params.get("location"),
            notes=params.get("notes"),
        )
        if result is None:
            return "Error: event not found."
        return f"Event updated: {result['title']}"

    elif action == "delete":
        event_id = params.get("event_id")
        if not event_id:
            return "Error: 'event_id' is required for delete."
        if client.delete_event(event_id):
            return f"Event {event_id} deleted."
        return "Error: event not found."

    else:
        return f"Unknown calendar action: {action}"


async def _sqlite_calendar_handler(params: dict[str, Any]) -> str:
    """Handle calendar actions via local SQLite store."""
    import json

    store = _get_store()
    action = params.get("action", "list")

    if action == "create":
        title = params.get("title")
        start = params.get("start")
        if not title or not start:
            return "Error: 'title' and 'start' are required for create."
        event = store.create_event(
            title=title,
            start=start,
            end=params.get("end"),
            location=params.get("location"),
            notes=params.get("notes"),
        )
        return f"Event created: {event['title']} at {event['start']} (id: {event['id']})"

    elif action == "today":
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        events = store.list_events(today, tomorrow)
        if not events:
            return "No events today."
        return json.dumps(events, indent=2)

    elif action == "list":
        start = params.get("start", datetime.now().strftime("%Y-%m-%d"))
        end = params.get(
            "end",
            (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59"),
        )
        events = store.list_events(start, end)
        if not events:
            return f"No events between {start} and {end}."
        return json.dumps(events, indent=2)

    elif action == "update":
        event_id = params.get("event_id")
        if not event_id:
            return "Error: 'event_id' is required for update."
        result = store.update_event(
            event_id,
            title=params.get("title"),
            start=params.get("start"),
            end=params.get("end"),
            location=params.get("location"),
            notes=params.get("notes"),
        )
        if result is None:
            return "Error: event not found or is from an external feed (read-only)."
        return f"Event updated: {result['title']}"

    elif action == "delete":
        event_id = params.get("event_id")
        if not event_id:
            return "Error: 'event_id' is required for delete."
        if store.delete_event(event_id):
            return f"Event {event_id} deleted."
        return "Error: event not found or is from an external feed (read-only)."

    elif action == "add_feed":
        url = params.get("url")
        name = params.get("name", "")
        if not url:
            return "Error: 'url' is required for add_feed."
        store.add_feed(url, name or url)
        try:
            count = await store.sync_feed(url)
            return f"Feed added and synced: {count} events imported."
        except Exception as exc:
            return f"Feed saved but sync failed: {exc}"

    elif action == "remove_feed":
        url = params.get("url")
        if not url:
            return "Error: 'url' is required for remove_feed."
        # Check if this is a config-managed feed
        for existing in store.list_feeds():
            if existing["url"] == url and existing.get("origin", "manual") == "config":
                return "Error: this feed is managed by config (ASSISTANT_CALENDAR_FEEDS). Remove it from .env instead."
        if store.remove_feed(url):
            return f"Feed removed: {url}"
        return "Error: feed not found."

    elif action == "sync_feeds":
        results = await store.sync_all_feeds()
        if not results:
            return "No feeds to sync."
        lines = []
        for feed_url, result in results.items():
            if isinstance(result, int):
                lines.append(f"  {feed_url}: {result} events")
            else:
                lines.append(f"  {feed_url}: {result}")
        return "Sync complete:\n" + "\n".join(lines)

    else:
        return f"Unknown calendar action: {action}"


# ---------------------------------------------------------------------------
# Auto-sync configured feeds from settings
# ---------------------------------------------------------------------------

async def sync_configured_feeds() -> None:
    """Register and sync ICS feeds defined in ASSISTANT_CALENDAR_FEEDS.

    Treats the env config as source of truth: feeds removed from config
    are also removed from the database.
    """
    from assistant.core.config import get_settings

    feeds = get_settings().calendar_feeds
    store = _get_store()

    configured_urls = {feed["url"] for feed in feeds}

    # Remove config-origin feeds that are no longer in config
    # Manual feeds (added by agent via tool) are left untouched
    for existing in store.list_feeds():
        if existing.get("origin", "manual") == "config" and existing["url"] not in configured_urls:
            store.remove_feed(existing["url"])
            logger.info("Removed stale calendar feed: %s", existing["url"])

    if not feeds:
        return

    # Add/update configured feeds (tagged as config-origin)
    for feed in feeds:
        store.add_feed(url=feed["url"], name=feed["name"], origin="config")
    results = await store.sync_all_feeds()
    for url, result in results.items():
        logger.info("Calendar feed sync %s: %s", url, result)
