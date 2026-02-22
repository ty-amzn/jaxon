"""Plugin system types — protocol, manifest, and hook definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class HookType(str, Enum):
    PRE_MESSAGE = "pre_message"
    POST_MESSAGE = "post_message"
    PRE_TOOL_CALL = "pre_tool_call"
    POST_TOOL_CALL = "post_tool_call"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class PluginManifest:
    """Metadata about a plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""


@dataclass
class PluginToolDef:
    """A tool contributed by a plugin."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    handler: Any = None  # async callable(dict) -> str
    permission_category: str = "write"  # read, write, delete, network_read, network_write


@dataclass
class PluginSkillDef:
    """A skill (system prompt section) contributed by a plugin."""

    name: str
    content: str


@dataclass
class PluginContext:
    """Context passed to plugins during initialization."""

    data_dir: Any  # Path
    settings: Any  # Settings


@runtime_checkable
class Plugin(Protocol):
    """Protocol that all plugins must implement."""

    @property
    def manifest(self) -> PluginManifest: ...

    async def initialize(self, context: PluginContext) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def get_tools(self) -> list[PluginToolDef]: ...

    def get_skills(self) -> list[PluginSkillDef]: ...

    def get_hooks(self) -> dict[HookType, Any]: ...


class BasePlugin:
    """Convenience base class for plugins (not required, but helpful)."""

    def __init__(self, manifest: PluginManifest) -> None:
        self._manifest = manifest

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    async def initialize(self, context: PluginContext) -> None:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def get_tools(self) -> list[PluginToolDef]:
        return []

    def get_skills(self) -> list[PluginSkillDef]:
        return []

    def get_hooks(self) -> dict[HookType, Any]:
        return {}
