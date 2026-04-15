from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..services.claude import run_claude
from ..services.cost import DEFAULT_PRICING
from ..services.heuristics import analyze_prompt
from ..services.repo_context import gather_repo_context

console = Console()

ESTIMATE_PROMPT = """\
You are a cost estimation engine for AI-driven software development.

Given a task description (and optional repo context), produce a structured JSON estimate.

## Task
{task}

{repo_section}

## Heuristic signals
- Prompt tokens: {prompt_tokens}
- Detected features: {feature_count}
- UI work: {has_ui}
- Backend work: {has_backend}
- Auth: {has_auth}
- Migration: {has_migration}
- Refactor: {has_refactor}
- Tests: {has_tests}
- Heuristic scope: {scope_label}
- Heuristic token range: {token_min:,} - {token_max:,}

## Instructions

Estimate the cost of having an AI coding agent (like Claude Code) implement this task.
Factor in likely iterations, debugging, and test cycles.

Return ONLY valid JSON with this exact schema:
{{
  "cost": {{ "min": <float>, "max": <float> }},
  "tokens": {{ "min": <int>, "max": <int> }},
  "scope": "<small|medium|large>",
  "files_touched": {{ "min": <int>, "max": <int> }},
  "risk": "<low|moderate|high>",
  "confidence": <float 0-1>,
  "ambiguities": ["<string>", ...],
  "acceptance_criteria": ["<string>", ...],
  "recommendation": "<safe_to_run|needs_clarification|high_risk>"
}}"""


def estimate(input_str: str, repo_context: bool = False, json_output: bool = False) -> None:
    task_text = _read_input(input_str)
    signals = analyze_prompt(task_text)

    repo_section = ""
    if repo_context:
        console.print("[dim]Gathering repo context...[/dim]")
        ctx = gather_repo_context()
        if ctx:
            repo_section = f"## Repo context\n{ctx}"

    token_min, token_max = signals.token_range
    prompt = ESTIMATE_PROMPT.format(
        task=task_text,
        repo_section=repo_section or "(no repo context provided)",
        prompt_tokens=signals.prompt_tokens,
        feature_count=signals.feature_count,
        has_ui=signals.has_ui,
        has_backend=signals.has_backend,
        has_auth=signals.has_auth,
        has_migration=signals.has_migration,
        has_refactor=signals.has_refactor,
        has_tests=signals.has_tests,
        scope_label=signals.scope_label,
        token_min=token_min,
        token_max=token_max,
    )

    console.print("[dim]Estimating...[/dim]")
    result = run_claude(prompt)

    data = _parse_estimate(result.response)
    if not data:
        console.print("[red]Failed to parse estimate from model response.[/red]")
        console.print(result.response)
        return

    _apply_pricing(data)

    if json_output:
        console.print(json.dumps(data, indent=2))
    else:
        _render(data)


def _read_input(input_str: str) -> str:
    path = Path(input_str)
    if path.exists() and path.is_file():
        return path.read_text(errors="ignore")
    return input_str


def _parse_estimate(raw: str) -> dict | None:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except (json.JSONDecodeError, ValueError):
                pass
    return None


def _apply_pricing(data: dict) -> None:
    """Ensure cost range reflects token estimates with current pricing."""
    tokens = data.get("tokens", {})
    t_min = tokens.get("min", 0)
    t_max = tokens.get("max", 0)
    if t_min and t_max and "cost" in data:
        input_price = DEFAULT_PRICING["input"]
        output_price = DEFAULT_PRICING["output"]
        avg_price = (input_price * 0.7 + output_price * 0.3) / 1_000_000
        data["cost"]["min"] = round(t_min * avg_price, 2)
        data["cost"]["max"] = round(t_max * avg_price, 2)


def _format_tokens(t: int) -> str:
    if t >= 1_000_000:
        return f"{t / 1_000_000:.1f}M"
    if t >= 1_000:
        return f"{t / 1_000:.0f}k"
    return str(t)


RISK_STYLE = {"low": "green", "moderate": "yellow", "high": "red"}
REC_LABELS = {
    "safe_to_run": ("Safe to run", "green"),
    "needs_clarification": ("Needs clarification", "yellow"),
    "high_risk": ("High risk", "red"),
}


def _render(data: dict) -> None:
    cost = data.get("cost", {})
    tokens = data.get("tokens", {})
    files = data.get("files_touched", {})
    risk = data.get("risk", "unknown")
    confidence = data.get("confidence", 0)
    rec = data.get("recommendation", "unknown")

    lines = Text()
    lines.append("Estimated cost:   ", style="dim")
    lines.append(f"${cost.get('min', 0):.2f} – ${cost.get('max', 0):.2f}\n", style="magenta")

    lines.append("Estimated tokens: ", style="dim")
    lines.append(f"{_format_tokens(tokens.get('min', 0))} – {_format_tokens(tokens.get('max', 0))}\n", style="cyan")

    lines.append("Scope:            ", style="dim")
    lines.append(f"{data.get('scope', 'unknown')}\n")

    lines.append("Files touched:    ", style="dim")
    lines.append(f"{files.get('min', '?')} – {files.get('max', '?')}\n")

    lines.append("Risk:             ", style="dim")
    lines.append(f"{risk}\n", style=RISK_STYLE.get(risk, ""))

    lines.append("Confidence:       ", style="dim")
    lines.append(f"{confidence:.0%}\n")

    rec_label, rec_style = REC_LABELS.get(rec, (rec, ""))
    lines.append("\nRecommendation:   ", style="dim")
    lines.append(rec_label, style=f"bold {rec_style}")

    ambiguities = data.get("ambiguities", [])
    if ambiguities:
        lines.append("\n\nAmbiguities:\n", style="dim")
        for a in ambiguities:
            lines.append(f"  - {a}\n", style="yellow")

    criteria = data.get("acceptance_criteria", [])
    if criteria:
        lines.append("\nAcceptance criteria:\n", style="dim")
        for c in criteria:
            lines.append(f"  - {c}\n", style="cyan")

    console.print()
    console.print(Panel(lines, title="[bold]helios estimate[/bold]", border_style="blue", padding=(1, 2)))
    console.print()
