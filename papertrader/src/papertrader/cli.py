"""Paper Trading CLI."""

from __future__ import annotations

import click


@click.group()
def cli() -> None:
    """Paper Trading — simulated stock trading with real prices."""


@cli.command()
@click.option("--host", default=None, help="Bind host (default from env or 127.0.0.1)")
@click.option("--port", default=None, type=int, help="Bind port (default from env or 51433)")
def serve(host: str | None, port: int | None) -> None:
    """Run the Paper Trading API server."""
    import logging
    import uvicorn

    from papertrader.config import Settings

    logging.basicConfig(level=logging.INFO)

    settings = Settings()
    final_host = host or settings.host
    final_port = port or settings.port

    from papertrader.app import create_app

    app = create_app(settings)
    uvicorn.run(app, host=final_host, port=final_port)


if __name__ == "__main__":
    cli()
