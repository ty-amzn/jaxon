"""Tests for the reminders tool (VTODO via CalDAV)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from assistant.tools.reminders_tool import reminders_tool, set_reminders_client


class _MockCalDAVClient:
    """Mock CalDAV client with VTODO CRUD methods."""

    def __init__(self) -> None:
        self._todos: dict[str, dict[str, Any]] = {}

    def create_todo(
        self,
        title: str,
        due: str | None = None,
        priority: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        tid = uuid.uuid4().hex[:12]
        todo = {
            "id": tid,
            "title": title,
            "due": due or "",
            "priority": priority or "",
            "notes": notes or "",
            "status": "NEEDS-ACTION",
            "source": "caldav",
        }
        self._todos[tid] = todo
        return todo

    def list_todos(self, include_completed: bool = False) -> list[dict[str, Any]]:
        if include_completed:
            return list(self._todos.values())
        return [t for t in self._todos.values() if t["status"] != "COMPLETED"]

    def complete_todo(self, todo_id: str) -> dict[str, Any] | None:
        todo = self._todos.get(todo_id)
        if todo is None:
            return None
        todo["status"] = "COMPLETED"
        return todo

    def update_todo(
        self,
        todo_id: str,
        title: str | None = None,
        due: str | None = None,
        priority: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        todo = self._todos.get(todo_id)
        if todo is None:
            return None
        if title:
            todo["title"] = title
        if due:
            todo["due"] = due
        if priority:
            todo["priority"] = priority
        if notes is not None:
            todo["notes"] = notes
        return todo

    def delete_todo(self, todo_id: str) -> bool:
        if todo_id in self._todos:
            del self._todos[todo_id]
            return True
        return False


@pytest.fixture(autouse=True)
def mock_client():
    client = _MockCalDAVClient()
    set_reminders_client(client)
    yield client
    set_reminders_client(None)


class TestRemindersCreate:
    @pytest.mark.asyncio
    async def test_create(self, mock_client: _MockCalDAVClient) -> None:
        result = await reminders_tool({
            "action": "create",
            "title": "Buy milk",
            "due": "2025-03-15T18:00:00",
            "priority": "medium",
        })
        assert "Reminder created" in result
        assert "Buy milk" in result
        assert len(mock_client._todos) == 1

    @pytest.mark.asyncio
    async def test_create_minimal(self, mock_client: _MockCalDAVClient) -> None:
        result = await reminders_tool({"action": "create", "title": "Do thing"})
        assert "Reminder created" in result
        assert "Do thing" in result

    @pytest.mark.asyncio
    async def test_create_missing_title(self) -> None:
        result = await reminders_tool({"action": "create"})
        assert "Error" in result


class TestRemindersList:
    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        result = await reminders_tool({"action": "list"})
        assert "No pending reminders" in result

    @pytest.mark.asyncio
    async def test_list_with_items(self, mock_client: _MockCalDAVClient) -> None:
        mock_client.create_todo("Task A")
        mock_client.create_todo("Task B")
        result = await reminders_tool({"action": "list"})
        assert "Task A" in result
        assert "Task B" in result

    @pytest.mark.asyncio
    async def test_list_excludes_completed(self, mock_client: _MockCalDAVClient) -> None:
        todo = mock_client.create_todo("Done task")
        mock_client.complete_todo(todo["id"])
        result = await reminders_tool({"action": "list"})
        assert "No pending reminders" in result

    @pytest.mark.asyncio
    async def test_list_include_completed(self, mock_client: _MockCalDAVClient) -> None:
        todo = mock_client.create_todo("Done task")
        mock_client.complete_todo(todo["id"])
        result = await reminders_tool({"action": "list", "include_completed": True})
        assert "Done task" in result


class TestRemindersComplete:
    @pytest.mark.asyncio
    async def test_complete(self, mock_client: _MockCalDAVClient) -> None:
        todo = mock_client.create_todo("Finish report")
        result = await reminders_tool({"action": "complete", "reminder_id": todo["id"]})
        assert "Reminder completed" in result
        assert "Finish report" in result

    @pytest.mark.asyncio
    async def test_complete_not_found(self) -> None:
        result = await reminders_tool({"action": "complete", "reminder_id": "nonexistent"})
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_complete_missing_id(self) -> None:
        result = await reminders_tool({"action": "complete"})
        assert "Error" in result


class TestRemindersUpdate:
    @pytest.mark.asyncio
    async def test_update(self, mock_client: _MockCalDAVClient) -> None:
        todo = mock_client.create_todo("Old title")
        result = await reminders_tool({
            "action": "update",
            "reminder_id": todo["id"],
            "title": "New title",
        })
        assert "Reminder updated" in result
        assert "New title" in result

    @pytest.mark.asyncio
    async def test_update_not_found(self) -> None:
        result = await reminders_tool({
            "action": "update",
            "reminder_id": "nonexistent",
            "title": "X",
        })
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self) -> None:
        result = await reminders_tool({"action": "update"})
        assert "Error" in result


class TestRemindersDelete:
    @pytest.mark.asyncio
    async def test_delete(self, mock_client: _MockCalDAVClient) -> None:
        todo = mock_client.create_todo("Delete me")
        result = await reminders_tool({"action": "delete", "reminder_id": todo["id"]})
        assert "deleted" in result
        assert len(mock_client._todos) == 0

    @pytest.mark.asyncio
    async def test_delete_not_found(self) -> None:
        result = await reminders_tool({"action": "delete", "reminder_id": "nonexistent"})
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_delete_missing_id(self) -> None:
        result = await reminders_tool({"action": "delete"})
        assert "Error" in result


class TestRemindersUnknown:
    @pytest.mark.asyncio
    async def test_unknown_action(self) -> None:
        result = await reminders_tool({"action": "explode"})
        assert "Unknown" in result
