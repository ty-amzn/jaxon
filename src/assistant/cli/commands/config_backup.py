"""Slash command: /backup — create, list, and restore data backups."""

from __future__ import annotations

import tarfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface


async def handle_backup(chat: ChatInterface, args: list[str]) -> None:
    """Handle /backup command."""
    console = chat._console
    settings = chat._settings
    backup_dir = settings.backup_dir
    data_dir = settings.data_dir

    subcommand = args[0] if args else "help"

    if subcommand == "create":
        name = args[1] if len(args) > 1 else "backup"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}-{timestamp}.tar.gz"

        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / filename

        # Create tarball of data dir, excluding backups dir itself
        with tarfile.open(backup_path, "w:gz") as tar:
            for item in data_dir.iterdir():
                if item.name == "backups":
                    continue
                tar.add(item, arcname=item.name)

        size_kb = backup_path.stat().st_size / 1024
        console.print(f"[green]Backup created: {filename} ({size_kb:.1f} KB)[/green]")

    elif subcommand == "list":
        backup_dir.mkdir(parents=True, exist_ok=True)
        backups = sorted(backup_dir.glob("*.tar.gz"))
        if not backups:
            console.print("[dim]No backups found.[/dim]")
            return

        console.print("[bold]Available Backups:[/bold]")
        for bp in backups:
            size_kb = bp.stat().st_size / 1024
            console.print(f"  {bp.name}  ({size_kb:.1f} KB)")

    elif subcommand == "restore" and len(args) > 1:
        name = args[1]
        # Find backup file
        backup_dir.mkdir(parents=True, exist_ok=True)
        matches = list(backup_dir.glob(f"{name}*"))
        if not matches:
            console.print(f"[red]Backup not found: {name}[/red]")
            return

        backup_path = matches[0]
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(path=data_dir)

        console.print(f"[green]Restored from: {backup_path.name}[/green]")

    else:
        console.print(
            "[bold]Usage:[/bold]\n"
            "  /backup create [name]     — Create a backup\n"
            "  /backup list              — List available backups\n"
            "  /backup restore <name>    — Restore from a backup"
        )
