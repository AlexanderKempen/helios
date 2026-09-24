import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..services.db import get_report, init_db

console = Console()


def _format_cost(cost: float) -> Text:
    return Text(f"${cost:,.2f}", style="magenta")


def _format_tokens(tokens: int) -> str:
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


MODEL_LABEL = re.compile(
    r"claude-(?P<family>opus|sonnet|haiku|fable|mythos)-(?P<version>\d+(?:-\d+)?)"
    r"|claude-(?P<major>\d+)(?:-(?P<minor>\d+))?-(?P<legacy_family>opus|sonnet|haiku)"
)


def _short_model(model: str | None) -> str:
    """Render 'claude-sonnet-4-5-20250929' as 'Sonnet 4.5'."""
    if not model:
        return "—"
    match = MODEL_LABEL.search(model)
    if not match:
        return model
    if match.group("family"):
        return f"{match.group('family').title()} {match.group('version').replace('-', '.')}"
    version = match.group("major")
    if match.group("minor"):
        version = f"{version}.{match.group('minor')}"
    return f"{match.group('legacy_family').title()} {version}"


def report() -> None:
    init_db()
    rows = get_report()

    if not rows:
        console.print("[dim]No usage data recorded yet.[/dim]")
        return

    total_cost = sum(r["total_cost"] for r in rows)
    total_tokens = sum(r["total_tokens"] for r in rows)
    total_calls = sum(r["calls"] for r in rows)

    table = Table(
        show_header=True,
        header_style="bold",
        border_style="dim",
        row_styles=["", ""],
        padding=(0, 1),
        expand=True,
    )
    table.add_column("Feature", style="white", ratio=3)
    table.add_column("Cost", justify="right", ratio=1)
    table.add_column("Tokens", justify="right", style="cyan", ratio=1)
    table.add_column("Calls", justify="center", style="dim", ratio=1)
    table.add_column("Model", ratio=2)

    for r in rows:
        table.add_row(
            r["feature"],
            _format_cost(r["total_cost"]),
            _format_tokens(r["total_tokens"]),
            str(r["calls"]),
            _short_model(r["top_model"]),
        )

    summary = Text.assemble(
        ("Total: ", "dim"),
        (f"${total_cost:,.2f}", "bold"),
        ("  ·  ", "dim"),
        (f"{_format_tokens(total_tokens)} tokens", "cyan"),
        ("  ·  ", "dim"),
        (f"{total_calls} calls", "dim"),
        ("  ·  ", "dim"),
        (f"{len(rows)} branches", "dim"),
    )

    console.print()
    console.print(Panel(table, title="[bold]helios[/bold]", subtitle=summary, border_style="blue", padding=(1, 2)))
    console.print()
