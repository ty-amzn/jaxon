"""Tests for the thread persistence system."""

from pathlib import Path

from assistant.gateway.thread_store import ThreadStore, Thread


class TestThreadStore:
    """Tests for the thread persistence system."""

    def test_create_and_save_thread(self, tmp_path: Path):
        """Test creating and saving a thread."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("Test Thread")
        thread.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        store.save(thread)

        # Verify it was saved
        loaded = store.load(thread.id)
        assert loaded is not None
        assert loaded.name == "Test Thread"
        assert len(loaded.messages) == 2

    def test_list_threads(self, tmp_path: Path):
        """Test listing saved threads."""
        store = ThreadStore(tmp_path)

        thread1 = store.create_thread("Thread 1")
        thread2 = store.create_thread("Thread 2")
        store.save(thread1)
        store.save(thread2)

        threads = store.list_threads()
        assert len(threads) == 2

    def test_load_by_name(self, tmp_path: Path):
        """Test loading a thread by name."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("My Conversation")
        store.save(thread)

        loaded = store.load_by_name("My Conversation")
        assert loaded is not None
        assert loaded.name == "My Conversation"

    def test_delete_thread(self, tmp_path: Path):
        """Test deleting a thread."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("To Delete")
        store.save(thread)

        assert store.load(thread.id) is not None
        assert store.delete(thread.id) is True
        assert store.load(thread.id) is None

    def test_export_thread_json(self, tmp_path: Path):
        """Test exporting a thread as JSON."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("Export Test")
        thread.messages = [{"role": "user", "content": "Test"}]
        store.save(thread)

        exported = store.export_thread(thread, format="json")
        assert "Export Test" in exported
        assert "Test" in exported

    def test_export_thread_markdown(self, tmp_path: Path):
        """Test exporting a thread as Markdown."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("MD Export")
        thread.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "World"},
        ]
        store.save(thread)

        exported = store.export_thread(thread, format="markdown")
        assert "# MD Export" in exported
        assert "**User:**" in exported
        assert "**Assistant:**" in exported
