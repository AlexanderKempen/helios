from rich.console import Console
from rich.panel import Panel

from ..services.claude import run_claude
from ..services.db import get_summary_text, init_db

console = Console()

ANALYZE_PROMPT = """\
Here is my AI usage data across feature branches:

{summary}

Analyze cost patterns and suggest optimizations. Be specific and actionable. \
Focus on: which features are expensive, whether model choices are optimal, \
and concrete ways to reduce cost while maintaining productivity."""


def analyze() -> None:
    init_db()
    summary = get_summary_text()

    if summary.startswith("No usage"):
        console.print("[yellow]No usage data to analyze yet. Run some prompts first.[/yellow]")
        return

    console.print("[dim]Analyzing usage patterns...[/dim]")
    console.print()

    result = run_claude(ANALYZE_PROMPT.format(summary=summary))

    console.print(Panel(result.response, title="Cost Analysis", border_style="cyan"))
