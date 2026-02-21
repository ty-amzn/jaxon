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

    asyncio.run(interface.run())


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
