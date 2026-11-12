from __future__ import annotations

import json
import sqlite3
import threading
import time
import unittest
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory

from edcr.config import ConfigError, EddnConfig, load_config
from edcr.eddn.listener import EddnListener, apply_payload
from edcr.eddn.game_markets import import_game_markets, import_game_markets_every
from edcr.eddn.service import start_eddn_service
from edcr.eddn.messages import COMMODITY_SCHEMA, JOURNAL_SCHEMA, SIGNAL_SCHEMA, CarrierName, parse_eddn_message
from edcr.eddn.store import EddnStore
from edcr.recent_markets import save_recent_markets, snapshot_from_market_json

LIVE_HEADER = {"softwareName": "EDMC", "gameversion": "4.0.0.1904", "uploaderID": "x"}


def commodity_envelope(
    *,
    market_id: int = 3229359104,
    station: str = "Galileo",
    timestamp: str = "2026-11-10T14:00:00Z",
    commodities: list[dict[str, object]] | None = None,
    header: dict[str, object] = LIVE_HEADER,
    schema: str = COMMODITY_SCHEMA,
) -> dict[str, object]:
    return {
        "$schemaRef": schema,
        "header": header,
        "message": {
            "timestamp": timestamp,
            "systemName": "Sol",
            "stationName": station,
            "marketId": market_id,
            "commodities": commodities
            if commodities is not None
            else [
                {"name": "Gold", "buyPrice": 9000, "sellPrice": 8900, "stock": 5000, "demand": 0},
                {"name": "silver", "buyPrice": 0, "sellPrice": 5200, "stock": 0, "demand": 12000},
                {"name": "tea", "buyPrice": 0, "sellPrice": 1400, "stock": 0, "demand": 0},
            ],
        },
    }


def docked_envelope(*, timestamp: str = "2026-11-10T14:00:00Z", **overrides: object) -> dict[str, object]:
    message: dict[str, object] = {
        "timestamp": timestamp,
        "event": "Docked",
        "StarSystem": "Sol",
        "SystemAddress": 10477373803,
        "StarPos": [0.0, 0.0, 0.0],
        "StationName": "Galileo",
        "StationType": "Ocellus",
        "MarketID": 3229359104,
        "DistFromStarLS": 503.2,
        "LandingPads": {"Small": 4, "Medium": 7, "Large": 0},
    }
    message.update(overrides)
    return {"$schemaRef": JOURNAL_SCHEMA, "header": LIVE_HEADER, "message": message}


def carrier_commodity_envelope(access: str | None, *, timestamp: str, station: str = "JFF-15Z") -> dict[str, object]:
    envelope = commodity_envelope(market_id=3713428992, station=station, timestamp=timestamp)
    if access is not None:
        envelope["message"]["carrierDockingAccess"] = access  # type: ignore[index]
    return envelope


def signal_envelope(*names: str, timestamp: str = "2026-11-10T14:00:00Z") -> dict[str, object]:
    return {
        "$schemaRef": SIGNAL_SCHEMA,
        "header": LIVE_HEADER,
        "message": {
            "event": "FSSSignalDiscovered", "timestamp": timestamp, "StarSystem": "Sol", "SystemAddress": 10477373803,
            "StarPos": [0.0, 0.0, 0.0],
            "signals": [{"timestamp": timestamp, "SignalName": name, "SignalType": "FleetCarrier", "IsStation": True}
                        for name in names]
            + [{"timestamp": timestamp, "SignalName": "Galileo", "SignalType": "Outpost", "IsStation": True}],
        },
    }


def carrier_access(store: EddnStore) -> list[tuple[object, ...]]:
    return store._db.execute("SELECT market_id, access FROM carrier_access").fetchall()


def frame(envelope: dict[str, object]) -> bytes:
    return zlib.compress(json.dumps(envelope).encode())


def memory_store() -> EddnStore:
    return EddnStore(sqlite3.connect(":memory:", check_same_thread=False))


def prices(store: EddnStore) -> list[tuple[object, ...]]:
    return store._db.execute("SELECT market_id, commodity, buy, sell, supply, demand FROM price ORDER BY 1, 2").fetchall()


class EddnMessageTests(unittest.TestCase):
    def test_market_snapshot_keeps_only_tradeable_rows(self) -> None:
        [snapshot] = parse_eddn_message(commodity_envelope())

        self.assertEqual(snapshot.station_name, "Galileo")
        self.assertFalse(snapshot.is_carrier)
        self.assertEqual([price.name for price in snapshot.prices], ["gold", "silver"])

    def test_carriers_are_flagged_by_callsign(self) -> None:
        [snapshot] = parse_eddn_message(commodity_envelope(station="K7Q-BQL", market_id=3709000000))

        self.assertTrue(snapshot.is_carrier)

    def test_carrier_access_is_read_when_the_message_has_it(self) -> None:
        [with_access] = parse_eddn_message(carrier_commodity_envelope("SquadronFriends", timestamp="2026-11-10T14:00:00Z"))
        [without] = parse_eddn_message(carrier_commodity_envelope(None, timestamp="2026-11-10T14:00:00Z"))

        self.assertEqual((with_access.carrier_access, without.carrier_access), ("squadronfriends", ""))

    def test_carrier_signals_give_display_names_by_callsign(self) -> None:
        updates = parse_eddn_message(signal_envelope(
            "GRAND ARTS THEATRE JFF-15Z", "CANARY PARADISE  H3Q-W4M", "Clarissa BBG-4HW", "[UAPF] CENTURIO ASTRA B8H-7KT",
            "Q6K-WVH", "no callsign here",
        ))

        self.assertEqual([(update.callsign, update.name) for update in updates], [
            ("JFF-15Z", "GRAND ARTS THEATRE"), ("H3Q-W4M", "CANARY PARADISE"), ("BBG-4HW", "Clarissa"),
            ("B8H-7KT", "[UAPF] CENTURIO ASTRA"),
        ])
        self.assertTrue(all(isinstance(update, CarrierName) for update in updates))

    def test_legacy_test_and_unknown_messages_are_ignored(self) -> None:
        self.assertEqual(parse_eddn_message(commodity_envelope(header={**LIVE_HEADER, "gameversion": "CAPI-Legacy-market"})), [])
        self.assertEqual(parse_eddn_message(commodity_envelope(header={**LIVE_HEADER, "gameversion": "3.8.0.407"})), [])
        self.assertEqual(parse_eddn_message(commodity_envelope(schema=COMMODITY_SCHEMA + "/test")), [])
        self.assertEqual(parse_eddn_message(commodity_envelope(timestamp="yesterday")), [])
        self.assertEqual(parse_eddn_message(docked_envelope(event="Scan")), [])
        self.assertEqual(parse_eddn_message("junk"), [])

    def test_docked_gives_system_position_and_station(self) -> None:
        position, station = parse_eddn_message(docked_envelope())

        self.assertEqual((position.name, position.x), ("Sol", 0.0))
        self.assertEqual((station.name, station.type, station.dist_ls, station.max_pad), ("Galileo", "Ocellus", 503.2, "M"))


class EddnStoreTests(unittest.TestCase):
    def test_new_snapshot_replaces_market_prices(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        apply_payload(store, frame(commodity_envelope()))
        apply_payload(
            store,
            frame(
                commodity_envelope(
                    timestamp="2026-11-10T15:00:00Z",
                    commodities=[{"name": "gold", "buyPrice": 9100, "sellPrice": 9000, "stock": 10, "demand": 0}],
                )
            ),
        )

        self.assertEqual(prices(store), [(3229359104, "gold", 9100, 9000, 10, 0)])

    def test_older_snapshot_does_not_overwrite_newer_one(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        apply_payload(store, frame(commodity_envelope(timestamp="2026-11-10T15:00:00Z")))

        applied = apply_payload(
            store,
            frame(
                commodity_envelope(
                    commodities=[{"name": "gold", "buyPrice": 1, "sellPrice": 1, "stock": 1, "demand": 0}],
                )
            ),
        )

        self.assertEqual(applied, [])
        self.assertEqual(len(prices(store)), 2)

    def test_resent_snapshot_with_the_same_timestamp_is_kept_not_rewritten(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        apply_payload(store, frame(commodity_envelope(timestamp="2026-11-10T15:00:00Z")))

        applied = apply_payload(store, frame(commodity_envelope(timestamp="2026-11-10T15:00:00Z")))

        self.assertEqual(applied, [])
        self.assertEqual(len(prices(store)), 2)

    def test_station_update_keeps_known_details_and_flags_carrier_market(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        apply_payload(store, frame(commodity_envelope(station="Q2W-3ER", market_id=99)))
        apply_payload(store, frame(docked_envelope(MarketID=99, StationName="Q2W-3ER", StationType="FleetCarrier")))
        apply_payload(
            store,
            frame(
                docked_envelope(
                    timestamp="2026-11-10T16:00:00Z",
                    MarketID=99,
                    StationName="Q2W-3ER",
                    StationType="FleetCarrier",
                    DistFromStarLS=None,
                    LandingPads=None,
                )
            ),
        )

        self.assertEqual(
            store._db.execute("SELECT dist_ls, max_pad FROM station WHERE market_id = 99").fetchone(), (503.2, "M")
        )
        self.assertEqual(store._db.execute("SELECT is_carrier FROM market WHERE market_id = 99").fetchone(), (1,))

    def test_carrier_access_is_kept_until_a_newer_message_changes_it(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        apply_payload(store, frame(carrier_commodity_envelope("squadron", timestamp="2026-11-10T14:00:00Z")))
        apply_payload(store, frame(carrier_commodity_envelope(None, timestamp="2026-11-10T14:10:00Z")))
        self.assertEqual(carrier_access(store), [(3713428992, "squadron")])

        apply_payload(store, frame(carrier_commodity_envelope("all", timestamp="2026-11-10T14:20:00Z")))
        # A late upload of an older market does not undo the newer access.
        apply_payload(store, frame(carrier_commodity_envelope("none", timestamp="2026-11-10T13:00:00Z")))
        self.assertEqual(carrier_access(store), [(3713428992, "all")])

    def test_carrier_names_are_written_only_when_new_or_changed(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)

        def applied(name: str, timestamp: str) -> list[type]:
            return apply_payload(store, frame(signal_envelope(name, timestamp=timestamp)))

        self.assertEqual(applied("GRAND ARTS THEATRE JFF-15Z", "2026-11-10T14:00:00Z"), [CarrierName])
        self.assertEqual(applied("GRAND ARTS THEATRE JFF-15Z", "2026-11-10T14:05:00Z"), [])
        self.assertEqual(applied("OLD NAME JFF-15Z", "2026-11-10T13:00:00Z"), [])
        self.assertEqual(applied("GRAND ARTS HALL JFF-15Z", "2026-11-10T14:10:00Z"), [CarrierName])
        self.assertEqual(store._db.execute("SELECT callsign, name FROM carrier_name").fetchall(),
                         [("JFF-15Z", "GRAND ARTS HALL")])

    def test_a_database_from_before_carrier_facts_opens_with_its_data(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "eddn.sqlite3"
            old = sqlite3.connect(path)
            old.executescript(
                "CREATE TABLE market (market_id INTEGER PRIMARY KEY, system_name TEXT NOT NULL,"
                " station_name TEXT NOT NULL, is_carrier INTEGER NOT NULL, updated_at REAL NOT NULL);"
                "INSERT INTO market VALUES (3713428992, 'Sol', 'JFF-15Z', 1, 1.0);"
            )
            old.commit()
            old.close()

            store = EddnStore.open(path)
            apply_payload(store, frame(carrier_commodity_envelope("friends", timestamp="2026-11-10T14:00:00Z")))
            store.close()
            reopened = EddnStore.open(path)
            self.addCleanup(reopened.close)
            self.assertEqual(reopened.counts().markets, 1)
            self.assertEqual(carrier_access(reopened), [(3713428992, "friends")])

    def test_prune_drops_stale_markets_and_counts_report_the_rest(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        apply_payload(store, frame(commodity_envelope(market_id=1, timestamp="2026-11-01T00:00:00Z")))
        apply_payload(store, frame(commodity_envelope(market_id=2, timestamp="2026-11-10T00:00:00Z")))
        apply_payload(store, frame(docked_envelope()))

        removed = store.prune(older_than=parse_eddn_message(docked_envelope(timestamp="2026-11-05T00:00:00Z"))[0].timestamp)
        counts = store.counts()

        self.assertEqual(removed, 1)
        self.assertEqual((counts.markets, counts.prices, counts.stations, counts.systems), (1, 2, 1, 1))


class FakeSocket:
    def __init__(self, frames: list[bytes | None], on_empty: object) -> None:
        self.frames = frames
        self.on_empty = on_empty
        self.closed = False

    def recv(self, timeout_s: float) -> bytes | None:
        if not self.frames:
            self.on_empty()
            return None
        return self.frames.pop(0)

    def close(self) -> None:
        self.closed = True


class EddnListenerTests(unittest.TestCase):
    def test_listener_applies_frames_counts_errors_and_reconnects_after_silence(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        clock = [1000.0]
        sockets: list[FakeSocket] = []
        logs: list[str] = []

        def tick() -> float:
            clock[0] += 1.0
            return clock[0]

        def open_socket() -> FakeSocket:
            if not sockets:
                # First connection: two messages, junk, then a silent minute.
                frames: list[bytes | None] = [frame(commodity_envelope()), frame(docked_envelope()), b"junk"]
                frames += [None] * 61
                socket = FakeSocket(frames, on_empty=lambda: None)
            else:
                socket = FakeSocket([], on_empty=listener.stop)
            sockets.append(socket)
            return socket

        listener = EddnListener(store=store, open_socket=open_socket, time_fn=tick, max_age_s=7 * 86400, log=logs.append)
        listener.run()
        stats = listener.stats()

        self.assertEqual((stats.messages, stats.markets, stats.stations, stats.systems, stats.errors), (3, 1, 1, 1, 1))
        self.assertEqual(stats.reconnects, 1)
        self.assertFalse(stats.connected)
        self.assertTrue(all(socket.closed for socket in sockets))
        self.assertEqual(logs, ["EDDN relay silent; reconnecting."])
        self.assertEqual(len(prices(store)), 2)


def save_game_markets(path: Path, *timestamps: str, access: str = "") -> None:
    """Recent markets as the Control Room records them from Market.json, one per timestamp."""
    markets = []
    for index, timestamp in enumerate(timestamps):
        markets.append(snapshot_from_market_json({
            "timestamp": timestamp, "MarketID": 3229359104 + index, "StationName": f"Galileo {index}" if index else "Galileo",
            "StarSystem": "Sol", "StationType": "FleetCarrier" if access else "Ocellus",
            **({"CarrierDockingAccess": access} if access else {}),
            "Items": [
                {"Name": "$gold_name;", "BuyPrice": 9500, "SellPrice": 9400, "Stock": 700, "Demand": 1},
                {"Name": "$insulatingmembrane_name;", "BuyPrice": 0, "SellPrice": 20375, "Stock": 0, "Demand": 7134688},
                {"Name": "$tea_name;", "BuyPrice": 0, "SellPrice": 1400, "Stock": 0, "Demand": 0},
            ],
        }))
    save_recent_markets(path, tuple(markets))


class GameMarketImportTests(unittest.TestCase):
    def test_our_market_uses_eddn_names_and_replaces_only_older_data(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        apply_payload(store, frame(commodity_envelope(timestamp="2026-11-10T15:00:00Z")))
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_markets.json"
            save_game_markets(path, "2026-11-10T14:00:00Z")
            [older] = import_game_markets(store, path)
            self.assertFalse(older.written)
            self.assertEqual(len(prices(store)), 2)

            save_game_markets(path, "2026-11-10T16:00:00Z")
            [newer] = import_game_markets(store, path)

        self.assertTrue(newer.written)
        # The whole station is replaced: EDDN's silver row does not ride along under our timestamp.
        self.assertEqual(prices(store), [(3229359104, "gold", 9500, 9400, 700, 1),
                                         (3229359104, "insulatingmembrane", 0, 20375, 0, 7134688)])
        self.assertEqual(apply_payload(store, frame(commodity_envelope(timestamp="2026-11-10T15:30:00Z"))), [])

    def test_our_carrier_market_brings_its_docking_access(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_markets.json"
            save_game_markets(path, "2026-11-10T14:00:00Z", access="squadronfriends")
            import_game_markets(store, path)

        self.assertEqual(carrier_access(store), [(3229359104, "squadronfriends")])

    def test_service_imports_our_markets_at_start_and_when_the_file_changes(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        stop = threading.Event()
        logs: list[str] = []
        imported = threading.Condition()

        def log(message: str) -> None:
            with imported:
                logs.append(message)
                imported.notify_all()

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_markets.json"
            save_game_markets(path, "2026-11-10T14:00:00Z")
            import_game_markets_every(store, path, 0.001, log, stop=stop)
            with imported:
                self.assertTrue(imported.wait_for(lambda: len(logs) == 1, 2.0))
            save_game_markets(path, "2026-11-10T14:00:00Z", "2026-11-10T14:05:00Z")
            with imported:
                self.assertTrue(imported.wait_for(lambda: len(logs) == 2, 2.0))
            stop.set()

        self.assertEqual(logs[0], "Market DB our markets: 1 written: Galileo (2026-11-10T14:00:00Z); 0 already in the DB")
        # Every recorded market is offered again; one already stored with the same timestamp is kept.
        self.assertEqual(logs[1], "Market DB our markets: 1 written: Galileo 1 (2026-11-10T14:05:00Z); 1 already in the DB")
        self.assertEqual(store.counts().markets, 2)


class EddnServiceTests(unittest.TestCase):
    def test_service_fills_the_configured_database_reports_status_and_closes(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "eddn.sqlite3"
            done = threading.Event()
            reported = threading.Event()
            logs: list[str] = []

            def log(message: str) -> None:
                logs.append(message)
                if message.startswith("EDDN connected") and "1 market updates" in message:
                    reported.set()

            def idle() -> None:
                # A real socket blocks for the poll timeout; returning at once spins the listener
                # and starves the status thread of the GIL for ~0.1s.
                done.set()
                time.sleep(0.001)

            store = EddnStore.open(path)
            service = start_eddn_service(
                EddnConfig(enabled=True, database_file=path, status_every_s=0.001),
                store=store,
                open_socket=lambda: FakeSocket([frame(commodity_envelope())], on_empty=idle),
                time_fn=lambda: 1000.0,
                log=log,
            )
            self.assertTrue(done.wait(2.0))
            self.assertTrue(reported.wait(2.0))
            status = service.status()
            service.close()
            store.close()

            self.assertEqual(status["listener"]["markets"], 1)
            self.assertEqual(status["store"]["prices"], 2)
            self.assertIn("db 1 markets, 2 prices", next(line for line in logs if line.startswith("EDDN connected")))
            self.assertFalse(service.listener._thread.is_alive())


class EddnConfigTests(unittest.TestCase):
    def test_defaults_and_validation(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("", encoding="utf-8")
            eddn = load_config(path).eddn
            self.assertFalse(eddn.enabled)
            self.assertEqual(eddn.status_every_s, 30.0)
            self.assertEqual(eddn.relay, "tcp://eddn.edcd.io:9500")
            self.assertEqual(eddn.database_file, Path(".eddn_markets.sqlite3"))
            self.assertEqual(eddn.max_age_days, 7.0)

            path.write_text("[eddn]\nmax_age_days = 0\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "eddn.max_age_days"):
                load_config(path)
            path.write_text("[eddn]\nstatus_every_s = -1\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "eddn.status_every_s"):
                load_config(path)

if __name__ == "__main__":
    unittest.main()
