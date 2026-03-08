"""Tests for slash commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from assistant.cli.commands import CommandRegistry


def test_command_registry_has_defaults():
    registry = CommandRegistry()
    cmds = registry.commands
    assert "help" in cmds
    assert "status" in cmds
    assert "memory" in cmds
    assert "history" in cmds
    assert "cancel" in cmds
    assert "config" in cmds
    assert "skills" in cmds


def test_command_registry_custom():
    registry = CommandRegistry()

    async def handler(chat, args):
        pass

    registry.register("test", handler, "A test command")
    assert "test" in registry.commands


@pytest.mark.asyncio
async def test_dispatch_unknown_command():
    registry = CommandRegistry()
    mock_chat = MagicMock()
    mock_chat._console = MagicMock()
    await registry.dispatch("/unknown", mock_chat)
    mock_chat._console.print.assert_called()
    call_args = str(mock_chat._console.print.call_args)
    assert "Unknown command" in call_args
