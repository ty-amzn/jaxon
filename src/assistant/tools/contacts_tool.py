"""Contacts tool — personal relationship management (PRM)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlite_utils

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ContactStore — SQLite persistence
# ---------------------------------------------------------------------------


class ContactStore:
    """SQLite-backed personal contacts / relationship manager."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        if "contacts" not in self._db.table_names():
            self._db["contacts"].create(
                {
                    "id": str,
                    "name": str,
                    "relationship": str,
                    "how_met": str,
                    "organization": str,
                    "location": str,
                    "email": str,
                    "phone": str,
                    "social": str,
                    "notes": str,
                    "birthday": str,
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
            )

    # -- CRUD ---------------------------------------------------------------

    def add(
        self,
        name: str,
        relationship: str = "",
        how_met: str = "",
        organization: str = "",
        location: str = "",
        email: str = "",
        phone: str = "",
        social: str = "",
        notes: str = "",
        birthday: str = "",
    ) -> dict[str, Any]:
        now = datetime.now().isoformat()
        contact = {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "relationship": relationship,
            "how_met": how_met,
            "organization": organization,
            "location": location,
            "email": email,
            "phone": phone,
            "social": social,
            "notes": notes,
            "birthday": birthday,
            "created_at": now,
            "updated_at": now,
        }
        self._db["contacts"].insert(contact)
        return contact

    def get(self, contact_id: str) -> dict[str, Any] | None:
        try:
            return dict(self._db["contacts"].get(contact_id))
        except Exception:
            return None

    def get_by_name(self, name: str) -> list[dict[str, Any]]:
        """Case-insensitive name lookup (exact or substring)."""
        return list(
            self._db["contacts"].rows_where(
                "name LIKE ?", [f"%{name}%"]
            )
        )

    def update(self, contact_id: str, **fields: Any) -> dict[str, Any] | None:
        contact = self.get(contact_id)
        if not contact:
            return None
        allowed = {
            "name", "relationship", "how_met", "organization",
            "location", "email", "phone", "social", "notes", "birthday",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return contact
        updates["updated_at"] = datetime.now().isoformat()
        self._db["contacts"].update(contact_id, updates)
        return {**contact, **updates}

    def delete(self, contact_id: str) -> bool:
        if not self.get(contact_id):
            return False
        self._db["contacts"].delete(contact_id)
        return True

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search across name, relationship, organization, location, notes."""
        pattern = f"%{query}%"
        return list(
            self._db["contacts"].rows_where(
                "name LIKE ? OR relationship LIKE ? OR organization LIKE ? "
                "OR location LIKE ? OR notes LIKE ?",
                [pattern] * 5,
            )
        )

    def list_all(self, relationship: str | None = None) -> list[dict[str, Any]]:
        if relationship:
            return list(
                self._db["contacts"].rows_where(
                    "relationship LIKE ?", [f"%{relationship}%"]
                )
            )
        return list(self._db["contacts"].rows)

    def append_notes(self, contact_id: str, text: str) -> dict[str, Any] | None:
        contact = self.get(contact_id)
        if not contact:
            return None
        timestamp = datetime.now().strftime("%Y-%m-%d")
        entry = f"[{timestamp}] {text}"
        existing = contact.get("notes", "")
        new_notes = f"{existing}\n{entry}" if existing else entry
        now = datetime.now().isoformat()
        self._db["contacts"].update(contact_id, {"notes": new_notes, "updated_at": now})
        return {**contact, "notes": new_notes, "updated_at": now}


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

CONTACTS_TOOL_DEF: dict[str, Any] = {
    "name": "contacts",
    "description": (
        "Manage the user's personal contacts and relationships (personal CRM). Actions:\n"
        "- add: create a new contact (name required; relationship, how_met, organization, "
        "location, email, phone, social, notes, birthday optional)\n"
        "- get: retrieve a contact by contact_id or name\n"
        "- update: modify a contact by contact_id (partial update of any fields)\n"
        "- delete: remove a contact by contact_id\n"
        "- search: search across all text fields by query\n"
        "- list: list all contacts, optionally filtered by relationship\n"
        "- append_notes: append a timestamped note to a contact's notes\n\n"
        "Proactive behavior:\n"
        "- When someone's name comes up in conversation, search contacts to see if they're known\n"
        "- When learning about a new person, suggest adding them as a contact\n"
        "- When learning new info about an existing contact, use append_notes to record it"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "get", "update", "delete", "search", "list", "append_notes"],
                "description": "The contacts action to perform.",
            },
            "contact_id": {
                "type": "string",
                "description": "Contact ID (for get/update/delete/append_notes).",
            },
            "name": {
                "type": "string",
                "description": "Full name (for add/get/update).",
            },
            "relationship": {
                "type": "string",
                "description": "Relationship type, e.g. friend, colleague, family (for add/update/list filter).",
            },
            "how_met": {
                "type": "string",
                "description": "How the user knows this person (for add/update).",
            },
            "organization": {
                "type": "string",
                "description": "Where they work or study (for add/update).",
            },
            "location": {
                "type": "string",
                "description": "Where they live (for add/update).",
            },
            "email": {
                "type": "string",
                "description": "Email address (for add/update).",
            },
            "phone": {
                "type": "string",
                "description": "Phone number (for add/update).",
            },
            "social": {
                "type": "string",
                "description": "Social media handles as JSON string (for add/update).",
            },
            "notes": {
                "type": "string",
                "description": "Free-form notes (for add/update/append_notes).",
            },
            "birthday": {
                "type": "string",
                "description": "Birthday in ISO date format, e.g. 1990-05-15 (for add/update).",
            },
            "query": {
                "type": "string",
                "description": "Search query (for search action).",
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------

_store: ContactStore | None = None


def _get_store() -> ContactStore:
    global _store
    if _store is None:
        from assistant.core.config import get_settings

        settings = get_settings()
        db_path = settings.data_dir / "db" / "contacts.db"
        _store = ContactStore(db_path)
    return _store


def set_store(store: ContactStore) -> None:
    """Override the store (for tests)."""
    global _store
    _store = store


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------


async def contacts_tool(params: dict[str, Any]) -> str:
    """Handle contacts tool calls."""
    store = _get_store()
    action = params.get("action", "list")

    if action == "add":
        name = params.get("name")
        if not name:
            return "Error: 'name' is required for add."
        contact = store.add(
            name=name,
            relationship=params.get("relationship", ""),
            how_met=params.get("how_met", ""),
            organization=params.get("organization", ""),
            location=params.get("location", ""),
            email=params.get("email", ""),
            phone=params.get("phone", ""),
            social=params.get("social", ""),
            notes=params.get("notes", ""),
            birthday=params.get("birthday", ""),
        )
        return f"Contact added: {contact['name']} (id: {contact['id']})"

    elif action == "get":
        contact_id = params.get("contact_id")
        name = params.get("name")
        if contact_id:
            contact = store.get(contact_id)
            if not contact:
                return "Error: contact not found."
            return json.dumps(contact, indent=2)
        elif name:
            matches = store.get_by_name(name)
            if not matches:
                return f"No contacts found matching '{name}'."
            return json.dumps(matches, indent=2)
        else:
            return "Error: 'contact_id' or 'name' is required for get."

    elif action == "update":
        contact_id = params.get("contact_id")
        if not contact_id:
            return "Error: 'contact_id' is required for update."
        result = store.update(
            contact_id,
            name=params.get("name"),
            relationship=params.get("relationship"),
            how_met=params.get("how_met"),
            organization=params.get("organization"),
            location=params.get("location"),
            email=params.get("email"),
            phone=params.get("phone"),
            social=params.get("social"),
            notes=params.get("notes"),
            birthday=params.get("birthday"),
        )
        if result is None:
            return "Error: contact not found."
        return f"Contact updated: {result['name']}"

    elif action == "delete":
        contact_id = params.get("contact_id")
        if not contact_id:
            return "Error: 'contact_id' is required for delete."
        if store.delete(contact_id):
            return f"Contact {contact_id} deleted."
        return "Error: contact not found."

    elif action == "search":
        query = params.get("query")
        if not query:
            return "Error: 'query' is required for search."
        results = store.search(query)
        if not results:
            return f"No contacts matching '{query}'."
        return json.dumps(results, indent=2)

    elif action == "list":
        relationship = params.get("relationship")
        contacts = store.list_all(relationship=relationship)
        if not contacts:
            if relationship:
                return f"No contacts with relationship '{relationship}'."
            return "No contacts yet."
        return json.dumps(contacts, indent=2)

    elif action == "append_notes":
        contact_id = params.get("contact_id")
        notes = params.get("notes")
        if not contact_id:
            return "Error: 'contact_id' is required for append_notes."
        if not notes:
            return "Error: 'notes' is required for append_notes."
        result = store.append_notes(contact_id, notes)
        if result is None:
            return "Error: contact not found."
        return f"Notes updated for {result['name']}."

    else:
        return f"Unknown contacts action: {action}"
