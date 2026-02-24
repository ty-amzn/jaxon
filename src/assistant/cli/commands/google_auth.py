"""One-time Google OAuth2 CLI command for Calendar API access."""

from __future__ import annotations

import json

import click

from assistant.core.config import get_settings
from assistant.tools.google_calendar import SCOPES


@click.command("google-auth")
def google_auth() -> None:
    """Authenticate with Google Calendar (one-time OAuth2 setup).

    Opens a browser for consent. The refresh token is saved to
    data/google_auth/credentials.json and reused automatically.

    Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars.
    """
    settings = get_settings()

    if not settings.google_client_id or not settings.google_client_secret:
        click.echo(
            "Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set.\n"
            "Create OAuth Desktop credentials in Google Cloud Console and add them to .env."
        )
        raise SystemExit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    # Build client config from env vars (no client_secrets.json file needed)
    client_config = {
        "installed": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    click.echo("Opening browser for Google Calendar authorization...")
    click.echo("If the browser doesn't open, copy the URL from the terminal.\n")

    creds = flow.run_local_server(port=0)

    # Save credentials
    auth_dir = settings.google_auth_dir
    auth_dir.mkdir(parents=True, exist_ok=True)
    creds_path = auth_dir / "credentials.json"

    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }
    creds_path.write_text(json.dumps(data))

    click.echo(f"\nCredentials saved to {creds_path}")
    click.echo("Google Calendar integration is ready!")
    click.echo("\nSet ASSISTANT_GOOGLE_CALENDAR_ENABLED=true in .env to activate.")
