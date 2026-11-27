"""SQLite store of the latest market snapshot per station (no price history) plus system, station and carrier facts.

Hub and standalone Control Rooms always open it; a peer never does. EDDN, our own journal and
Market.json, and Ardent all write into it with the same newest-wins rule.
Writes are batched: callers apply updates and call `commit()` periodically.
WAL mode lets route queries read from their own connection while the listener writes.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import closing
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from edcr.eddn.messages import (
    CarrierName,
    CarrierSighting,
    EddnUpdate,
    MarketSnapshot,
    StationInfo,
    StationTypeSeen,
    SystemPosition,
    is_carrier_station,
)

SCHEMA_VERSION = 1

# Each step upgrades its input shape by one version, before additive schema setup.
# Steps must use db.execute only, never executescript or commit: the ladder owns transactions.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}


def migrate(db: sqlite3.Connection, *, target: int,
            migrations: Mapping[int, Callable[[sqlite3.Connection], None]],
            backup: Callable[[int, int], None]) -> int:
    start = db.execute("PRAGMA user_version").fetchone()[0]
    if start > target:
        raise ValueError(f"Market database schema {start} is newer than this code ({target})")
    version = start
    if version == 0:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone():
            return start
        version = 1  # Stores predating version metadata have the v1 shape.
    if version < target:
        for step in range(version, target):
            if step not in migrations:
                raise ValueError(f"Missing market schema migration {step} -> {step + 1}")
        backup(start, target)
        for step in range(version, target):
            with db:
                db.execute("BEGIN")
                migrations[step](db)
                db.execute(f"PRAGMA user_version = {step + 1}")
    elif start == 0:
        db.execute("PRAGMA user_version = 1")
    return start


def migrate_file(path: Path) -> None:
    """Upgrade a disposable downloaded copy; the published source is its backup."""
    def source_is_backup(start: int, target: int) -> None:
        pass

    with closing(sqlite3.connect(path)) as db:
        EddnStore(db, backup=source_is_backup)


_SIGHTING_REFRESH_S = 600.0

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
CREATE TABLE IF NOT EXISTS station_services_seen (
    market_id INTEGER PRIMARY KEY,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS station_service (
    service TEXT NOT NULL,
    market_id INTEGER NOT NULL,
    PRIMARY KEY (service, market_id)
) WITHOUT ROWID;
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
-- Only some commodity messages carry a carrier's access, so the last one seen is kept apart from the market row.
CREATE TABLE IF NOT EXISTS carrier_access (
    market_id INTEGER PRIMARY KEY,
    access TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS carrier_name (
    callsign TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    updated_at REAL NOT NULL
);
-- Where each carrier's signal was last seen, and when our own journal last listed every carrier in a system.
CREATE TABLE IF NOT EXISTS carrier_seen (
    callsign TEXT PRIMARY KEY,
    system_address INTEGER NOT NULL,
    seen_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS carrier_scan (
    system_address INTEGER PRIMARY KEY,
    scanned_at REAL NOT NULL
);
"""


@dataclass(frozen=True)
class SnapshotImport:
    """Rows accepted from a snapshot; carriers sums access, names, sightings and scans."""
    markets: int
    prices: int
    stations: int
    systems: int
    carriers: int
    # Number of accepted station service lists, including known empty lists.
    services: int = 0


@dataclass(frozen=True)
class EddnStoreCounts:
    systems: int
    stations: int
    markets: int
    prices: int
    oldest_market_at: float | None
    newest_market_at: float | None


class EddnStore:
    def __init__(self, connection: sqlite3.Connection, *, backup: Callable[[int, int], None]) -> None:
        self._db = connection
        migrate(connection, target=SCHEMA_VERSION, migrations=MIGRATIONS, backup=backup)
        self._db.executescript(_SCHEMA)
        if self._db.execute("PRAGMA user_version").fetchone()[0] == 0:
            self._db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        # The listener thread writes while other threads read counts through the same connection.
        self._lock = threading.RLock()

    @classmethod
    def open(cls, path: Path) -> "EddnStore":
        path.parent.mkdir(parents=True, exist_ok=True)
        # The listener thread owns writes; the connection is created before it starts.
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        def backup(start: int, target: int) -> None:
            destination = path.with_name(f"{path.name}.pre-v{target}")
            # A retry after a failed migration can encounter the previous backup.
            staged = destination.with_name(destination.name + ".tmp")
            if not destination.exists():
                staged.unlink(missing_ok=True)
                connection.execute("VACUUM INTO ?", (str(staged),))
                staged.replace(destination)
            for old in path.parent.iterdir():
                if old.name.startswith(path.name + ".pre-v") and old != destination:
                    old.unlink()

        try:
            return cls(connection, backup=backup)
        except BaseException:
            connection.close()
            raise

    def apply(self, update: EddnUpdate) -> bool:
        """Apply one update; False when the stored data is already as new or newer."""
        with self._lock:
            return self._apply(update)

    def save(self, updates: list[EddnUpdate]) -> None:
        """Apply several updates and commit them, as the journal and Ardent writers do."""
        with self._lock:
            for update in updates:
                self._apply(update)
            self._db.commit()

    def _apply(self, update: EddnUpdate) -> bool:
        if isinstance(update, MarketSnapshot):
            return self._apply_market(update)
        if isinstance(update, SystemPosition):
            return self._apply_system(update)
        if isinstance(update, StationTypeSeen):
            return self._apply_station_type(update)
        if isinstance(update, CarrierName):
            return self._apply_carrier_name(update)
        if isinstance(update, CarrierSighting):
            return self._apply_carrier_sighting(update)
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

    def import_database(self, path: Path, *, min_updated_at: float) -> SnapshotImport:
        """Merge a frozen database atomically, preserving already pending listener writes.

        Carrier scan membership is represented by matching sighting/scan timestamps.
        Counts include accepted equal-time facts, just as apply() does.
        """
        with self._lock:
            db = self._db
            # Pending listener updates belong to the caller, not the import transaction.
            db.commit()
            db.execute("ATTACH DATABASE ? AS snapshot", (str(path.resolve(strict=True)),))
            try:
                version = db.execute("PRAGMA snapshot.user_version").fetchone()[0]
                if version != SCHEMA_VERSION:
                    raise ValueError(f"Unsupported market schema {version}; expected {SCHEMA_VERSION}")
                db.execute("BEGIN")
                db.execute("CREATE TEMP TABLE import_markets (market_id INTEGER PRIMARY KEY)")
                db.execute(
                    "INSERT INTO import_markets SELECT s.market_id FROM snapshot.market s"
                    " LEFT JOIN main.market m USING (market_id)"
                    " WHERE s.updated_at >= ? AND (m.market_id IS NULL OR s.updated_at > m.updated_at)",
                    (min_updated_at,),
                )
                db.execute("DELETE FROM main.price WHERE market_id IN (SELECT market_id FROM import_markets)")
                markets = db.execute(
                    "INSERT OR REPLACE INTO main.market SELECT s.* FROM snapshot.market s"
                    " JOIN import_markets USING (market_id)"
                ).rowcount
                prices = db.execute(
                    "INSERT INTO main.price SELECT s.* FROM snapshot.price s JOIN import_markets USING (market_id)"
                ).rowcount
                systems = db.execute(
                    "INSERT INTO main.system SELECT * FROM snapshot.system WHERE true"
                    " ON CONFLICT(address) DO UPDATE SET name=excluded.name, x=excluded.x,"
                    " y=excluded.y, z=excluded.z, updated_at=excluded.updated_at"
                    " WHERE excluded.updated_at >= system.updated_at"
                ).rowcount
                # Capture accepted station facts before upsert, so older facts cannot mark a market.
                db.execute(
                    "CREATE TEMP TABLE import_stations AS SELECT s.* FROM snapshot.station s"
                    " LEFT JOIN main.station t USING (market_id)"
                    " WHERE t.market_id IS NULL OR s.updated_at >= t.updated_at"
                )
                stations = db.execute(
                    "INSERT INTO main.station SELECT * FROM import_stations WHERE true"
                    " ON CONFLICT(market_id) DO UPDATE SET system_address=excluded.system_address,"
                    " system_name=excluded.system_name, name=excluded.name, type=excluded.type,"
                    " dist_ls=COALESCE(excluded.dist_ls, station.dist_ls),"
                    " max_pad=CASE WHEN excluded.max_pad != '' THEN excluded.max_pad ELSE station.max_pad END,"
                    " updated_at=excluded.updated_at"
                ).rowcount
                db.execute(
                    "UPDATE main.market SET is_carrier=1 WHERE market_id IN"
                    " (SELECT market_id FROM import_stations WHERE type='FleetCarrier'"
                    " OR name GLOB '[A-Z0-9][A-Z0-9][A-Z0-9]-[A-Z0-9][A-Z0-9][A-Z0-9]')"
                )
                carriers = db.execute(
                    "INSERT INTO main.carrier_access SELECT * FROM snapshot.carrier_access WHERE true"
                    " ON CONFLICT(market_id) DO UPDATE SET access=excluded.access, updated_at=excluded.updated_at"
                    " WHERE excluded.updated_at >= carrier_access.updated_at"
                ).rowcount
                carriers += db.execute(
                    "INSERT INTO main.carrier_name SELECT * FROM snapshot.carrier_name WHERE true"
                    " ON CONFLICT(callsign) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at"
                    " WHERE excluded.name != carrier_name.name AND excluded.updated_at >= carrier_name.updated_at"
                ).rowcount
                carriers += db.execute(
                    "INSERT INTO main.carrier_seen SELECT * FROM snapshot.carrier_seen WHERE true"
                    " ON CONFLICT(callsign) DO UPDATE SET system_address=excluded.system_address, seen_at=excluded.seen_at"
                    " WHERE excluded.seen_at > carrier_seen.seen_at AND"
                    " (excluded.system_address != carrier_seen.system_address OR"
                    " excluded.seen_at >= carrier_seen.seen_at + ? OR EXISTS"
                    " (SELECT 1 FROM snapshot.carrier_scan s WHERE s.system_address=excluded.system_address"
                    " AND s.scanned_at=excluded.seen_at))", (_SIGHTING_REFRESH_S,),
                ).rowcount
                carriers += db.execute(
                    "INSERT INTO main.carrier_scan SELECT * FROM snapshot.carrier_scan WHERE true"
                    " ON CONFLICT(system_address) DO UPDATE SET scanned_at=excluded.scanned_at"
                    " WHERE excluded.scanned_at > carrier_scan.scanned_at"
                ).rowcount
                services = self._import_services()
                db.execute("DROP TABLE import_stations")
                db.execute("DROP TABLE import_markets")
                db.commit()
                return SnapshotImport(markets, prices, stations, systems, carriers, services)
            except BaseException:
                db.rollback()
                raise
            finally:
                db.execute("DETACH DATABASE snapshot")

    def _import_services(self) -> int:
        db = self._db
        if db.execute(
            "SELECT 1 FROM snapshot.sqlite_master WHERE type='table' AND name='station_services_seen'"
        ).fetchone() is None:
            return 0
        db.execute(
            "CREATE TEMP TABLE import_services AS SELECT s.* FROM snapshot.station_services_seen s"
            " LEFT JOIN main.station_services_seen t USING (market_id)"
            " WHERE t.market_id IS NULL OR s.updated_at > t.updated_at"
        )
        db.execute("DELETE FROM main.station_service WHERE market_id IN (SELECT market_id FROM import_services)")
        db.execute(
            "INSERT OR IGNORE INTO main.station_service SELECT lower(s.service), s.market_id"
            " FROM snapshot.station_service s JOIN import_services USING (market_id)"
        )
        accepted = db.execute(
            "INSERT OR REPLACE INTO main.station_services_seen SELECT * FROM import_services"
        ).rowcount
        db.execute("DROP TABLE import_services")
        return accepted

    def _apply_market(self, snapshot: MarketSnapshot) -> bool:
        if snapshot.carrier_access:
            self._db.execute(
                "INSERT INTO carrier_access (market_id, access, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT (market_id) DO UPDATE SET access = excluded.access, updated_at = excluded.updated_at"
                " WHERE excluded.updated_at >= carrier_access.updated_at",
                (snapshot.market_id, snapshot.carrier_access, snapshot.timestamp),
            )
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
        services_changed = self._apply_services(station)
        return cursor.rowcount > 0 or services_changed

    def _apply_services(self, station: StationInfo) -> bool:
        if station.services is None:
            return False
        cursor = self._db.execute(
            "INSERT INTO station_services_seen (market_id, updated_at) VALUES (?, ?)"
            " ON CONFLICT (market_id) DO UPDATE SET updated_at=excluded.updated_at"
            " WHERE excluded.updated_at >= station_services_seen.updated_at",
            (station.market_id, station.timestamp),
        )
        if cursor.rowcount == 0:
            return False
        self._db.execute("DELETE FROM station_service WHERE market_id = ?", (station.market_id,))
        self._db.executemany(
            "INSERT INTO station_service (service, market_id) VALUES (?, ?)",
            [(service, station.market_id) for service in dict.fromkeys(s.lower() for s in station.services)],
        )
        return True

    def _apply_station_type(self, seen: StationTypeSeen) -> bool:
        """Set a known station's type; a new row needs the system address, from the system table."""
        cursor = self._db.execute(
            "UPDATE station SET type = ?, updated_at = ? WHERE market_id = ? AND updated_at <= ?",
            (seen.type, seen.timestamp, seen.market_id, seen.timestamp),
        )
        if cursor.rowcount > 0:
            return True
        if self._db.execute("SELECT 1 FROM station WHERE market_id = ?", (seen.market_id,)).fetchone() is not None:
            return False
        row = self._db.execute(
            "SELECT address FROM system WHERE name = ? COLLATE NOCASE ORDER BY updated_at DESC LIMIT 1",
            (seen.system_name,),
        ).fetchone()
        if row is None:
            return False
        return self._apply_station(StationInfo(
            market_id=seen.market_id, system_address=row[0], system_name=seen.system_name, name=seen.name,
            type=seen.type, dist_ls=None, max_pad="", timestamp=seen.timestamp, services=None,
        ))

    def _apply_carrier_name(self, carrier: CarrierName) -> bool:
        """Signals repeat the same names many times a minute, so only a new or changed name is written."""
        cursor = self._db.execute(
            "INSERT INTO carrier_name (callsign, name, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT (callsign) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at"
            " WHERE excluded.name != carrier_name.name AND excluded.updated_at >= carrier_name.updated_at",
            (carrier.callsign, carrier.name, carrier.timestamp),
        )
        return cursor.rowcount > 0

    def _apply_carrier_sighting(self, sighting: CarrierSighting) -> bool:
        """EDDN repeats the same sightings many times a minute, so one in the same system is written only
        every `_SIGHTING_REFRESH_S`; a complete batch is always written, since its members must match its scan time."""
        if sighting.complete:
            self._db.execute(
                "INSERT INTO carrier_scan (system_address, scanned_at) VALUES (?, ?)"
                " ON CONFLICT (system_address) DO UPDATE SET scanned_at = excluded.scanned_at"
                " WHERE excluded.scanned_at > carrier_scan.scanned_at",
                (sighting.system_address, sighting.timestamp),
            )
        refresh = 0.0 if sighting.complete else _SIGHTING_REFRESH_S
        cursor = self._db.execute(
            "INSERT INTO carrier_seen (callsign, system_address, seen_at) VALUES (?, ?, ?)"
            " ON CONFLICT (callsign) DO UPDATE SET system_address = excluded.system_address, seen_at = excluded.seen_at"
            " WHERE excluded.seen_at > carrier_seen.seen_at AND (excluded.system_address != carrier_seen.system_address"
            " OR excluded.seen_at >= carrier_seen.seen_at + ?)",
            (sighting.callsign, sighting.system_address, sighting.timestamp, refresh),
        )
        return cursor.rowcount > 0
