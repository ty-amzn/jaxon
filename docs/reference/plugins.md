# Plugins

Plugins extend the assistant with custom tools, skills, and lifecycle hooks — all without modifying source code. Drop a Python file into `data/plugins/` and it's live on the next start.

## Configuration

```bash
ASSISTANT_PLUGINS_ENABLED=true
```

---

## Writing a Plugin

Create a `.py` file in `data/plugins/`. Each plugin must:

1. Define a class that extends `BasePlugin` (or implements the `Plugin` protocol)
2. Export a `create_plugin()` factory function

Here's a minimal plugin that adds a tool:

```python
# data/plugins/my_plugin.py
from assistant.plugins.types import BasePlugin, PluginManifest, PluginToolDef

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__(PluginManifest(
            name="my-plugin",
            version="1.0.0",
            description="My custom plugin",
            author="Me",
        ))

    def get_tools(self) -> list[PluginToolDef]:
        async def greet(params: dict) -> str:
            return f"Hello, {params['name']}!"

        return [PluginToolDef(
            name="greet",
            description="Greet someone by name",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            handler=greet,
            permission_category="read",   # auto-approved
        )]

def create_plugin() -> MyPlugin:
    return MyPlugin()
```

Plugin packages (directories with `__init__.py`) are also supported. Files starting with `_` are ignored.

---

## Plugin API

Plugins can contribute three things:

### Tools

Registered with the LLM tool system and permission gates:

```python
def get_tools(self) -> list[PluginToolDef]:
    return [PluginToolDef(
        name="tool_name",
        description="What it does",
        input_schema={...},                # JSON Schema
        handler=async_callable,            # async (dict) -> str
        permission_category="read",        # read | write | delete | network_read | network_write
    )]
```

### Skills

Markdown injected into the system prompt:

```python
def get_skills(self) -> list[PluginSkillDef]:
    return [PluginSkillDef(
        name="my-skill",
        content="When asked about X, do Y...",
    )]
```

### Hooks

Async callbacks at key lifecycle points:

```python
def get_hooks(self) -> dict[HookType, Any]:
    async def on_pre_message(message: str, session_id: str = "") -> str:
        # Modify or inspect messages before they reach the LLM
        return message

    return {HookType.PRE_MESSAGE: on_pre_message}
```

Available hooks:

| Hook | Fires when | Signature |
|------|-----------|-----------|
| `PRE_MESSAGE` | Before user message is processed | `(message, session_id) -> str` |
| `POST_MESSAGE` | After response is generated | `(message, response, session_id) -> None` |
| `PRE_TOOL_CALL` | Before a tool executes | `(tool_name, params) -> None` |
| `POST_TOOL_CALL` | After a tool completes | `(tool_name, params, result) -> None` |
| `SESSION_START` | Chat session begins | `() -> None` |
| `SESSION_END` | Chat session ends | `() -> None` |

---

## Lifecycle

Plugins go through these stages:

1. **Discovery** — `data/plugins/` is scanned for `.py` files and packages
2. **Load** — `create_plugin()` is called, plugin is validated
3. **Initialize** — `plugin.initialize(context)` receives `PluginContext` with `data_dir` and `settings`
4. **Start** — `plugin.start()` is called (set up connections, background tasks, etc.)
5. **Stop** — `plugin.stop()` is called on shutdown (clean up resources)

Errors in any plugin are isolated — a broken plugin won't crash the assistant.

---

## CLI Commands

```
/plugins              # List all loaded plugins
/plugins info <name>  # Show details (tools, skills, hooks)
/plugins reload <name> # Hot-reload a plugin without restart
```
