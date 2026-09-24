import json
import sqlite3

from helios.services.db import db_path, get_report, get_sync_offset, init_db
from helios.services.sync import claude_dir, sync_claude_sessions


def _assistant_line(timestamp: str, branch: str = "feature/csv-export", tokens_out: int = 50) -> str:
    return json.dumps({
        "type": "assistant",
        "timestamp": timestamp,
        "gitBranch": branch,
        "message": {
            "model": "claude-sonnet-5",
            "usage": {
                "input_tokens": 1000,
                "output_tokens": tokens_out,
                "cache_creation_input_tokens": 10,
                "cache_read_input_tokens": 100,
            },
        },
    }) + "\n"


def _write_session(lines: list[str]):
    path = claude_dir() / "project-a" / "session.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines))
    return path


def test_sync_imports_assistant_events_and_strips_branch_prefix():
    init_db()
    _write_session([_assistant_line("2026-01-01T00:00:00Z")])

    assert sync_claude_sessions() == 1

    rows = get_report()
    assert [r["feature"] for r in rows] == ["csv-export"]
    # cache tokens count towards input
    assert rows[0]["total_tokens"] == 1000 + 10 + 100 + 50


def test_sync_is_incremental_and_idempotent():
    init_db()
    path = _write_session([_assistant_line("2026-01-01T00:00:00Z")])
    sync_claude_sessions()

    assert sync_claude_sessions() == 0

    with path.open("a") as f:
        f.write(_assistant_line("2026-01-01T00:01:00Z"))
    assert sync_claude_sessions() == 1


def test_rotated_log_is_reread_without_duplicating_events():
    init_db()
    path = _write_session([
        _assistant_line("2026-01-01T00:00:00Z"),
        _assistant_line("2026-01-01T00:01:00Z"),
    ])
    assert sync_claude_sessions() == 2

    # Rotation: the file shrinks, so the stored offset now points past its end.
    path.write_text(_assistant_line("2026-01-01T00:02:00Z"))
    assert sync_claude_sessions() == 1

    offset, size = get_sync_offset(str(path))
    assert offset == size == path.stat().st_size
    assert sum(r["calls"] for r in get_report()) == 3


def test_replaying_the_same_events_is_deduplicated():
    init_db()
    path = _write_session([_assistant_line("2026-01-01T00:00:00Z")])
    sync_claude_sessions()

    # Same content, rewritten: offset resets but the unique index holds.
    path.write_text(_assistant_line("2026-01-01T00:00:00Z"))
    conn = sqlite3.connect(db_path())
    conn.execute("UPDATE sync_state SET last_offset = 0, file_size = 0")
    conn.commit()
    conn.close()

    assert sync_claude_sessions() == 0
    assert sum(r["calls"] for r in get_report()) == 1


def test_lines_without_usage_are_skipped():
    init_db()
    _write_session([
        json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n",
        json.dumps({"type": "assistant", "message": {"usage": {}}}) + "\n",
        "not json at all\n",
    ])
    assert sync_claude_sessions() == 0


def test_sync_without_claude_directory_is_a_noop():
    init_db()
    assert sync_claude_sessions() == 0
