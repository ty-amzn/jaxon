"""Workflow engine for multi-step YAML-defined automation chains."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    name: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False


@dataclass
class WorkflowDefinition:
    """A multi-step workflow loaded from YAML."""

    name: str
    description: str
    trigger: str  # "manual", "webhook", "schedule"
    steps: list[WorkflowStep] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowDefinition:
        steps = [
            WorkflowStep(
                name=s.get("name", f"step_{i}"),
                tool=s["tool"],
                args=s.get("args", {}),
                requires_approval=s.get("requires_approval", False),
            )
            for i, s in enumerate(data.get("steps", []))
        ]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            trigger=data.get("trigger", "manual"),
            steps=steps,
            enabled=data.get("enabled", True),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> WorkflowDefinition:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


class WorkflowRunner:
    """Executes workflow definitions step by step."""

    def __init__(
        self,
        tool_executor: Any = None,
        approval_callback: Any = None,
    ) -> None:
        self._tool_executor = tool_executor
        self._approval_callback = approval_callback

    async def run(
        self,
        definition: WorkflowDefinition,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run all steps in a workflow, passing output forward.

        Returns a list of step results.
        """
        ctx = dict(context or {})
        results: list[dict[str, Any]] = []

        for step in definition.steps:
            logger.info("Workflow %s: running step %s", definition.name, step.name)

            if step.requires_approval and self._approval_callback:
                approved = await self._approval_callback(definition.name, step.name)
                if not approved:
                    results.append({
                        "step": step.name,
                        "status": "skipped",
                        "reason": "approval_denied",
                    })
                    logger.info("Step %s skipped (approval denied)", step.name)
                    continue

            # Merge context into step args
            merged_args = {**step.args, **ctx}

            try:
                if self._tool_executor:
                    output = await self._tool_executor(step.tool, merged_args)
                else:
                    output = f"[dry-run] {step.tool}({merged_args})"

                ctx["previous_output"] = output
                results.append({
                    "step": step.name,
                    "status": "success",
                    "output": output,
                })
            except Exception as e:
                logger.exception("Step %s failed", step.name)
                results.append({
                    "step": step.name,
                    "status": "error",
                    "error": str(e),
                })
                break  # Stop workflow on error

        return results


class WorkflowManager:
    """Manages workflow definitions loaded from YAML files."""

    def __init__(self, workflow_dir: Path) -> None:
        self._workflow_dir = workflow_dir
        self._workflows: dict[str, WorkflowDefinition] = {}

    def load(self) -> None:
        """Load all workflow YAML files from the workflow directory."""
        self._workflows.clear()
        self._workflow_dir.mkdir(parents=True, exist_ok=True)

        for path in sorted(self._workflow_dir.glob("*.yaml")):
            try:
                wf = WorkflowDefinition.from_yaml(path)
                self._workflows[wf.name] = wf
                logger.info("Loaded workflow: %s", wf.name)
            except Exception:
                logger.exception("Failed to load workflow from %s", path)

        for path in sorted(self._workflow_dir.glob("*.yml")):
            if path.with_suffix(".yaml").exists():
                continue  # Skip if .yaml version exists
            try:
                wf = WorkflowDefinition.from_yaml(path)
                self._workflows[wf.name] = wf
                logger.info("Loaded workflow: %s", wf.name)
            except Exception:
                logger.exception("Failed to load workflow from %s", path)

    def get(self, name: str) -> WorkflowDefinition | None:
        return self._workflows.get(name)

    def list_workflows(self) -> list[dict[str, Any]]:
        return [
            {
                "name": wf.name,
                "description": wf.description,
                "trigger": wf.trigger,
                "steps": len(wf.steps),
                "enabled": wf.enabled,
            }
            for wf in self._workflows.values()
        ]
