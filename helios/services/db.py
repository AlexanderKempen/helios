from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path.home() / ".helios" / "helios.db"
SCHEMA = Path(__file__).parent.parent / "db" / "schema.sql"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript(SCHEMA.read_text())
    conn.close()


def insert_event(
    feature: str,
    model: str | None,
    tokens_in: int,
    tokens_out: int,
    total_tokens: int,
    cost: float,
    source: str = "cli",
    timestamp: str | None = None,
) -> None:
    conn = _connect()
    conn.execute(
        """
        INSERT INTO events (timestamp, feature, model, tokens_in, tokens_out, total_tokens, cost, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp or datetime.now(timezone.utc).isoformat(),
            feature,
            model,
            tokens_in,
            tokens_out,
            total_tokens,
            cost,
            source,
        ),
    )
    conn.commit()
    conn.close()


def get_sync_offset(file_path: str) -> int:
    conn = _connect()
    row = conn.execute(
        "SELECT last_offset FROM sync_state WHERE file_path = ?", (file_path,)
    ).fetchone()
    conn.close()
    return row["last_offset"] if row else 0


def set_sync_offset(file_path: str, offset: int) -> None:
    conn = _connect()
    conn.execute(
        """
        INSERT INTO sync_state (file_path, last_offset) VALUES (?, ?)
        ON CONFLICT(file_path) DO UPDATE SET last_offset = excluded.last_offset
        """,
        (file_path, offset),
    )
    conn.commit()
    conn.close()


def get_report() -> list[dict]:
    """Aggregate usage per feature, sorted by total cost descending."""
    conn = _connect()
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
    conn.close()
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
