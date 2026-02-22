"""Click CLI group with chat, serve, and ask commands."""

from __future__ import annotations

import asyncio

import click

from assistant.core.config import get_settings
from assistant.core.logging import setup_logging


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Personal AI Assistant CLI."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


@cli.command()
def chat() -> None:
    """Start an interactive chat session."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.app_log_path)

    if not settings.anthropic_api_key:
        click.echo("Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and configure it.")
        raise SystemExit(1)

    from assistant.cli.chat import ChatInterface
    from assistant.cli.commands import CommandRegistry

    interface = ChatInterface(settings)
    command_registry = CommandRegistry()
    interface.set_command_registry(command_registry)

    asyncio.run(_run_chat(interface, settings))


async def _run_chat(interface, settings) -> None:
    """Async wrapper that starts scheduler/watchdog if enabled, then runs chat."""
    from assistant.core.notifications import NotificationDispatcher

    dispatcher = NotificationDispatcher()

    # Console notification sink
    async def console_sink(msg: str) -> None:
        interface._console.print(f"\n[bold yellow]Notification:[/bold yellow] {msg}\n")

    dispatcher.register(console_sink)

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
            chat_interface=interface,
            timezone=settings.scheduler_timezone,
        )
        await scheduler_manager.start()
        interface._scheduler_manager = scheduler_manager

        # Wire the real handler into the tool registry
        handler = create_schedule_reminder_handler(scheduler_manager)
        interface._tool_registry._handlers["schedule_reminder"] = handler

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
        interface._file_monitor = file_monitor

        # Watch configured paths
        for path in settings.watchdog_paths:
            file_monitor.add_path(path)

    try:
        await interface.run()
    finally:
        if scheduler_manager:
            await scheduler_manager.stop()
        if file_monitor:
            file_monitor.stop()


@cli.command()
@click.argument("question", nargs=-1, required=True)
def ask(question: tuple[str, ...]) -> None:
    """Ask a single question and get a response."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.app_log_path)

    if not settings.anthropic_api_key:
        click.echo("Error: ANTHROPIC_API_KEY not set.")
        raise SystemExit(1)

    from assistant.cli.chat import ChatInterface

    interface = ChatInterface(settings)
    full_question = " ".join(question)
    asyncio.run(interface.handle_message(full_question))


@cli.command()
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port to bind to")
def serve(host: str | None, port: int | None) -> None:
    """Start the API server."""
    import uvicorn

    settings = get_settings()
    setup_logging(settings.log_level, settings.app_log_path)

    uvicorn.run(
        "assistant.app:create_app",
        factory=True,
        host=host or settings.host,
        port=port or settings.port,
        reload=False,
    )
