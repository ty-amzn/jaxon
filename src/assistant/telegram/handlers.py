"""Telegram command and message handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

if TYPE_CHECKING:
    from assistant.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)


def register_handlers(bot: TelegramBot) -> None:
    """Register all handlers on the bot's application."""
    app = bot.application

    app.add_handler(CommandHandler("start", _make_start(bot)))
    app.add_handler(CommandHandler("status", _make_status(bot)))
    app.add_handler(CommandHandler("schedule", _make_schedule(bot)))
    app.add_handler(CommandHandler("watch", _make_watch(bot)))
    app.add_handler(CallbackQueryHandler(_make_callback(bot)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _make_text(bot)))


def _check_allowed(bot: TelegramBot, user_id: int | None) -> bool:
    if not bot.allowed_user_ids:
        return True  # No whitelist = allow all
    return user_id in bot.allowed_user_ids


def _make_start(bot: TelegramBot):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message:
            return
        if not _check_allowed(bot, update.effective_user.id):
            await update.message.reply_text("Not authorized.")
            return
        await update.message.reply_text(
            "AI Assistant connected. Send me a message to chat."
        )
    return handler


def _make_status(bot: TelegramBot):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message:
            return
        if not _check_allowed(bot, update.effective_user.id):
            return
        chat_id = str(update.effective_chat.id) if update.effective_chat else "unknown"
        session = bot.chat_interface._session_manager.get_or_create_keyed_session(chat_id)
        await update.message.reply_text(
            f"Session: {session.id}\n"
            f"Messages: {len(session.messages)}\n"
            f"Model: {bot.chat_interface._settings.model}"
        )
    return handler


def _make_schedule(bot: TelegramBot):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message:
            return
        if not _check_allowed(bot, update.effective_user.id):
            return
        if bot.scheduler_manager is None:
            await update.message.reply_text("Scheduler is not enabled.")
            return
        jobs = bot.scheduler_manager.list_jobs()
        if not jobs:
            await update.message.reply_text("No scheduled jobs.")
            return
        lines = [f"- {j['id']}: {j['description']} ({j['trigger']})" for j in jobs]
        await update.message.reply_text("Scheduled jobs:\n" + "\n".join(lines))
    return handler


def _make_watch(bot: TelegramBot):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message:
            return
        if not _check_allowed(bot, update.effective_user.id):
            return
        if bot.file_monitor is None:
            await update.message.reply_text("Watchdog is not enabled.")
            return
        paths = bot.file_monitor.watched_paths
        if not paths:
            await update.message.reply_text("No watched paths.")
            return
        await update.message.reply_text("Watched paths:\n" + "\n".join(f"- {p}" for p in paths))
    return handler


def _make_text(bot: TelegramBot):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message or not update.message.text:
            return
        if not _check_allowed(bot, update.effective_user.id):
            await update.message.reply_text("Not authorized.")
            return

        chat_id = str(update.effective_chat.id) if update.effective_chat else "unknown"
        user_input = update.message.text

        try:
            response = await bot.chat_interface.get_response(chat_id, user_input)
            # Telegram has a 4096 char limit per message
            if len(response) > 4000:
                for i in range(0, len(response), 4000):
                    await update.message.reply_text(response[i:i + 4000])
            else:
                await update.message.reply_text(response or "(no response)")
        except Exception:
            logger.exception("Error processing Telegram message")
            await update.message.reply_text("Sorry, an error occurred.")
    return handler


def _make_callback(bot: TelegramBot):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not query.data:
            return

        await query.answer()

        parts = query.data.split(":", 1)
        if len(parts) != 2:
            return

        action, request_id = parts
        approved = action == "approve"

        chat_id = str(query.message.chat_id) if query.message else None
        if chat_id and chat_id in bot._approval_callbacks:
            bot._approval_callbacks[chat_id].resolve(request_id, approved)

        status = "Approved" if approved else "Denied"
        if query.message:
            await query.message.edit_text(f"{query.message.text}\n\n{status}")
    return handler
