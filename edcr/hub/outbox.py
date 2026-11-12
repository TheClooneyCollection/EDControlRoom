"""The peer's outbox: what must reach the hub, kept on disk until the hub acknowledges it.

Items leave in the order they were added. Each item has a key (a market's id and game timestamp,
a fact's own identity and timestamp); a key already queued once is not queued again, so the
journal replay and market rescan at every start do not resend what the hub already has.
Haul run keys never expire: the whole run history is rescanned at every start, and a run older
than 30 days must not go up again.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Keys are remembered this long; older ones may be queued again, which the hub shrugs off.
SEEN_KEY_DAYS = 30.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS item (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS seen (
    key TEXT PRIMARY KEY,
    added_at REAL NOT NULL
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS kept (
    key TEXT PRIMARY KEY
) WITHOUT ROWID;
"""


@dataclass(frozen=True)
class OutboxItem:
    seq: int
    kind: str
    body: Any


class Outbox:
    def __init__(self, connection: sqlite3.Connection, *, now: float) -> None:
        self._db = connection
        self._lock = threading.Lock()
        self._db.executescript(_SCHEMA)
        self._db.execute("DELETE FROM seen WHERE added_at < ?", (now - SEEN_KEY_DAYS * 86400,))
        self._db.commit()

    @classmethod
    def open(cls, path: Path, *, now: float) -> "Outbox":
        path.parent.mkdir(parents=True, exist_ok=True)
        # The journal, market watcher and link threads all add or remove items.
        return cls(sqlite3.connect(path, check_same_thread=False), now=now)

    def add(self, kind: str, body: Any, *, key: str, now: float, forever: bool = False) -> int | None:
        """Queue one item; None when its key was queued before. A `forever` key is never forgotten."""
        with self._lock:
            if forever:
                added = self._db.execute("INSERT OR IGNORE INTO kept (key) VALUES (?)", (key,)).rowcount
            else:
                added = self._db.execute("INSERT OR IGNORE INTO seen (key, added_at) VALUES (?, ?)", (key, now)).rowcount
            if added == 0:
                return None
            seq = self._db.execute("INSERT INTO item (kind, body) VALUES (?, ?)", (kind, json.dumps(body))).lastrowid
            self._db.commit()
            return int(seq)

    def pending(self, *, after: int) -> list[OutboxItem]:
        with self._lock:
            rows = self._db.execute("SELECT seq, kind, body FROM item WHERE seq > ? ORDER BY seq", (after,)).fetchall()
        return [OutboxItem(seq, kind, json.loads(body)) for seq, kind, body in rows]

    def remove(self, seq: int) -> None:
        with self._lock:
            self._db.execute("DELETE FROM item WHERE seq = ?", (seq,))
            self._db.commit()

    def count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM item").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._db.close()
