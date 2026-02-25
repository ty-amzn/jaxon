"""Example plugin — demonstrates the plugin API with a simple echo tool."""

from __future__ import annotations

from assistant.plugins.types import (
    BasePlugin,
    PluginContext,
    PluginManifest,
    PluginToolDef,
)


class ExamplePlugin(BasePlugin):
    """A simple example plugin that provides an echo tool."""

    def __init__(self) -> None:
        super().__init__(
            PluginManifest(
                name="example",
                version="1.0.0",
                description="Example plugin with echo tool",
                author="AI Assistant",
            )
        )

    def get_tools(self) -> list[PluginToolDef]:
        async def echo_handler(params: dict) -> str:
            text = params.get("text", "")
            return f"Echo: {text}"

        return [
            PluginToolDef(
                name="echo",
                description="Echo back the input text. Useful for testing.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to echo back",
                        }
                    },
                    "required": ["text"],
                },
                handler=echo_handler,
                permission_category="read",
            )
        ]


def create_plugin() -> ExamplePlugin:
    return ExamplePlugin()
