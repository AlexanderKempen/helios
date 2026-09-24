from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass

from .cost import estimate_tokens


@dataclass
class ClaudeResult:
    response: str
    model: str | None
    tokens_in: int
    tokens_out: int
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    estimated: bool = False

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


def run_claude(prompt: str) -> ClaudeResult:
    """Run a prompt through Claude Code CLI and parse the result."""
    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "json", prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        print("Error: 'claude' CLI not found. Install it first: https://docs.anthropic.com/en/docs/claude-code", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: Claude CLI timed out after 5 minutes.", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        print(f"Error: Claude CLI failed (exit {result.returncode}): {stderr}", file=sys.stderr)
        sys.exit(1)

    return _parse_response(result.stdout, prompt)


def _parse_response(raw: str, prompt: str = "") -> ClaudeResult:
    """Parse Claude CLI JSON output, falling back to plain text estimation."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return _estimated(raw.strip(), prompt, model=None)

    response = str(data.get("result", raw.strip()))
    model = data.get("model")

    usage = data.get("usage", {})
    tokens_in = usage.get("input_tokens", 0)
    tokens_out = usage.get("output_tokens", 0)

    if tokens_in == 0 and tokens_out == 0:
        return _estimated(response, prompt, model=model)

    return ClaudeResult(
        response=response,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
        cache_read_tokens=usage.get("cache_read_input_tokens", 0),
    )


def _estimated(response: str, prompt: str, model: str | None) -> ClaudeResult:
    """Approximate usage when the CLI reports none: prompt in, response out."""
    return ClaudeResult(
        response=response,
        model=model,
        tokens_in=estimate_tokens(prompt) if prompt else 0,
        tokens_out=estimate_tokens(response),
        estimated=True,
    )
