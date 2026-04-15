import typer

from .commands.analyze import analyze as _analyze
from .commands.estimate import estimate as _estimate
from .commands.report import report as _report
from .commands.run import run as _run
from .commands.start import start as _start
from .commands.sync import sync as _sync

app = typer.Typer(
    name="helios",
    help="Track and estimate LLM usage for git feature branches.",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def start():
    """Start tracking for the current feature branch."""
    _start()


@app.command()
def run(prompt: str = typer.Argument(..., help="Prompt to send to Claude")):
    """Run a prompt through Claude and track usage."""
    _run(prompt)


@app.command()
def report():
    """Show aggregated AI usage per feature branch."""
    _report()


@app.command()
def analyze():
    """Analyze cost patterns using Claude (meta-analysis)."""
    _analyze()


@app.command()
def sync():
    """Import usage from Claude Code interactive sessions."""
    _sync()


@app.command()
def estimate(
    input: str = typer.Argument(..., help="Prompt string or path to a markdown file"),
    repo_context: bool = typer.Option(False, "--repo-context", help="Include file tree and manifest signals"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Estimate cost and scope before running a prompt."""
    _estimate(input, repo_context=repo_context, json_output=json)


if __name__ == "__main__":
    app()
