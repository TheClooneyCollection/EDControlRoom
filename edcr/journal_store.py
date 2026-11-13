"""Every node's journal events, kept as written in one SQLite file the hub (or standalone) owns.

A line is identified by its node, journal file and line number, so a line passed on twice is
stored once. Chat and the friends list never get in.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

# Chat and the friends list help no analysis and are the only private content in a journal.
SKIPPED_EVENTS = frozenset({"ReceiveText", "SendText", "Friends"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS journal_event (
    node_id TEXT NOT NULL,
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    event TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY (node_id, file, line)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS journal_event_time ON journal_event (event, timestamp);
"""


@dataclass(frozen=True)
class JournalLine:
    """One complete journal line and its 1-based number in its file."""
    line: int
    text: str


def parse_line(text: str) -> tuple[float, str] | None:
    """The line's timestamp and event name, or None when it is not an event worth keeping."""
    try:
        event = json.loads(text)
    except ValueError:
        return None
    if not isinstance(event, dict):
        return None
    name, stamp = event.get("event"), event.get("timestamp")
    if not isinstance(name, str) or not name or name in SKIPPED_EVENTS or not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp(), name
    except ValueError:
        return None


class JournalStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection
        self._lock = threading.Lock()
        self._db.executescript(_SCHEMA)
        self._db.commit()

    @classmethod
    def open(cls, path: Path) -> "JournalStore":
        path.parent.mkdir(parents=True, exist_ok=True)
        # The journal sync thread and the hub link both write.
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        return cls(connection)

    def add(self, node_id: str, file: str, lines: Iterable[JournalLine]) -> int:
        """Store a file's lines for a node; returns how many were new."""
        rows = []
        for item in lines:
            parsed = parse_line(item.text)
            if parsed is not None:
                rows.append((node_id, file, item.line, parsed[0], parsed[1], item.text))
        if not rows:
            return 0
        with self._lock:
            before = self._db.total_changes
            self._db.executemany(
                "INSERT OR IGNORE INTO journal_event (node_id, file, line, timestamp, event, body)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            self._db.commit()
            return self._db.total_changes - before

    def counts(self) -> list[tuple[str, str, int]]:
        """(node id, event, count), most frequent first."""
        with self._lock:
            return self._db.execute(
                "SELECT node_id, event, COUNT(*) FROM journal_event GROUP BY node_id, event ORDER BY 3 DESC"
            ).fetchall()

    def close(self) -> None:
        with self._lock:
            self._db.close()
