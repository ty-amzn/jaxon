"""Tests for WhatsApp integration."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from assistant.core.config import Settings


# --- Config ---


def test_whatsapp_config_defaults(tmp_path: Path):
    """WhatsApp config fields have correct defaults."""
    settings = Settings(anthropic_api_key="test", data_dir=tmp_path)

    assert settings.whatsapp_enabled is False
    assert settings.whatsapp_allowed_numbers == []
    assert settings.whatsapp_session_name == "assistant"
    assert settings.whatsapp_auth_dir == tmp_path / "whatsapp_auth"


# --- Mock neonize before importing whatsapp modules ---


@pytest.fixture(autouse=True)
def _mock_neonize():
    """Pre-mock neonize modules so our whatsapp code can be imported without
    the real neonize C/Go extensions."""
    mock_client_module = MagicMock()
    mock_events_module = MagicMock()
    mock_utils_module = MagicMock()

    # Make NewAClient return a mock with an .event() decorator
    mock_new_aclient = MagicMock()
    mock_new_aclient.return_value = MagicMock()
    mock_new_aclient.return_value.event = MagicMock(
        side_effect=lambda ev_type: lambda fn: fn
    )
    mock_client_module.NewAClient = mock_new_aclient

    mock_utils_module.build_jid = MagicMock(return_value=MagicMock())

    mocks = {
        "neonize": MagicMock(),
        "neonize.aioze": MagicMock(),
        "neonize.aioze.client": mock_client_module,
        "neonize.aioze.events": mock_events_module,
        "neonize.utils": mock_utils_module,
    }

    # Remove any previously cached imports of our whatsapp modules
    for mod_name in list(sys.modules):
        if mod_name.startswith("assistant.whatsapp"):
            del sys.modules[mod_name]

    with patch.dict(sys.modules, mocks):
        yield mocks

    # Clean up so other tests aren't affected
    for mod_name in list(sys.modules):
        if mod_name.startswith("assistant.whatsapp"):
            del sys.modules[mod_name]


# --- WhatsAppBot construction ---


def test_whatsapp_bot_construction(_mock_neonize, tmp_path: Path):
    """WhatsAppBot can be constructed with mock neonize client."""
    from assistant.whatsapp.bot import WhatsAppBot

    chat_interface = MagicMock()
    bot = WhatsAppBot(
        chat_interface=chat_interface,
        allowed_numbers=["+15551234567"],
        session_name="test",
        auth_dir=tmp_path,
    )

    assert bot.allowed_numbers == {"+15551234567"}
    assert bot.chat_interface is chat_interface
    mock_client_cls = _mock_neonize["neonize.aioze.client"].NewAClient
    mock_client_cls.assert_called_once_with(str(tmp_path / "test.sqlite3"))


# --- Message handler allowlist ---


def test_allowlist_check_empty_allows_all():
    """Empty allowlist allows all senders."""
    from assistant.whatsapp.handlers import _check_allowed

    bot = MagicMock()
    bot.allowed_numbers = set()
    assert _check_allowed(bot, "15551234567") is True


def test_allowlist_check_with_plus_prefix():
    """Allowlist matches numbers with or without + prefix."""
    from assistant.whatsapp.handlers import _check_allowed

    bot = MagicMock()
    bot.allowed_numbers = {"+15551234567"}

    # Sender number comes without + from JID
    assert _check_allowed(bot, "15551234567") is True
    assert _check_allowed(bot, "19999999999") is False


def test_allowlist_check_without_plus_prefix():
    """Allowlist matches when stored without + prefix."""
    from assistant.whatsapp.handlers import _check_allowed

    bot = MagicMock()
    bot.allowed_numbers = {"15551234567"}

    assert _check_allowed(bot, "15551234567") is True
    assert _check_allowed(bot, "19999999999") is False


# --- Send message chunking ---


@pytest.mark.asyncio
async def test_send_message_short(_mock_neonize, tmp_path: Path):
    """Short messages are sent in a single call."""
    from assistant.whatsapp.bot import WhatsAppBot

    bot = WhatsAppBot(
        chat_interface=MagicMock(),
        auth_dir=tmp_path,
    )
    bot._client.send_message = AsyncMock()

    mock_jid = MagicMock()
    _mock_neonize["neonize.utils"].build_jid.return_value = mock_jid

    await bot.send_message("+15551234567", "Hello")

    _mock_neonize["neonize.utils"].build_jid.assert_called_with("15551234567")
    bot._client.send_message.assert_called_once_with(mock_jid, "Hello")


@pytest.mark.asyncio
async def test_send_message_chunked(_mock_neonize, tmp_path: Path):
    """Long messages are split into chunks."""
    from assistant.whatsapp.bot import WhatsAppBot

    bot = WhatsAppBot(
        chat_interface=MagicMock(),
        auth_dir=tmp_path,
    )
    bot._client.send_message = AsyncMock()

    long_text = "x" * 8500  # Should be split into 3 chunks (4000 + 4000 + 500)
    await bot.send_message("+15551234567", long_text)

    assert bot._client.send_message.call_count == 3
