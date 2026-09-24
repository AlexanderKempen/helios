from __future__ import annotations

import json
import os
from pathlib import Path

from .cost import calculate_cost
from .db import Event, get_sync_offset, insert_events, set_sync_offset
from .git import strip_branch_prefix


def claude_dir() -> Path:
    """Directory holding Claude Code session logs (override with CLAUDE_CONFIG_DIR)."""
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(override) if override else Path.home() / ".claude"
    return base / "projects"


def _find_jsonl_files() -> list[Path]:
    root = claude_dir()
    if not root.exists():
        return []
    return sorted(root.glob("*/*.jsonl"))


def sync_claude_sessions() -> int:
    """Import new usage events from Claude Code session logs. Returns count of new events."""
    imported = 0
    for jsonl_path in _find_jsonl_files():
        file_key = str(jsonl_path)
        offset, known_size = get_sync_offset(file_key)
        file_size = jsonl_path.stat().st_size

        # A shorter file means it was rotated or rewritten, so byte offsets from
        # the previous run point into unrelated content: re-read from the start.
        # Duplicate events are dropped by the unique index on insert.
        if file_size < known_size or offset > file_size:
            offset = 0

        if offset == file_size:
            continue

        events: list[Event] = []
        new_offset = offset
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            for line in f:
                new_offset += len(line.encode("utf-8"))
                event = _parse_line(line)
                if event:
                    events.append(event)

        imported += insert_events(events)
        set_sync_offset(file_key, new_offset, file_size)

    return imported


def _parse_line(line: str) -> Event | None:
    """Turn one JSONL line into an Event, or None if it carries no usage."""
    try:
        data = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None

    if data.get("type") != "assistant":
        return None

    message = data.get("message", {})
    usage = message.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    if input_tokens == 0 and output_tokens == 0:
        return None

    cache_creation = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    total_all_input = input_tokens + cache_creation + cache_read

    model = message.get("model")
    branch = data.get("gitBranch") or "unknown"

    cost = calculate_cost(
        input_tokens, output_tokens, model,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=cache_read,
    )

    return Event(
        feature=strip_branch_prefix(branch),
        model=model,
        tokens_in=total_all_input,
        tokens_out=output_tokens,
        total_tokens=total_all_input + output_tokens,
        cost=cost,
        source="claude-code",
        timestamp=data.get("timestamp"),
    )
