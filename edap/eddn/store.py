"""SQLite store of the latest EDDN market snapshot per station (no price history).

Writes are batched: callers apply updates and call `commit()` periodically.
WAL mode lets route queries read from their own connection while the listener writes.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from edap.eddn.messages import EddnUpdate, MarketSnapshot, StationInfo, SystemPosition, is_carrier_station

_SCHEMA = """
CREATE TABLE IF NOT EXISTS system (
    address INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS system_name ON system (name COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS station (
    market_id INTEGER PRIMARY KEY,
    system_address INTEGER NOT NULL,
    system_name TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    dist_ls REAL,
    max_pad TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS market (
    market_id INTEGER PRIMARY KEY,
    system_name TEXT NOT NULL,
    station_name TEXT NOT NULL,
    is_carrier INTEGER NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS market_updated_at ON market (updated_at);
CREATE TABLE IF NOT EXISTS price (
    market_id INTEGER NOT NULL,
    commodity TEXT NOT NULL,
    buy INTEGER NOT NULL,
    sell INTEGER NOT NULL,
    supply INTEGER NOT NULL,
    demand INTEGER NOT NULL,
    PRIMARY KEY (market_id, commodity)
) WITHOUT ROWID;
"""


@dataclass(frozen=True)
class EddnStoreCounts:
    systems: int
    stations: int
    markets: int
    prices: int
    oldest_market_at: float | None
    newest_market_at: float | None


class EddnStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection
        self._db.executescript(_SCHEMA)
        # The listener thread writes while other threads read counts through the same connection.
        self._lock = threading.RLock()

    @classmethod
    def open(cls, path: Path) -> "EddnStore":
        path.parent.mkdir(parents=True, exist_ok=True)
        # The listener thread owns writes; the connection is created before it starts.
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return cls(connection)

    def apply(self, update: EddnUpdate) -> bool:
        """Apply one update; False when the stored data is already as new or newer."""
        with self._lock:
            return self._apply(update)

    def _apply(self, update: EddnUpdate) -> bool:
        if isinstance(update, MarketSnapshot):
            return self._apply_market(update)
        if isinstance(update, SystemPosition):
            return self._apply_system(update)
        return self._apply_station(update)

    def commit(self) -> None:
        with self._lock:
            self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.commit()
            self._db.close()

    def prune(self, *, older_than: float) -> int:
        """Drop markets (and their prices) last updated before `older_than`."""
        stale = "SELECT market_id FROM market WHERE updated_at < ?"
        with self._lock:
            self._db.execute(f"DELETE FROM price WHERE market_id IN ({stale})", (older_than,))
            removed = self._db.execute("DELETE FROM market WHERE updated_at < ?", (older_than,)).rowcount
            self._db.commit()
        return removed

    def counts(self) -> EddnStoreCounts:
        with self._lock:
            return self._counts()

    def _counts(self) -> EddnStoreCounts:
        def scalar(sql: str) -> int:
            return int(self._db.execute(sql).fetchone()[0])

        oldest, newest = self._db.execute("SELECT MIN(updated_at), MAX(updated_at) FROM market").fetchone()
        return EddnStoreCounts(
            systems=scalar("SELECT COUNT(*) FROM system"),
            stations=scalar("SELECT COUNT(*) FROM station"),
            markets=scalar("SELECT COUNT(*) FROM market"),
            prices=scalar("SELECT COUNT(*) FROM price"),
            oldest_market_at=oldest,
            newest_market_at=newest,
        )

    def _apply_market(self, snapshot: MarketSnapshot) -> bool:
        row = self._db.execute(
            "SELECT updated_at FROM market WHERE market_id = ?", (snapshot.market_id,)
        ).fetchone()
        if row is not None and row[0] >= snapshot.timestamp:
            return False
        self._db.execute(
            "INSERT OR REPLACE INTO market (market_id, system_name, station_name, is_carrier, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                snapshot.market_id,
                snapshot.system_name,
                snapshot.station_name,
                int(snapshot.is_carrier),
                snapshot.timestamp,
            ),
        )
        self._db.execute("DELETE FROM price WHERE market_id = ?", (snapshot.market_id,))
        self._db.executemany(
            "INSERT INTO price (market_id, commodity, buy, sell, supply, demand) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (snapshot.market_id, price.name, price.buy, price.sell, price.supply, price.demand)
                for price in snapshot.prices
            ],
        )
        return True

    def _apply_system(self, position: SystemPosition) -> bool:
        cursor = self._db.execute(
            "INSERT INTO system (address, name, x, y, z, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (address) DO UPDATE SET name = excluded.name, x = excluded.x, y = excluded.y,"
            " z = excluded.z, updated_at = excluded.updated_at WHERE excluded.updated_at >= system.updated_at",
            (position.address, position.name, position.x, position.y, position.z, position.timestamp),
        )
        return cursor.rowcount > 0

    def _apply_station(self, station: StationInfo) -> bool:
        cursor = self._db.execute(
            "INSERT INTO station (market_id, system_address, system_name, name, type, dist_ls, max_pad, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (market_id) DO UPDATE SET system_address = excluded.system_address,"
            " system_name = excluded.system_name, name = excluded.name, type = excluded.type,"
            " dist_ls = COALESCE(excluded.dist_ls, station.dist_ls),"
            " max_pad = CASE WHEN excluded.max_pad != '' THEN excluded.max_pad ELSE station.max_pad END,"
            " updated_at = excluded.updated_at WHERE excluded.updated_at >= station.updated_at",
            (
                station.market_id,
                station.system_address,
                station.system_name,
                station.name,
                station.type,
                station.dist_ls,
                station.max_pad,
                station.timestamp,
            ),
        )
        if cursor.rowcount > 0 and is_carrier_station(station.name, station.type):
            self._db.execute("UPDATE market SET is_carrier = 1 WHERE market_id = ?", (station.market_id,))
        return cursor.rowcount > 0
