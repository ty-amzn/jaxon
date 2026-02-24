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

from assistant.gateway.permissions import PermissionManager

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
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, _make_media(bot)))


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

        # Get or create Telegram approval callback for this chat
        if chat_id not in bot._approval_callbacks:
            from assistant.telegram.permissions import TelegramApprovalCallback

            numeric_chat_id = update.effective_chat.id if update.effective_chat else 0
            bot._approval_callbacks[chat_id] = TelegramApprovalCallback(
                bot.application.bot, numeric_chat_id
            )
        approval_cb = bot._approval_callbacks[chat_id]
        permission_manager = PermissionManager(approval_cb)

        # Create delivery callback for background tasks
        async def _tg_deliver(text: str) -> None:
            tg_bot = bot.application.bot
            numeric_id = update.effective_chat.id if update.effective_chat else 0
            if len(text) > 4000:
                for i in range(0, len(text), 4000):
                    await tg_bot.send_message(numeric_id, text[i:i + 4000])
            else:
                await tg_bot.send_message(numeric_id, text)

        try:
            response = await bot.chat_interface.get_response(
                chat_id, user_input,
                permission_manager=permission_manager,
                delivery_callback=_tg_deliver,
            )
            # Telegram has a 4096 char limit per message
            if len(response) > 4000:
                for i in range(0, len(response), 4000):
                    await update.message.reply_text(response[i:i + 4000])
            else:
                await update.message.reply_text(response or "Sorry, I got an empty response. Please try again.")
        except Exception:
            logger.exception("Error processing Telegram message")
            await update.message.reply_text("Sorry, an error occurred.")
    return handler


def _make_media(bot: TelegramBot):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message:
            return
        if not _check_allowed(bot, update.effective_user.id):
            await update.message.reply_text("Not authorized.")
            return

        chat_id = str(update.effective_chat.id) if update.effective_chat else "unknown"

        # Determine the file to download
        if update.message.photo:
            # Photos come as a list of sizes; pick the largest
            photo = update.message.photo[-1]
            file_id = photo.file_id
            mime_type = "image/jpeg"  # Telegram photos are always JPEG
            filename = "photo.jpg"
        elif update.message.document:
            file_id = update.message.document.file_id
            mime_type = update.message.document.mime_type or "image/png"
            filename = update.message.document.file_name or "document.png"
        else:
            return

        try:
            tg_file = await context.bot.get_file(file_id)
            file_bytes = await tg_file.download_as_bytearray()
        except Exception:
            logger.exception("Failed to download Telegram file %s", file_id)
            await update.message.reply_text("Sorry, I couldn't download that file.")
            return

        # Build multimodal content
        from assistant.cli.media import MediaContent, MediaHandler

        media = MediaContent.from_bytes(bytes(file_bytes), mime_type, filename)
        caption = update.message.caption or "What's in this image?"
        media_handler = MediaHandler()
        content = media_handler.build_multimodal_message(caption, [media])

        # Set up approval callback (same as text handler)
        if chat_id not in bot._approval_callbacks:
            from assistant.telegram.permissions import TelegramApprovalCallback

            numeric_chat_id = update.effective_chat.id if update.effective_chat else 0
            bot._approval_callbacks[chat_id] = TelegramApprovalCallback(
                bot.application.bot, numeric_chat_id
            )
        approval_cb = bot._approval_callbacks[chat_id]
        permission_manager = PermissionManager(approval_cb)

        async def _tg_deliver(text: str) -> None:
            tg_bot = bot.application.bot
            numeric_id = update.effective_chat.id if update.effective_chat else 0
            if len(text) > 4000:
                for i in range(0, len(text), 4000):
                    await tg_bot.send_message(numeric_id, text[i:i + 4000])
            else:
                await tg_bot.send_message(numeric_id, text)

        try:
            response = await bot.chat_interface.get_response(
                chat_id, caption,
                permission_manager=permission_manager,
                delivery_callback=_tg_deliver,
                content=content,
            )
            if len(response) > 4000:
                for i in range(0, len(response), 4000):
                    await update.message.reply_text(response[i:i + 4000])
            else:
                await update.message.reply_text(response or "Sorry, I got an empty response. Please try again.")
        except Exception:
            logger.exception("Error processing Telegram media message")
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

        chat_id = str(query.message.chat_id) if query.message else None
        approval_cb = bot._approval_callbacks.get(chat_id) if chat_id else None

        if action == "show_full":
            if approval_cb:
                full_text = approval_cb.get_full_details(request_id)
                if full_text and query.message:
                    # Send as a new message to preserve the approve/deny buttons
                    for i in range(0, len(full_text), 4000):
                        await query.message.reply_text(full_text[i:i + 4000])
            return

        approved = action == "approve"

        if approval_cb:
            approval_cb.resolve(request_id, approved)

        status = "Approved" if approved else "Denied"
        if query.message:
            await query.message.edit_text(f"{query.message.text}\n\n{status}")
    return handler
