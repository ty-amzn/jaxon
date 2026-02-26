"""Tests for the multi-agent orchestration system."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from assistant.agents.background import (
    BackgroundTaskManager,
    TaskStatus,
    _auto_approve,
    current_delivery,
    current_review_delivery,
)
from assistant.agents.types import AgentDef, AgentResult
from assistant.agents.loader import AgentLoader
from assistant.agents.runner import AgentRunner
from assistant.agents.orchestrator import Orchestrator
from assistant.llm.types import StreamEvent, StreamEventType


class TestAgentTypes:
    def test_agent_def_defaults(self):
        agent = AgentDef(name="test", description="A test agent")
        assert agent.name == "test"
        assert agent.allowed_tools == []
        assert agent.denied_tools == []
        assert agent.max_tool_rounds == 5
        assert agent.model == ""
        assert agent.can_delegate is False

    def test_agent_result_success(self):
        result = AgentResult(agent_name="test", response="done")
        assert result.success
        assert result.response == "done"

    def test_agent_result_error(self):
        result = AgentResult(agent_name="test", response="", error="failed")
        assert not result.success
        assert result.error == "failed"


class TestAgentLoader:
    @pytest.fixture
    def agents_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "agents"
        d.mkdir()
        return d

    def test_load_empty_dir(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.load_all()
        assert len(agents) == 0

    def test_creates_missing_dir(self, tmp_path: Path):
        missing = tmp_path / "nonexistent_agents"
        loader = AgentLoader(missing)
        loader.load_all()
        assert missing.exists()

    def test_load_yaml(self, agents_dir: Path):
        data = {
            "name": "test_agent",
            "description": "A test agent",
            "system_prompt": "You are a test agent.",
            "allowed_tools": ["read_file", "shell_exec"],
            "max_tool_rounds": 3,
        }
        (agents_dir / "test_agent.yaml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        agents = loader.load_all()
        assert "test_agent" in agents
        assert agents["test_agent"].description == "A test agent"
        assert agents["test_agent"].allowed_tools == ["read_file", "shell_exec"]
        assert agents["test_agent"].max_tool_rounds == 3

    def test_load_yml_extension(self, agents_dir: Path):
        data = {"name": "yml_agent", "description": "YML agent"}
        (agents_dir / "yml_agent.yml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        agents = loader.load_all()
        assert "yml_agent" in agents

    def test_get_agent(self, agents_dir: Path):
        data = {"name": "lookup", "description": "Lookup test"}
        (agents_dir / "lookup.yaml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        agent = loader.get_agent("lookup")
        assert agent is not None
        assert agent.name == "lookup"
        assert loader.get_agent("nonexistent") is None

    def test_list_agents(self, agents_dir: Path):
        for i in range(3):
            data = {"name": f"agent_{i}", "description": f"Agent {i}"}
            (agents_dir / f"agent_{i}.yaml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        agents = loader.list_agents()
        assert len(agents) == 3

    def test_reload(self, agents_dir: Path):
        data = {"name": "initial", "description": "Initial"}
        (agents_dir / "initial.yaml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        assert len(loader.list_agents()) == 1

        # Add another agent
        data2 = {"name": "added", "description": "Added"}
        (agents_dir / "added.yaml").write_text(yaml.dump(data2))

        loader.reload()
        assert len(loader.list_agents()) == 2

    def test_load_can_delegate(self, agents_dir: Path):
        data = {
            "name": "coordinator",
            "description": "Coordinator",
            "can_delegate": True,
            "allowed_tools": ["delegate_to_agent"],
        }
        (agents_dir / "coordinator.yaml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        agents = loader.load_all()
        assert agents["coordinator"].can_delegate is True

    def test_load_can_delegate_defaults_false(self, agents_dir: Path):
        data = {"name": "basic", "description": "Basic agent"}
        (agents_dir / "basic.yaml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        agents = loader.load_all()
        assert agents["basic"].can_delegate is False

    def test_invalid_yaml_skipped(self, agents_dir: Path):
        (agents_dir / "bad.yaml").write_text("not: [valid: yaml: {")

        loader = AgentLoader(agents_dir)
        agents = loader.load_all()
        # Should not crash, just skip
        assert "bad" not in agents


class TestAgentRunner:
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that yields a simple text response."""
        llm = AsyncMock()

        async def mock_stream(**kwargs):
            yield StreamEvent(type=StreamEventType.TEXT_DELTA, text="Agent response")
            yield StreamEvent(type=StreamEventType.MESSAGE_COMPLETE, text="Agent response")

        llm.stream_with_tool_loop = mock_stream
        return llm

    @pytest.fixture
    def mock_registry(self):
        registry = MagicMock()
        registry.definitions = [
            {"name": "read_file", "description": "Read a file", "input_schema": {}},
            {"name": "write_file", "description": "Write a file", "input_schema": {}},
            {"name": "shell_exec", "description": "Execute shell", "input_schema": {}},
        ]
        return registry

    @pytest.mark.asyncio
    async def test_run_basic(self, mock_llm, mock_registry):
        runner = AgentRunner(mock_llm, mock_registry)
        agent = AgentDef(name="test", description="Test agent")

        result = await runner.run(agent, "Do something")
        assert result.success
        assert result.response == "Agent response"
        assert result.agent_name == "test"

    def test_filter_tools_allowed(self, mock_registry):
        runner = AgentRunner(AsyncMock(), mock_registry)
        agent = AgentDef(
            name="test",
            description="Test",
            allowed_tools=["read_file"],
        )

        tools = runner._filter_tools(agent)
        assert len(tools) == 1
        assert tools[0]["name"] == "read_file"

    def test_filter_tools_denied(self, mock_registry):
        runner = AgentRunner(AsyncMock(), mock_registry)
        agent = AgentDef(
            name="test",
            description="Test",
            denied_tools=["shell_exec"],
        )

        tools = runner._filter_tools(agent)
        names = [t["name"] for t in tools]
        assert "shell_exec" not in names
        assert "read_file" in names
        assert "write_file" in names

    def test_filter_tools_removes_delegation(self, mock_registry):
        mock_registry.definitions.append(
            {"name": "delegate_to_agent", "description": "Delegate", "input_schema": {}}
        )
        runner = AgentRunner(AsyncMock(), mock_registry)
        agent = AgentDef(name="test", description="Test")

        tools = runner._filter_tools(agent)
        names = [t["name"] for t in tools]
        assert "delegate_to_agent" not in names

    def test_filter_tools_keeps_delegation_when_can_delegate(self, mock_registry):
        delegation_tools = [
            {"name": "delegate_to_agent", "description": "Delegate", "input_schema": {}},
            {"name": "delegate_parallel", "description": "Parallel delegate", "input_schema": {}},
            {"name": "list_agents", "description": "List agents", "input_schema": {}},
        ]
        mock_registry.definitions.extend(delegation_tools)
        runner = AgentRunner(AsyncMock(), mock_registry)
        agent = AgentDef(name="coordinator", description="Test", can_delegate=True)

        tools = runner._filter_tools(agent)
        names = [t["name"] for t in tools]
        assert "delegate_to_agent" in names
        assert "delegate_parallel" in names
        assert "list_agents" in names

    @pytest.mark.asyncio
    async def test_run_error(self, mock_registry):
        llm = AsyncMock()

        async def error_stream(**kwargs):
            yield StreamEvent(type=StreamEventType.ERROR, error="LLM error")

        llm.stream_with_tool_loop = error_stream

        runner = AgentRunner(llm, mock_registry)
        agent = AgentDef(name="test", description="Test")

        result = await runner.run(agent, "Do something")
        assert not result.success
        assert result.error == "LLM error"


class TestOrchestrator:
    @pytest.fixture
    def orchestrator(self, tmp_path: Path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        data = {
            "name": "test_agent",
            "description": "A test agent",
            "allowed_tools": ["read_file"],
        }
        (agents_dir / "test_agent.yaml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        loader.load_all()

        mock_llm = AsyncMock()

        async def mock_stream(**kwargs):
            yield StreamEvent(type=StreamEventType.MESSAGE_COMPLETE, text="Result from agent")

        mock_llm.stream_with_tool_loop = mock_stream

        mock_registry = MagicMock()
        mock_registry.definitions = [
            {"name": "read_file", "description": "Read", "input_schema": {}},
        ]

        runner = AgentRunner(mock_llm, mock_registry)

        from assistant.memory.manager import MemoryManager
        memory = MemoryManager(
            identity_path=tmp_path / "memory" / "IDENTITY.md",
            memory_path=tmp_path / "memory" / "MEMORY.md",
            daily_log_dir=tmp_path / "memory" / "daily",
            search_db_path=tmp_path / "db" / "search.db",
        )
        # Create required files
        (tmp_path / "memory").mkdir(exist_ok=True)
        (tmp_path / "memory" / "daily").mkdir(parents=True, exist_ok=True)
        (tmp_path / "memory" / "IDENTITY.md").write_text("Test identity")
        (tmp_path / "memory" / "MEMORY.md").write_text("Test memory")
        (tmp_path / "db").mkdir(exist_ok=True)

        return Orchestrator(loader, runner, memory)

    @pytest.mark.asyncio
    async def test_delegate(self, orchestrator):
        result = await orchestrator.delegate("test_agent", "Do something")
        assert result.success
        assert result.response == "Result from agent"

    @pytest.mark.asyncio
    async def test_delegate_unknown_agent(self, orchestrator):
        result = await orchestrator.delegate("nonexistent", "Do something")
        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_delegate_parallel(self, orchestrator):
        results = await orchestrator.delegate_parallel([
            {"agent_name": "test_agent", "task": "Task 1"},
            {"agent_name": "test_agent", "task": "Task 2"},
        ])
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_tool_definitions(self, orchestrator):
        defs = orchestrator.get_tool_definitions()
        names = [d["name"] for d in defs]
        assert "list_agents" in names
        assert "delegate_to_agent" in names
        assert "delegate_parallel" in names

    @pytest.mark.asyncio
    async def test_tool_handlers(self, orchestrator):
        handlers = orchestrator.get_tool_handlers()
        assert "list_agents" in handlers
        assert "delegate_to_agent" in handlers
        assert "delegate_parallel" in handlers

        # Test list_agents handler
        result = await handlers["list_agents"]({})
        assert "test_agent" in result

        # Test delegate handler
        result = await handlers["delegate_to_agent"]({
            "agent_name": "test_agent",
            "task": "Do something",
        })
        assert "Result from agent" in result

    @pytest.mark.asyncio
    async def test_depth_guard_blocks_at_max(self, orchestrator):
        from assistant.agents.orchestrator import _delegation_depth_var, MAX_DELEGATION_DEPTH
        _delegation_depth_var.set(MAX_DELEGATION_DEPTH)
        try:
            result = await orchestrator.delegate("test_agent", "Do something")
            assert not result.success
            assert "depth" in result.error.lower()
        finally:
            _delegation_depth_var.set(0)

    @pytest.mark.asyncio
    async def test_depth_counter_resets_after_delegate(self, orchestrator):
        from assistant.agents.orchestrator import _delegation_depth_var
        assert _delegation_depth_var.get() == 0
        await orchestrator.delegate("test_agent", "Do something")
        assert _delegation_depth_var.get() == 0

    def test_config_settings(self):
        from assistant.core.config import Settings
        s = Settings(anthropic_api_key="test", _env_file=None)
        assert s.plugins_enabled is False
        assert s.agents_enabled is False
        assert s.plugins_dir == s.data_dir / "plugins"
        assert s.agents_dir == s.data_dir / "agents"


class TestBackgroundTaskManager:
    def test_create_task(self):
        mgr = BackgroundTaskManager()
        bt = mgr.create("research", "Find papers on X")
        assert len(bt.id) == 8
        assert bt.agent_name == "research"
        assert bt.status == TaskStatus.PENDING

    def test_get_task(self):
        mgr = BackgroundTaskManager()
        bt = mgr.create("research", "Find papers")
        assert mgr.get(bt.id) is bt
        assert mgr.get("nonexistent") is None

    def test_list_all(self):
        mgr = BackgroundTaskManager()
        bt1 = mgr.create("a1", "task1")
        bt2 = mgr.create("a2", "task2")
        tasks = mgr.list_all()
        assert len(tasks) == 2
        assert tasks[0] is bt1
        assert tasks[1] is bt2

    def test_bounded_eviction(self):
        mgr = BackgroundTaskManager(maxlen=3)
        ids = [mgr.create("agent", f"task {i}").id for i in range(5)]
        # Should only keep last 3
        assert len(mgr.list_all()) == 3
        assert mgr.get(ids[0]) is None
        assert mgr.get(ids[1]) is None
        assert mgr.get(ids[2]) is not None
        assert mgr.get(ids[3]) is not None
        assert mgr.get(ids[4]) is not None


class TestAutoApprove:
    @pytest.mark.asyncio
    async def test_auto_approve_always_true(self):
        from assistant.gateway.permissions import PermissionRequest, ActionCategory
        req = PermissionRequest(
            tool_name="shell_exec",
            action_category=ActionCategory.WRITE,
            details={"command": "rm -rf /"},
            description="dangerous command",
        )
        assert await _auto_approve(req) is True


class TestBackgroundDelegation:
    @pytest.fixture
    def bg_orchestrator(self, tmp_path: Path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        data = {
            "name": "researcher",
            "description": "Research agent",
            "allowed_tools": ["web_fetch"],
        }
        (agents_dir / "researcher.yaml").write_text(yaml.dump(data))

        loader = AgentLoader(agents_dir)
        loader.load_all()

        mock_llm = AsyncMock()

        async def mock_stream(**kwargs):
            yield StreamEvent(type=StreamEventType.MESSAGE_COMPLETE, text="Research result: found 3 papers")

        mock_llm.stream_with_tool_loop = mock_stream

        mock_registry = MagicMock()
        mock_registry.definitions = [
            {"name": "web_fetch", "description": "Fetch", "input_schema": {}},
        ]
        mock_registry.execute = AsyncMock()

        runner = AgentRunner(mock_llm, mock_registry)

        from assistant.memory.manager import MemoryManager
        (tmp_path / "memory").mkdir(exist_ok=True)
        (tmp_path / "memory" / "daily").mkdir(parents=True, exist_ok=True)
        (tmp_path / "memory" / "IDENTITY.md").write_text("Test identity")
        (tmp_path / "memory" / "MEMORY.md").write_text("Test memory")
        (tmp_path / "db").mkdir(exist_ok=True)

        memory = MemoryManager(
            identity_path=tmp_path / "memory" / "IDENTITY.md",
            memory_path=tmp_path / "memory" / "MEMORY.md",
            daily_log_dir=tmp_path / "memory" / "daily",
            search_db_path=tmp_path / "db" / "search.db",
        )

        bg_manager = BackgroundTaskManager()
        return Orchestrator(loader, runner, memory, bg_manager=bg_manager)

    @pytest.mark.asyncio
    async def test_background_returns_task_id(self, bg_orchestrator):
        handlers = bg_orchestrator.get_tool_handlers()
        result = await handlers["delegate_to_agent"]({
            "agent_name": "researcher",
            "task": "Find papers on transformers",
            "background": True,
        })
        assert "task_id=" in result
        # Extract task ID
        task_id = result.split("task_id=")[1].rstrip(")")
        assert len(task_id) == 8

    @pytest.mark.asyncio
    async def test_background_delivers_result(self, bg_orchestrator):
        delivered = []

        async def mock_deliver(text: str) -> None:
            delivered.append(text)

        # Set delivery callback via contextvar
        token = current_delivery.set(mock_deliver)
        try:
            handlers = bg_orchestrator.get_tool_handlers()
            result = await handlers["delegate_to_agent"]({
                "agent_name": "researcher",
                "task": "Find papers",
                "background": True,
            })
            # Wait for background task to complete
            await asyncio.sleep(0.5)
        finally:
            current_delivery.reset(token)

        assert len(delivered) == 1
        assert "Research result" in delivered[0]

    @pytest.mark.asyncio
    async def test_task_status_returns_result(self, bg_orchestrator):
        token = current_delivery.set(None)
        try:
            handlers = bg_orchestrator.get_tool_handlers()
            result = await handlers["delegate_to_agent"]({
                "agent_name": "researcher",
                "task": "Find papers",
                "background": True,
            })
            task_id = result.split("task_id=")[1].rstrip(")")

            # Wait for completion
            await asyncio.sleep(0.5)

            status = await handlers["task_status"]({"task_id": task_id})
            assert "done" in status.lower()
            assert "Research result" in status
        finally:
            current_delivery.reset(token)

    def test_tool_definitions_include_task_status(self, bg_orchestrator):
        defs = bg_orchestrator.get_tool_definitions()
        names = [d["name"] for d in defs]
        assert "task_status" in names

    def test_tool_definitions_include_background_param(self, bg_orchestrator):
        defs = bg_orchestrator.get_tool_definitions()
        delegate_def = next(d for d in defs if d["name"] == "delegate_to_agent")
        assert "background" in delegate_def["input_schema"]["properties"]

    @pytest.mark.asyncio
    async def test_background_uses_review_delivery(self, bg_orchestrator):
        """When review delivery is set, results route through it instead of direct delivery."""
        reviewed = []
        direct = []

        async def mock_review(raw_result: str, agent_name: str) -> None:
            reviewed.append((raw_result, agent_name))

        async def mock_direct(text: str) -> None:
            direct.append(text)

        token_d = current_delivery.set(mock_direct)
        token_r = current_review_delivery.set(mock_review)
        try:
            handlers = bg_orchestrator.get_tool_handlers()
            await handlers["delegate_to_agent"]({
                "agent_name": "researcher",
                "task": "Find papers",
                "background": True,
            })
            await asyncio.sleep(0.5)
        finally:
            current_delivery.reset(token_d)
            current_review_delivery.reset(token_r)

        # Review delivery was used, not direct
        assert len(reviewed) == 1
        assert "Research result" in reviewed[0][0]
        assert reviewed[0][1] == "researcher"
        assert len(direct) == 0

    @pytest.mark.asyncio
    async def test_review_delivery_fallback_on_error(self, bg_orchestrator):
        """If review delivery fails, falls back to direct delivery."""
        direct = []

        async def failing_review(raw_result: str, agent_name: str) -> None:
            raise RuntimeError("review failed")

        async def mock_direct(text: str) -> None:
            direct.append(text)

        token_d = current_delivery.set(mock_direct)
        token_r = current_review_delivery.set(failing_review)
        try:
            handlers = bg_orchestrator.get_tool_handlers()
            await handlers["delegate_to_agent"]({
                "agent_name": "researcher",
                "task": "Find papers",
                "background": True,
            })
            await asyncio.sleep(0.5)
        finally:
            current_delivery.reset(token_d)
            current_review_delivery.reset(token_r)

        # Fell back to direct delivery
        assert len(direct) == 1
        assert "Research result" in direct[0]

    @pytest.mark.asyncio
    async def test_silent_skips_review_delivery(self, bg_orchestrator):
        """Silent tasks skip both review and direct delivery."""
        reviewed = []
        direct = []

        async def mock_review(raw_result: str, agent_name: str) -> None:
            reviewed.append(raw_result)

        async def mock_direct(text: str) -> None:
            direct.append(text)

        token_d = current_delivery.set(mock_direct)
        token_r = current_review_delivery.set(mock_review)
        try:
            handlers = bg_orchestrator.get_tool_handlers()
            await handlers["delegate_to_agent"]({
                "agent_name": "researcher",
                "task": "Find papers",
                "background": True,
                "silent": True,
            })
            await asyncio.sleep(0.5)
        finally:
            current_delivery.reset(token_d)
            current_review_delivery.reset(token_r)

        assert len(reviewed) == 0
        assert len(direct) == 0

    @pytest.mark.asyncio
    async def test_foreground_still_works(self, bg_orchestrator):
        handlers = bg_orchestrator.get_tool_handlers()
        result = await handlers["delegate_to_agent"]({
            "agent_name": "researcher",
            "task": "Find papers",
        })
        assert "Research result" in result
