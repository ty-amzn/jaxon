"""Tests for Slack bot integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from assistant.core.config import Settings


class TestSlackConfigDefaults:
    """Verify Slack config fields exist with correct defaults."""

    def test_slack_config_defaults(self):
        with patch.dict("os.environ", {}, clear=False):
            settings = Settings(
                _env_file=None,  # type: ignore[call-arg]
            )
        assert settings.slack_enabled is False
        assert settings.slack_bot_token == ""
        assert settings.slack_app_token == ""
        assert settings.slack_allowed_user_ids == []
        assert settings.slack_allowed_channel_ids == []

    def test_slack_allowed_user_ids_parsing(self):
        with patch.dict(
            "os.environ",
            {"ASSISTANT_SLACK_ALLOWED_USER_IDS": "U01ABC,U02DEF"},
            clear=False,
        ):
            settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.slack_allowed_user_ids == ["U01ABC", "U02DEF"]

    def test_slack_allowed_channel_ids_parsing(self):
        with patch.dict(
            "os.environ",
            {"ASSISTANT_SLACK_ALLOWED_CHANNEL_IDS": "C01XYZ,C02ABC"},
            clear=False,
        ):
            settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.slack_allowed_channel_ids == ["C01XYZ", "C02ABC"]


class TestCheckAllowed:
    """Test the _check_allowed helper function."""

    def _make_bot(
        self,
        allowed_user_ids: list[str] | None = None,
        allowed_channel_ids: list[str] | None = None,
    ) -> MagicMock:
        bot = MagicMock()
        bot.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids else set()
        bot.allowed_channel_ids = set(allowed_channel_ids) if allowed_channel_ids else set()
        return bot

    def test_check_allowed_empty_allows_all(self):
        from assistant.slack.handlers import _check_allowed

        bot = self._make_bot()
        assert _check_allowed(bot, "U123", "C456") is True

    def test_check_allowed_user_filter(self):
        from assistant.slack.handlers import _check_allowed

        bot = self._make_bot(allowed_user_ids=["U111", "U222"])
        assert _check_allowed(bot, "U111", "C456") is True
        assert _check_allowed(bot, "U999", "C456") is False

    def test_check_allowed_channel_filter(self):
        from assistant.slack.handlers import _check_allowed

        bot = self._make_bot(allowed_channel_ids=["C111", "C222"])
        assert _check_allowed(bot, "U123", "C111") is True
        assert _check_allowed(bot, "U123", "C999") is False

    def test_check_allowed_both_filters(self):
        from assistant.slack.handlers import _check_allowed

        bot = self._make_bot(
            allowed_user_ids=["U111"],
            allowed_channel_ids=["C111"],
        )
        assert _check_allowed(bot, "U111", "C111") is True
        assert _check_allowed(bot, "U111", "C999") is False
        assert _check_allowed(bot, "U999", "C111") is False


class TestSendMessage:
    """Test SlackBot.send_message."""

    def _make_bot(self) -> object:
        """Create a SlackBot with mocked Slack dependencies."""
        import assistant.slack.bot as bot_mod

        with patch.object(bot_mod, "AsyncApp"), \
             patch.object(bot_mod, "AsyncSocketModeHandler"):
            from assistant.slack.bot import SlackBot

            bot = SlackBot(
                bot_token="xoxb-test",
                app_token="xapp-test",
                chat_interface=MagicMock(),
            )
            bot._app.client.chat_postMessage = AsyncMock()
            return bot

    @pytest.mark.asyncio
    async def test_send_message_short(self):
        bot = self._make_bot()

        await bot.send_message("C123", "Hello!")

        bot._app.client.chat_postMessage.assert_called_once_with(
            channel="C123", text="Hello!"
        )

    @pytest.mark.asyncio
    async def test_send_message_chunked(self):
        bot = self._make_bot()

        long_text = "x" * 8500  # Should be split into 3 chunks
        await bot.send_message("C123", long_text)

        calls = bot._app.client.chat_postMessage.call_args_list
        assert len(calls) == 3
        assert calls[0].kwargs["text"] == "x" * 4000
        assert calls[1].kwargs["text"] == "x" * 4000
        assert calls[2].kwargs["text"] == "x" * 500
