"""Slash command: /webhook — list and test webhooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_webhook(chat: ChatInterface, args: list[str]) -> None:
    """Handle /webhook command."""
    console = chat._console
    settings = chat._settings

    if not settings.webhook_enabled:
        console.print("[yellow]Webhooks are not enabled. Set ASSISTANT_WEBHOOK_ENABLED=true[/yellow]")
        return

    workflow_manager = getattr(chat, "_workflow_manager", None)

    subcommand = args[0] if args else "list"

    if subcommand == "list":
        if workflow_manager is None:
            console.print("[dim]No webhook endpoints registered.[/dim]")
            return

        workflows = workflow_manager.list_workflows()
        webhook_workflows = [w for w in workflows if w["trigger"] in ("webhook", "manual")]
        if not webhook_workflows:
            console.print("[dim]No workflows with webhook triggers.[/dim]")
            return

        console.print("[bold]Webhook Endpoints:[/bold]")
        base_url = f"http://{settings.host}:{settings.port}"
        for wf in webhook_workflows:
            status = "[green]enabled[/green]" if wf["enabled"] else "[red]disabled[/red]"
            console.print(f"  POST {base_url}/webhooks/{wf['name']}  ({status})")

    elif subcommand == "test" and len(args) > 1:
        name = args[1]
        import httpx

        url = f"http://{settings.host}:{settings.port}/webhooks/{name}"
        headers = {}
        if settings.webhook_secret:
            headers["Authorization"] = f"Bearer {settings.webhook_secret}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"test": True}, headers=headers)
            if resp.status_code == 200:
                console.print(f"[green]Webhook test successful: {resp.json()}[/green]")
            else:
                console.print(f"[red]Webhook test failed ({resp.status_code}): {resp.text}[/red]")
        except httpx.ConnectError:
            console.print("[red]Could not connect. Is the API server running? (assistant serve)[/red]")

    else:
        console.print(
            "[bold]Usage:[/bold]\n"
            "  /webhook list           — List webhook endpoints\n"
            "  /webhook test <name>    — Test a webhook endpoint"
        )
