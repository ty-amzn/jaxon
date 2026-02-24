"""Tests for the contacts tool and ContactStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from assistant.tools.contacts_tool import ContactStore, contacts_tool, set_store


@pytest.fixture()
def store(tmp_path: Path) -> ContactStore:
    s = ContactStore(tmp_path / "contacts.db")
    set_store(s)
    return s


# ---------------------------------------------------------------------------
# ContactStore unit tests
# ---------------------------------------------------------------------------


class TestContactStore:
    def test_add_and_get(self, store: ContactStore) -> None:
        c = store.add("Alice Smith", relationship="friend", organization="Acme")
        assert c["name"] == "Alice Smith"
        assert c["relationship"] == "friend"
        fetched = store.get(c["id"])
        assert fetched is not None
        assert fetched["name"] == "Alice Smith"

    def test_get_nonexistent(self, store: ContactStore) -> None:
        assert store.get("no-such-id") is None

    def test_get_by_name(self, store: ContactStore) -> None:
        store.add("Bob Jones")
        store.add("Bobby Tables")
        matches = store.get_by_name("Bob")
        assert len(matches) == 2

    def test_get_by_name_case_insensitive(self, store: ContactStore) -> None:
        store.add("Carol White")
        matches = store.get_by_name("carol")
        assert len(matches) == 1

    def test_update(self, store: ContactStore) -> None:
        c = store.add("Dave Brown")
        updated = store.update(c["id"], organization="BigCorp", email="dave@big.com")
        assert updated is not None
        assert updated["organization"] == "BigCorp"
        assert updated["email"] == "dave@big.com"

    def test_update_nonexistent(self, store: ContactStore) -> None:
        assert store.update("no-such-id", name="X") is None

    def test_update_no_changes(self, store: ContactStore) -> None:
        c = store.add("Eve Green")
        result = store.update(c["id"])
        assert result is not None
        assert result["name"] == "Eve Green"

    def test_delete(self, store: ContactStore) -> None:
        c = store.add("Frank Black")
        assert store.delete(c["id"]) is True
        assert store.get(c["id"]) is None

    def test_delete_nonexistent(self, store: ContactStore) -> None:
        assert store.delete("no-such-id") is False

    def test_search(self, store: ContactStore) -> None:
        store.add("Grace Hopper", organization="Navy", notes="pioneer of computing")
        store.add("Alan Turing", organization="Bletchley", notes="codebreaker")
        results = store.search("Navy")
        assert len(results) == 1
        assert results[0]["name"] == "Grace Hopper"

    def test_search_notes(self, store: ContactStore) -> None:
        store.add("Test Person", notes="loves hiking")
        results = store.search("hiking")
        assert len(results) == 1

    def test_list_all(self, store: ContactStore) -> None:
        store.add("A", relationship="friend")
        store.add("B", relationship="colleague")
        store.add("C", relationship="friend")
        assert len(store.list_all()) == 3
        assert len(store.list_all(relationship="friend")) == 2

    def test_append_notes(self, store: ContactStore) -> None:
        c = store.add("Hank Hill", notes="initial note")
        result = store.append_notes(c["id"], "met at conference")
        assert result is not None
        assert "initial note" in result["notes"]
        assert "met at conference" in result["notes"]
        # Verify timestamp prefix
        assert "[" in result["notes"]

    def test_append_notes_empty_initial(self, store: ContactStore) -> None:
        c = store.add("Iris West")
        result = store.append_notes(c["id"], "first interaction")
        assert result is not None
        assert "first interaction" in result["notes"]

    def test_append_notes_nonexistent(self, store: ContactStore) -> None:
        assert store.append_notes("no-such-id", "text") is None


# ---------------------------------------------------------------------------
# Tool handler tests
# ---------------------------------------------------------------------------


class TestContactsToolHandler:
    @pytest.mark.asyncio
    async def test_add_contact(self, store: ContactStore) -> None:
        result = await contacts_tool({
            "action": "add",
            "name": "John Smith",
            "relationship": "colleague",
            "organization": "Acme Corp",
        })
        assert "Contact added" in result
        assert "John Smith" in result

    @pytest.mark.asyncio
    async def test_add_missing_name(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "add"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_get_by_id(self, store: ContactStore) -> None:
        c = store.add("Jane Doe")
        result = await contacts_tool({"action": "get", "contact_id": c["id"]})
        assert "Jane Doe" in result

    @pytest.mark.asyncio
    async def test_get_by_name(self, store: ContactStore) -> None:
        store.add("Jane Doe")
        result = await contacts_tool({"action": "get", "name": "Jane"})
        assert "Jane Doe" in result

    @pytest.mark.asyncio
    async def test_get_not_found(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "get", "contact_id": "bad-id"})
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_get_no_params(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "get"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_update_contact(self, store: ContactStore) -> None:
        c = store.add("Update Me")
        result = await contacts_tool({
            "action": "update",
            "contact_id": c["id"],
            "organization": "NewCorp",
        })
        assert "Contact updated" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "update", "name": "X"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_delete_contact(self, store: ContactStore) -> None:
        c = store.add("Delete Me")
        result = await contacts_tool({"action": "delete", "contact_id": c["id"]})
        assert "deleted" in result

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "delete"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_search(self, store: ContactStore) -> None:
        store.add("Searchable Sam", organization="FindMe Inc")
        result = await contacts_tool({"action": "search", "query": "FindMe"})
        assert "Searchable Sam" in result

    @pytest.mark.asyncio
    async def test_search_no_results(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "search", "query": "zzzzz"})
        assert "No contacts" in result

    @pytest.mark.asyncio
    async def test_search_missing_query(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "search"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_list_all(self, store: ContactStore) -> None:
        store.add("A Person", relationship="friend")
        store.add("B Person", relationship="colleague")
        result = await contacts_tool({"action": "list"})
        assert "A Person" in result
        assert "B Person" in result

    @pytest.mark.asyncio
    async def test_list_filtered(self, store: ContactStore) -> None:
        store.add("Friend One", relationship="friend")
        store.add("Colleague One", relationship="colleague")
        result = await contacts_tool({"action": "list", "relationship": "friend"})
        assert "Friend One" in result
        assert "Colleague One" not in result

    @pytest.mark.asyncio
    async def test_list_empty(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "list"})
        assert "No contacts" in result

    @pytest.mark.asyncio
    async def test_append_notes(self, store: ContactStore) -> None:
        c = store.add("Notes Person")
        result = await contacts_tool({
            "action": "append_notes",
            "contact_id": c["id"],
            "notes": "had coffee together",
        })
        assert "Notes updated" in result

    @pytest.mark.asyncio
    async def test_append_notes_missing_id(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "append_notes", "notes": "text"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_append_notes_missing_notes(self, store: ContactStore) -> None:
        c = store.add("No Notes")
        result = await contacts_tool({"action": "append_notes", "contact_id": c["id"]})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, store: ContactStore) -> None:
        result = await contacts_tool({"action": "explode"})
        assert "Unknown" in result
