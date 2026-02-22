"""Tests for the plugin system."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from assistant.plugins.types import (
    BasePlugin,
    HookType,
    Plugin,
    PluginContext,
    PluginManifest,
    PluginSkillDef,
    PluginToolDef,
)
from assistant.plugins.manager import PluginManager
from assistant.plugins.hooks import HookDispatcher


# --- Test plugin for use in tests ---


class MockPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(
            PluginManifest(
                name="mock",
                version="1.0.0",
                description="Mock plugin for testing",
            )
        )
        self.initialized = False
        self.started = False
        self.stopped = False

    async def initialize(self, context: PluginContext) -> None:
        self.initialized = True

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    def get_tools(self) -> list[PluginToolDef]:
        async def greet(params: dict) -> str:
            return f"Hello, {params.get('name', 'world')}!"

        return [
            PluginToolDef(
                name="greet",
                description="Greet someone",
                input_schema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
                handler=greet,
                permission_category="read",
            )
        ]

    def get_skills(self) -> list[PluginSkillDef]:
        return [
            PluginSkillDef(name="mock_skill", content="This is a mock skill.")
        ]

    def get_hooks(self) -> dict[HookType, any]:
        async def on_pre_message(**kwargs):
            msg = kwargs.get("message", "")
            return f"[mock] {msg}"

        return {HookType.PRE_MESSAGE: on_pre_message}


# --- Tests ---


class TestPluginTypes:
    def test_manifest(self):
        m = PluginManifest(name="test", version="2.0.0", description="A test")
        assert m.name == "test"
        assert m.version == "2.0.0"

    def test_base_plugin_defaults(self):
        p = BasePlugin(PluginManifest(name="base"))
        assert p.manifest.name == "base"
        assert p.get_tools() == []
        assert p.get_skills() == []
        assert p.get_hooks() == {}

    def test_plugin_protocol(self):
        p = MockPlugin()
        assert isinstance(p, Plugin)

    def test_tool_def(self):
        t = PluginToolDef(
            name="test_tool",
            description="A tool",
            permission_category="read",
        )
        assert t.name == "test_tool"
        assert t.permission_category == "read"


class TestPluginManager:
    @pytest.fixture
    def plugins_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "plugins"
        d.mkdir()
        return d

    @pytest.fixture
    def context(self, tmp_path: Path) -> PluginContext:
        return PluginContext(data_dir=tmp_path, settings=None)

    @pytest.mark.asyncio
    async def test_discover_empty_dir(self, plugins_dir: Path, context: PluginContext):
        pm = PluginManager(plugins_dir, context)
        await pm.discover_and_load()
        assert len(pm.plugins) == 0

    @pytest.mark.asyncio
    async def test_discover_creates_dir(self, tmp_path: Path, context: PluginContext):
        missing = tmp_path / "nonexistent_plugins"
        pm = PluginManager(missing, context)
        await pm.discover_and_load()
        assert missing.exists()

    @pytest.mark.asyncio
    async def test_load_plugin_file(self, plugins_dir: Path, context: PluginContext):
        # Write a simple plugin file
        plugin_code = '''
from assistant.plugins.types import BasePlugin, PluginManifest, PluginToolDef

class TestPlugin(BasePlugin):
    def __init__(self):
        super().__init__(PluginManifest(name="test_file", version="0.1.0", description="File test"))

    def get_tools(self):
        async def noop(params):
            return "ok"
        return [PluginToolDef(name="noop", description="No-op", handler=noop)]

def create_plugin():
    return TestPlugin()
'''
        (plugins_dir / "test_file.py").write_text(plugin_code)

        pm = PluginManager(plugins_dir, context)
        await pm.discover_and_load()
        assert "test_file" in pm.plugins
        assert len(pm.get_all_tools()) == 1
        assert pm.get_all_tools()[0].name == "noop"

    @pytest.mark.asyncio
    async def test_start_stop(self, plugins_dir: Path, context: PluginContext):
        pm = PluginManager(plugins_dir, context)
        # Manually inject a mock plugin
        mock = MockPlugin()
        await mock.initialize(context)
        pm._plugins["mock"] = mock

        await pm.start_all()
        assert mock.started

        await pm.stop_all()
        assert mock.stopped

    @pytest.mark.asyncio
    async def test_get_all_skills(self, plugins_dir: Path, context: PluginContext):
        pm = PluginManager(plugins_dir, context)
        mock = MockPlugin()
        await mock.initialize(context)
        pm._plugins["mock"] = mock

        skills = pm.get_all_skills()
        assert len(skills) == 1
        assert skills[0].name == "mock_skill"

    @pytest.mark.asyncio
    async def test_get_all_hooks(self, plugins_dir: Path, context: PluginContext):
        pm = PluginManager(plugins_dir, context)
        mock = MockPlugin()
        await mock.initialize(context)
        pm._plugins["mock"] = mock

        hooks = pm.get_all_hooks()
        assert len(hooks[HookType.PRE_MESSAGE.value]) == 1

    @pytest.mark.asyncio
    async def test_skip_underscore_files(self, plugins_dir: Path, context: PluginContext):
        (plugins_dir / "__init__.py").write_text("# skip")
        (plugins_dir / "_internal.py").write_text("# skip")
        pm = PluginManager(plugins_dir, context)
        await pm.discover_and_load()
        assert len(pm.plugins) == 0

    @pytest.mark.asyncio
    async def test_bad_plugin_isolated(self, plugins_dir: Path, context: PluginContext):
        (plugins_dir / "broken.py").write_text("raise RuntimeError('boom')")
        pm = PluginManager(plugins_dir, context)
        await pm.discover_and_load()
        assert "broken" not in pm.plugins


class TestHookDispatcher:
    @pytest.mark.asyncio
    async def test_pre_message_hook(self):
        pm = PluginManager.__new__(PluginManager)
        pm._plugins = {}
        pm._plugins_dir = Path("/tmp")

        mock = MockPlugin()
        await mock.initialize(PluginContext(data_dir=Path("/tmp"), settings=None))
        pm._plugins["mock"] = mock

        dispatcher = HookDispatcher(pm)
        result = await dispatcher.pre_message("hello")
        assert result == "[mock] hello"

    @pytest.mark.asyncio
    async def test_post_message_hook_no_error(self):
        pm = PluginManager.__new__(PluginManager)
        pm._plugins = {}
        pm._plugins_dir = Path("/tmp")

        dispatcher = HookDispatcher(pm)
        # Should not raise
        await dispatcher.post_message("hello", "world")

    @pytest.mark.asyncio
    async def test_session_hooks(self):
        pm = PluginManager.__new__(PluginManager)
        pm._plugins = {}
        pm._plugins_dir = Path("/tmp")

        dispatcher = HookDispatcher(pm)
        await dispatcher.session_start(session_id="test")
        await dispatcher.session_end(session_id="test")


class TestToolRegistryUnregister:
    def test_unregister(self):
        from unittest.mock import AsyncMock
        from assistant.core.logging import AuditLogger
        from assistant.gateway.permissions import PermissionManager
        from assistant.tools.registry import ToolRegistry

        pm = PermissionManager(AsyncMock(return_value=True))
        audit = AuditLogger.__new__(AuditLogger)
        audit._log_path = Path("/dev/null")

        registry = ToolRegistry(pm, audit)
        registry.register("test_tool", "Test", {"type": "object"}, AsyncMock())

        assert any(d["name"] == "test_tool" for d in registry.definitions)
        assert registry.unregister("test_tool")
        assert not any(d["name"] == "test_tool" for d in registry.definitions)
        assert not registry.unregister("nonexistent")


class TestPermissionManagerPluginCategory:
    def test_register_tool_category(self):
        from unittest.mock import AsyncMock
        from assistant.gateway.permissions import ActionCategory, PermissionManager

        pm = PermissionManager(AsyncMock())
        pm.register_tool_category("my_tool", "read")

        req = pm.classify_tool_call("my_tool", {})
        assert req.action_category == ActionCategory.READ
        assert not req.requires_approval

    def test_register_tool_category_write(self):
        from unittest.mock import AsyncMock
        from assistant.gateway.permissions import ActionCategory, PermissionManager

        pm = PermissionManager(AsyncMock())
        pm.register_tool_category("dangerous_tool", ActionCategory.DELETE)

        req = pm.classify_tool_call("dangerous_tool", {})
        assert req.action_category == ActionCategory.DELETE
        assert req.requires_approval


class TestMemoryManagerPluginSkills:
    def test_add_remove_plugin_skill(self, tmp_data_dir: Path):
        from assistant.memory.manager import MemoryManager

        mm = MemoryManager(
            identity_path=tmp_data_dir / "memory" / "IDENTITY.md",
            memory_path=tmp_data_dir / "memory" / "MEMORY.md",
            daily_log_dir=tmp_data_dir / "memory" / "daily",
            search_db_path=tmp_data_dir / "db" / "search.db",
        )

        mm.add_plugin_skill("test_skill", "Test skill content")
        prompt = mm.get_system_prompt()
        assert "test_skill" in prompt
        assert "Test skill content" in prompt

        mm.remove_plugin_skill("test_skill")
        prompt2 = mm.get_system_prompt()
        assert "test_skill" not in prompt2
