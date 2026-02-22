"""App startup/shutdown lifecycle events."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from assistant.core.config import get_settings
from assistant.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    setup_logging(settings.log_level, settings.app_log_path)
    logger.info("Assistant API starting up")

    # Ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.daily_log_dir.mkdir(parents=True, exist_ok=True)
    settings.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    settings.search_db_path.parent.mkdir(parents=True, exist_ok=True)

    from assistant.core.notifications import NotificationDispatcher

    dispatcher = NotificationDispatcher(
        dnd_enabled=settings.dnd_enabled,
        dnd_start=settings.dnd_start,
        dnd_end=settings.dnd_end,
        allow_urgent=settings.dnd_allow_urgent,
    )
    app.state.dispatcher = dispatcher

    # Create ChatInterface for headless use (Telegram, scheduler)
    from assistant.cli.chat import ChatInterface

    chat_interface = ChatInterface(settings)
    app.state.chat_interface = chat_interface

    # Start scheduler if enabled
    scheduler_manager = None
    if settings.scheduler_enabled:
        from assistant.scheduler.store import JobStore
        from assistant.scheduler.manager import SchedulerManager
        from assistant.scheduler.tool import create_schedule_reminder_handler

        job_store = JobStore(settings.scheduler_db_path)
        scheduler_manager = SchedulerManager(
            job_store=job_store,
            dispatcher=dispatcher,
            chat_interface=chat_interface,
            timezone=settings.scheduler_timezone,
        )
        await scheduler_manager.start()
        app.state.scheduler_manager = scheduler_manager

        # Wire the real handler
        handler = create_schedule_reminder_handler(scheduler_manager)
        chat_interface._tool_registry._handlers["schedule_reminder"] = handler

    # Initialize workflow system
    from assistant.scheduler.workflow import WorkflowManager, WorkflowRunner

    workflow_manager = WorkflowManager(settings.workflow_dir)
    workflow_manager.load()
    workflow_runner = WorkflowRunner()
    app.state.workflow_manager = workflow_manager
    app.state.workflow_runner = workflow_runner

    # Wire webhook router if enabled
    if settings.webhook_enabled:
        from assistant.gateway.webhooks import configure_webhooks, router as webhook_router

        configure_webhooks(
            secret=settings.webhook_secret,
            workflow_manager=workflow_manager,
            workflow_runner=workflow_runner,
            dispatcher=dispatcher,
        )
        app.include_router(webhook_router)

    # Start watchdog if enabled
    file_monitor = None
    if settings.watchdog_enabled:
        from assistant.watchdog_monitor.monitor import FileMonitor

        file_monitor = FileMonitor(
            dispatcher=dispatcher,
            debounce_seconds=settings.watchdog_debounce_seconds,
            analyze=settings.watchdog_analyze,
        )
        file_monitor.start()
        app.state.file_monitor = file_monitor

        for path in settings.watchdog_paths:
            file_monitor.add_path(path)

    # Start Telegram bot if enabled
    telegram_bot = None
    if settings.telegram_enabled and settings.telegram_bot_token:
        from assistant.telegram.bot import TelegramBot

        telegram_bot = TelegramBot(
            token=settings.telegram_bot_token,
            chat_interface=chat_interface,
            allowed_user_ids=settings.telegram_allowed_user_ids,
            webhook_url=settings.telegram_webhook_url,
            scheduler_manager=scheduler_manager,
            file_monitor=file_monitor,
        )
        await telegram_bot.start()
        app.state.telegram_bot = telegram_bot

        # Register Telegram as notification sink for all allowed users
        if settings.telegram_allowed_user_ids:
            for user_id in settings.telegram_allowed_user_ids:
                async def tg_sink(msg: str, uid=user_id) -> None:
                    await telegram_bot.send_message(uid, msg)
                dispatcher.register(tg_sink)

    # Start WhatsApp bot if enabled
    whatsapp_bot = None
    if settings.whatsapp_enabled:
        from assistant.whatsapp.bot import WhatsAppBot

        whatsapp_bot = WhatsAppBot(
            chat_interface=chat_interface,
            allowed_numbers=settings.whatsapp_allowed_numbers,
            session_name=settings.whatsapp_session_name,
            auth_dir=settings.whatsapp_auth_dir,
        )
        await whatsapp_bot.start()
        app.state.whatsapp_bot = whatsapp_bot

        # Register WhatsApp as notification sink for allowed numbers
        if settings.whatsapp_allowed_numbers:
            for number in settings.whatsapp_allowed_numbers:
                async def wa_sink(msg: str, num=number) -> None:
                    await whatsapp_bot.send_message(num, msg)
                dispatcher.register(wa_sink)

    yield

    # Shutdown
    if whatsapp_bot:
        await whatsapp_bot.stop()
    if telegram_bot:
        await telegram_bot.stop()
    if scheduler_manager:
        await scheduler_manager.stop()
    if file_monitor:
        file_monitor.stop()

    logger.info("Assistant API shutting down")
