"""PluginManager — discover, load, and manage plugins from data/plugins/."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from assistant.plugins.types import (
    BasePlugin,
    Plugin,
    PluginContext,
    PluginManifest,
    PluginSkillDef,
    PluginToolDef,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """Discovers and manages plugin lifecycle."""

    def __init__(self, plugins_dir: Path, context: PluginContext) -> None:
        self._plugins_dir = plugins_dir
        self._context = context
        self._plugins: dict[str, Plugin] = {}
        self._started = False

    @property
    def plugins(self) -> dict[str, Plugin]:
        return dict(self._plugins)

    async def discover_and_load(self) -> None:
        """Discover .py files in plugins_dir and load them."""
        if not self._plugins_dir.exists():
            self._plugins_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Created plugins directory: %s", self._plugins_dir)
            return

        for path in sorted(self._plugins_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            await self._load_plugin_file(path)

        # Also check for packages (directories with __init__.py)
        for path in sorted(self._plugins_dir.iterdir()):
            if path.is_dir() and (path / "__init__.py").exists():
                await self._load_plugin_file(path / "__init__.py", package_name=path.name)

    async def _load_plugin_file(self, path: Path, package_name: str | None = None) -> None:
        """Load a single plugin file."""
        module_name = package_name or path.stem
        full_module_name = f"assistant_plugin_{module_name}"

        try:
            spec = importlib.util.spec_from_file_location(full_module_name, path)
            if spec is None or spec.loader is None:
                logger.warning("Could not create module spec for %s", path)
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules[full_module_name] = module
            spec.loader.exec_module(module)

            # Look for create_plugin() factory
            factory = getattr(module, "create_plugin", None)
            if factory is None:
                logger.warning("Plugin %s has no create_plugin() function", module_name)
                return

            plugin = factory()
            if not isinstance(plugin, (Plugin, BasePlugin)):
                logger.warning("Plugin %s: create_plugin() did not return a Plugin", module_name)
                return

            # Initialize
            await plugin.initialize(self._context)
            self._plugins[plugin.manifest.name] = plugin
            logger.info("Loaded plugin: %s v%s", plugin.manifest.name, plugin.manifest.version)

        except Exception:
            logger.exception("Failed to load plugin from %s", path)

    async def start_all(self) -> None:
        """Start all loaded plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.start()
                logger.debug("Started plugin: %s", name)
            except Exception:
                logger.exception("Failed to start plugin: %s", name)
        self._started = True

    async def stop_all(self) -> None:
        """Stop all loaded plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.stop()
                logger.debug("Stopped plugin: %s", name)
            except Exception:
                logger.exception("Failed to stop plugin: %s", name)
        self._started = False

    async def reload_plugin(self, name: str) -> bool:
        """Reload a specific plugin by name."""
        if name not in self._plugins:
            return False

        plugin = self._plugins[name]
        try:
            await plugin.stop()
        except Exception:
            logger.exception("Error stopping plugin %s during reload", name)

        del self._plugins[name]

        # Re-discover and load just this plugin
        for path in self._plugins_dir.glob("*.py"):
            if path.stem == name or path.stem.replace("-", "_") == name:
                await self._load_plugin_file(path)
                if name in self._plugins:
                    if self._started:
                        await self._plugins[name].start()
                    return True

        # Check packages
        pkg_dir = self._plugins_dir / name
        if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
            await self._load_plugin_file(pkg_dir / "__init__.py", package_name=name)
            if name in self._plugins:
                if self._started:
                    await self._plugins[name].start()
                return True

        return False

    def get_all_tools(self) -> list[PluginToolDef]:
        """Collect tool definitions from all plugins."""
        tools: list[PluginToolDef] = []
        for name, plugin in self._plugins.items():
            try:
                tools.extend(plugin.get_tools())
            except Exception:
                logger.exception("Error getting tools from plugin: %s", name)
        return tools

    def get_all_skills(self) -> list[PluginSkillDef]:
        """Collect skill definitions from all plugins."""
        skills: list[PluginSkillDef] = []
        for name, plugin in self._plugins.items():
            try:
                skills.extend(plugin.get_skills())
            except Exception:
                logger.exception("Error getting skills from plugin: %s", name)
        return skills

    def get_all_hooks(self) -> dict[str, list[tuple[str, Any]]]:
        """Collect hooks from all plugins, grouped by HookType."""
        from assistant.plugins.types import HookType

        hooks: dict[str, list[tuple[str, Any]]] = {ht.value: [] for ht in HookType}
        for name, plugin in self._plugins.items():
            try:
                for hook_type, handler in plugin.get_hooks().items():
                    hooks[hook_type.value].append((name, handler))
            except Exception:
                logger.exception("Error getting hooks from plugin: %s", name)
        return hooks
