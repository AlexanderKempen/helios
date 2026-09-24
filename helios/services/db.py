from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = Path(__file__).parent.parent / "db" / "schema.sql"
SCHEMA_VERSION = 2


def db_path() -> Path:
    """Location of the local usage database (override with HELIOS_DB)."""
    override = os.environ.get("HELIOS_DB")
    if override:
        return Path(override)
    return Path.home() / ".helios" / "helios.db"


@dataclass
class Event:
    feature: str
    model: str | None
    tokens_in: int
    tokens_out: int
    total_tokens: int
    cost: float
    source: str = "cli"
    timestamp: str | None = None


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        _migrate(conn)
        conn.executescript(SCHEMA.read_text())
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _migrate(conn: sqlite3.Connection) -> None:
    """Bring pre-v2 databases up to a shape the current schema can apply."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= SCHEMA_VERSION:
        return

    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

    if "sync_state" in tables:
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(sync_state)")}
        if "file_size" not in columns:
            conn.execute("ALTER TABLE sync_state ADD COLUMN file_size INTEGER NOT NULL DEFAULT 0")
            conn.execute("UPDATE sync_state SET file_size = last_offset")

    if "events" in tables:
        # The v2 unique index cannot be created while historical duplicates exist.
        conn.execute(
            """
            DELETE FROM events WHERE id NOT IN (
                SELECT MIN(id) FROM events
                GROUP BY timestamp, feature, source, tokens_in, tokens_out
            )
            """
        )


def insert_event(
    feature: str,
    model: str | None,
    tokens_in: int,
    tokens_out: int,
    total_tokens: int,
    cost: float,
    source: str = "cli",
    timestamp: str | None = None,
) -> int:
    """Insert one event. Returns the number of rows actually written (0 if duplicate)."""
    return insert_events(
        [Event(feature, model, tokens_in, tokens_out, total_tokens, cost, source, timestamp)]
    )


def insert_events(events: Iterable[Event]) -> int:
    """Insert events in a single transaction, ignoring duplicates."""
    rows = [
        (
            e.timestamp or datetime.now(timezone.utc).isoformat(),
            e.feature,
            e.model,
            e.tokens_in,
            e.tokens_out,
            e.total_tokens,
            e.cost,
            e.source,
        )
        for e in events
    ]
    if not rows:
        return 0

    with _connect() as conn:
        cursor = conn.executemany(
            """
            INSERT OR IGNORE INTO events
                (timestamp, feature, model, tokens_in, tokens_out, total_tokens, cost, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return cursor.rowcount


def get_sync_offset(file_path: str) -> tuple[int, int]:
    """Return (offset, size) recorded for a session log."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT last_offset, file_size FROM sync_state WHERE file_path = ?", (file_path,)
        ).fetchone()
    return (row["last_offset"], row["file_size"]) if row else (0, 0)


def set_sync_offset(file_path: str, offset: int, size: int) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sync_state (file_path, last_offset, file_size) VALUES (?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                last_offset = excluded.last_offset,
                file_size = excluded.file_size
            """,
            (file_path, offset, size),
        )


def get_report() -> list[dict]:
    """Aggregate usage per feature, sorted by total cost descending."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                feature,
                SUM(cost) AS total_cost,
                SUM(total_tokens) AS total_tokens,
                COUNT(*) AS calls,
                -- most-used model per feature
                (
                    SELECT model FROM events e2
                    WHERE e2.feature = e1.feature AND e2.model IS NOT NULL
                    GROUP BY model ORDER BY COUNT(*) DESC LIMIT 1
                ) AS top_model
            FROM events e1
            GROUP BY feature
            ORDER BY total_cost DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_summary_text() -> str:
    """Return a plain-text summary suitable for LLM analysis."""
    report = get_report()
    if not report:
        return "No usage data recorded yet."
    lines = ["AI Usage Summary:", ""]
    for r in report:
        lines.append(f"Feature: {r['feature']}")
        lines.append(f"  Cost: ${r['total_cost']:.2f}")
        lines.append(f"  Tokens: {r['total_tokens']:,}")
        lines.append(f"  Calls: {r['calls']}")
        lines.append(f"  Top model: {r['top_model'] or 'unknown'}")
        lines.append("")
    return "\n".join(lines)
