from rich.console import Console
from rich.table import Table

from ..services.db import get_report, init_db

console = Console()


def report() -> None:
    init_db()
    rows = get_report()

    if not rows:
        console.print("[yellow]No usage data recorded yet.[/yellow]")
        return

    console.print()
    console.print("[bold]AI Usage Report[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Feature", style="bold")
    table.add_column("Cost", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Calls", justify="right")
    table.add_column("Top Model")

    for r in rows:
        table.add_row(
            r["feature"],
            f"${r['total_cost']:.2f}",
            f"{r['total_tokens']:,}",
            str(r["calls"]),
            r["top_model"] or "unknown",
        )

    console.print(table)
    console.print()
