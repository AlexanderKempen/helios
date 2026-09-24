import sqlite3

from helios.services.db import SCHEMA_VERSION, db_path, get_report, init_db, insert_event

LEGACY_SCHEMA = """
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    feature TEXT NOT NULL,
    model TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    total_tokens INTEGER,
    cost REAL,
    source TEXT DEFAULT 'cli'
);
CREATE TABLE sync_state (
    file_path TEXT PRIMARY KEY,
    last_offset INTEGER NOT NULL DEFAULT 0
);
"""


def _legacy_db():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(LEGACY_SCHEMA)
    return conn


def test_init_db_is_idempotent():
    init_db()
    insert_event("csv-export", "claude-sonnet-5", 10, 5, 15, 0.01, timestamp="2026-01-01T00:00:00Z")
    init_db()
    assert sum(r["calls"] for r in get_report()) == 1


def test_duplicate_events_are_ignored():
    init_db()
    args = ("csv-export", "claude-sonnet-5", 10, 5, 15, 0.01)
    assert insert_event(*args, timestamp="2026-01-01T00:00:00Z") == 1
    assert insert_event(*args, timestamp="2026-01-01T00:00:00Z") == 0


def test_v1_database_is_migrated_and_deduplicated():
    conn = _legacy_db()
    for _ in range(3):
        conn.execute(
            "INSERT INTO events (timestamp, feature, tokens_in, tokens_out, total_tokens, cost, source)"
            " VALUES ('2026-01-01T00:00:00Z', 'csv-export', 10, 5, 15, 0.01, 'claude-code')"
        )
    conn.execute("INSERT INTO sync_state (file_path, last_offset) VALUES ('/tmp/a.jsonl', 42)")
    conn.commit()
    conn.close()

    init_db()

    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    state = conn.execute("SELECT * FROM sync_state").fetchone()
    assert (state["last_offset"], state["file_size"]) == (42, 42)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    conn.close()
