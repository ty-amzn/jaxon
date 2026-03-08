"""Tests for workflow definition, runner, and manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from assistant.scheduler.workflow import WorkflowDefinition, WorkflowRunner, WorkflowManager


# --- WorkflowDefinition ---


def test_workflow_definition_from_dict():
    """WorkflowDefinition can be created from a dict."""
    data = {
        "name": "test-workflow",
        "description": "A test workflow",
        "trigger": "manual",
        "steps": [
            {"name": "step1", "tool": "shell_exec", "args": {"command": "echo hello"}},
            {"name": "step2", "tool": "read_file", "args": {"path": "/tmp/test"}, "requires_approval": True},
        ],
    }
    wf = WorkflowDefinition.from_dict(data)

    assert wf.name == "test-workflow"
    assert wf.description == "A test workflow"
    assert wf.trigger == "manual"
    assert len(wf.steps) == 2
    assert wf.steps[0].tool == "shell_exec"
    assert wf.steps[0].requires_approval is False
    assert wf.steps[1].requires_approval is True
    assert wf.enabled is True


def test_workflow_definition_from_yaml(tmp_path: Path):
    """WorkflowDefinition can be loaded from a YAML file."""
    yaml_content = """
name: yaml-workflow
description: Loaded from YAML
trigger: webhook
steps:
  - name: greet
    tool: shell_exec
    args:
      command: echo hi
"""
    yaml_path = tmp_path / "test.yaml"
    yaml_path.write_text(yaml_content)

    wf = WorkflowDefinition.from_yaml(yaml_path)
    assert wf.name == "yaml-workflow"
    assert wf.trigger == "webhook"
    assert len(wf.steps) == 1
    assert wf.steps[0].args == {"command": "echo hi"}


def test_workflow_definition_webhook_key():
    """WorkflowDefinition parses webhook_key from YAML."""
    data = {
        "name": "keyed-workflow",
        "trigger": "webhook",
        "webhook_key": "per-workflow-secret-123",
        "steps": [{"name": "s1", "tool": "echo"}],
    }
    wf = WorkflowDefinition.from_dict(data)
    assert wf.webhook_key == "per-workflow-secret-123"


def test_workflow_definition_no_webhook_key():
    """WorkflowDefinition defaults to empty webhook_key."""
    data = {
        "name": "no-key",
        "trigger": "webhook",
        "steps": [{"name": "s1", "tool": "echo"}],
    }
    wf = WorkflowDefinition.from_dict(data)
    assert wf.webhook_key == ""


def test_workflow_definition_parses_prompt():
    """WorkflowDefinition parses prompt field from dict."""
    data = {
        "name": "prompt-wf",
        "trigger": "webhook",
        "prompt": "Hello from {{name}}",
    }
    wf = WorkflowDefinition.from_dict(data)
    assert wf.prompt == "Hello from {{name}}"
    assert wf.steps == []


def test_workflow_definition_prompt_defaults_empty():
    """WorkflowDefinition defaults prompt to empty string."""
    data = {
        "name": "no-prompt",
        "trigger": "webhook",
        "steps": [{"name": "s1", "tool": "echo"}],
    }
    wf = WorkflowDefinition.from_dict(data)
    assert wf.prompt == ""


# --- WorkflowRunner ---


@pytest.mark.asyncio
async def test_workflow_runner_executes_steps():
    """WorkflowRunner executes all steps and collects results."""
    outputs = []

    async def mock_executor(tool: str, args: dict) -> str:
        output = f"{tool}:{args}"
        outputs.append(output)
        return output

    runner = WorkflowRunner(tool_executor=mock_executor)
    wf = WorkflowDefinition.from_dict({
        "name": "test",
        "steps": [
            {"name": "s1", "tool": "tool_a", "args": {"key": "val1"}},
            {"name": "s2", "tool": "tool_b", "args": {"key": "val2"}},
        ],
    })

    results = await runner.run(wf)
    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[1]["status"] == "success"
    assert len(outputs) == 2


@pytest.mark.asyncio
async def test_workflow_runner_stops_on_error():
    """WorkflowRunner stops execution on error."""
    async def failing_executor(tool: str, args: dict) -> str:
        raise RuntimeError("boom")

    runner = WorkflowRunner(tool_executor=failing_executor)
    wf = WorkflowDefinition.from_dict({
        "name": "fail-test",
        "steps": [
            {"name": "s1", "tool": "tool_a"},
            {"name": "s2", "tool": "tool_b"},
        ],
    })

    results = await runner.run(wf)
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "boom" in results[0]["error"]


@pytest.mark.asyncio
async def test_workflow_runner_approval_denied():
    """WorkflowRunner skips steps when approval is denied."""
    async def mock_executor(tool: str, args: dict) -> str:
        return "ok"

    async def deny_approval(wf_name: str, step_name: str) -> bool:
        return False

    runner = WorkflowRunner(tool_executor=mock_executor, approval_callback=deny_approval)
    wf = WorkflowDefinition.from_dict({
        "name": "approval-test",
        "steps": [
            {"name": "s1", "tool": "tool_a", "requires_approval": True},
        ],
    })

    results = await runner.run(wf)
    assert results[0]["status"] == "skipped"
    assert results[0]["reason"] == "approval_denied"


@pytest.mark.asyncio
async def test_workflow_runner_dry_run():
    """WorkflowRunner does dry-run when no executor provided."""
    runner = WorkflowRunner()
    wf = WorkflowDefinition.from_dict({
        "name": "dry-run",
        "steps": [{"name": "s1", "tool": "echo"}],
    })

    results = await runner.run(wf)
    assert results[0]["status"] == "success"
    assert "[dry-run]" in results[0]["output"]


# --- WorkflowManager ---


def test_workflow_manager_load(tmp_path: Path):
    """WorkflowManager loads YAML files from directory."""
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()

    (wf_dir / "wf1.yaml").write_text(
        "name: wf1\ndescription: first\ntrigger: manual\nsteps:\n  - name: s1\n    tool: echo\n"
    )
    (wf_dir / "wf2.yml").write_text(
        "name: wf2\ndescription: second\ntrigger: webhook\nsteps:\n  - name: s1\n    tool: echo\n"
    )

    mgr = WorkflowManager(wf_dir)
    mgr.load()

    workflows = mgr.list_workflows()
    assert len(workflows) == 2

    assert mgr.get("wf1") is not None
    assert mgr.get("wf2") is not None
    assert mgr.get("nonexistent") is None


def test_workflow_manager_list_shows_has_webhook_key(tmp_path: Path):
    """list_workflows reports whether a workflow has a per-webhook key."""
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    (wf_dir / "keyed.yaml").write_text(
        "name: keyed\ntrigger: webhook\nwebhook_key: secret123\nsteps:\n  - name: s1\n    tool: echo\n"
    )
    (wf_dir / "plain.yaml").write_text(
        "name: plain\ntrigger: webhook\nsteps:\n  - name: s1\n    tool: echo\n"
    )
    mgr = WorkflowManager(wf_dir)
    mgr.load()
    listing = {w["name"]: w for w in mgr.list_workflows()}
    assert listing["keyed"]["has_webhook_key"] is True
    assert listing["plain"]["has_webhook_key"] is False
