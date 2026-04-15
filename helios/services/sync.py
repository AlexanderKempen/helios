from __future__ import annotations

import json
from pathlib import Path

from .cost import calculate_cost
from .db import get_sync_offset, insert_event, set_sync_offset

CLAUDE_DIR = Path.home() / ".claude" / "projects"


def _strip_branch_prefix(branch: str) -> str:
    for prefix in ("feature/", "feat/", "bugfix/", "fix/", "hotfix/"):
        if branch.startswith(prefix):
            return branch[len(prefix):]
    return branch


def _find_jsonl_files() -> list[Path]:
    if not CLAUDE_DIR.exists():
        return []
    return sorted(CLAUDE_DIR.glob("*/*.jsonl"))


def sync_claude_sessions() -> int:
    """Import new usage events from Claude Code session logs. Returns count of new events."""
    imported = 0
    for jsonl_path in _find_jsonl_files():
        file_key = str(jsonl_path)
        offset = get_sync_offset(file_key)
        file_size = jsonl_path.stat().st_size
        if offset >= file_size:
            continue

        new_offset = offset
        with open(jsonl_path, "r") as f:
            f.seek(offset)
            for line in f:
                new_offset += len(line.encode("utf-8"))
                imported += _process_line(line)

        set_sync_offset(file_key, new_offset)

    return imported


def _process_line(line: str) -> int:
    """Process a single JSONL line. Returns 1 if an event was inserted, 0 otherwise."""
    try:
        data = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return 0

    if data.get("type") != "assistant":
        return 0

    message = data.get("message", {})
    usage = message.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    if input_tokens == 0 and output_tokens == 0:
        return 0

    # Cache tokens count as input for cost purposes
    cache_creation = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    total_input = input_tokens + cache_creation + cache_read

    model = message.get("model")
    branch = data.get("gitBranch", "unknown")
    feature = _strip_branch_prefix(branch) if branch else "unknown"
    timestamp = data.get("timestamp")

    cost = calculate_cost(total_input, output_tokens, model)

    insert_event(
        feature=feature,
        model=model,
        tokens_in=total_input,
        tokens_out=output_tokens,
        total_tokens=total_input + output_tokens,
        cost=cost,
        source="claude-code",
        timestamp=timestamp,
    )
    return 1
