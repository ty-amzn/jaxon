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


@cli.command("whatsapp-pair")
@click.option("--reset", is_flag=True, help="Delete existing session and re-pair")
def whatsapp_pair(reset: bool) -> None:
    """Pair WhatsApp by scanning a QR code.

    Run this once to link your WhatsApp account. The session is saved
    to data/whatsapp_auth/ and reused by the server automatically.

    In Docker:  docker compose run --rm -it assistant uv run assistant whatsapp-pair
    """
    asyncio.run(_whatsapp_pair(reset))


async def _whatsapp_pair(reset: bool) -> None:
    """Standalone WhatsApp pairing — runs neonize with its own event loop."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.app_log_path)

    auth_dir = settings.whatsapp_auth_dir
    auth_dir.mkdir(parents=True, exist_ok=True)
    db_path = auth_dir / f"{settings.whatsapp_session_name}.sqlite3"

    if reset and db_path.exists():
        db_path.unlink()
        click.echo(f"Deleted existing session: {db_path}")

    if db_path.exists():
        click.echo(f"Session file already exists: {db_path}")
        click.echo("Use --reset to delete it and re-pair.")
        click.echo("Starting anyway to verify connection...\n")

    # Patch neonize's internal event loop to the currently running one.
    # neonize creates its own loop at import time and all Go→Python callbacks
    # (QR codes, connected, messages) are scheduled on it.  Without this patch
    # those callbacks silently go nowhere.
    # Both modules must be patched: client.py has its own binding via
    # `from .events import event_global_loop`.
    import neonize.aioze.client as neonize_client
    import neonize.aioze.events as neonize_events
    running_loop = asyncio.get_running_loop()
    neonize_events.event_global_loop = running_loop
    neonize_client.event_global_loop = running_loop

    from neonize.aioze.client import NewAClient
    from neonize.aioze.events import ConnectedEv

    client = NewAClient(str(db_path))
    client.loop = running_loop

    paired = asyncio.Event()

    @client.event(ConnectedEv)
    async def on_connected(_client: NewAClient, _event: ConnectedEv) -> None:
        click.echo("\nWhatsApp connected successfully! Session saved.")
        click.echo(f"Auth file: {db_path}")
        click.echo("\nYou can now start the server — it will reuse this session.")
        paired.set()

    click.echo("Starting WhatsApp pairing...")
    click.echo("Open WhatsApp > Settings > Linked Devices > Link a Device")
    click.echo("Then scan the QR code below:\n")

    await client.connect()

    # Wait for connection or timeout
    try:
        await asyncio.wait_for(paired.wait(), timeout=120)
    except asyncio.TimeoutError:
        click.echo("\nPairing timed out after 120 seconds. Try again.")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


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
