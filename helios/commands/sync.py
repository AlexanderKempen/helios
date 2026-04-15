from rich.console import Console

from ..services.db import init_db
from ..services.sync import sync_claude_sessions

console = Console()


def sync() -> None:
    init_db()
    console.print("[dim]Syncing Claude Code sessions...[/dim]")
    count = sync_claude_sessions()
    if count == 0:
        console.print("[yellow]No new usage events found.[/yellow]")
    else:
        console.print(f"[green]Imported {count:,} usage events from Claude Code.[/green]")
