from rich.console import Console

from ..services.db import init_db
from ..services.git import get_current_feature

console = Console()


def start() -> None:
    init_db()
    feature = get_current_feature()
    console.print(f"[green]Tracking started for feature:[/green] [bold]{feature}[/bold]")
