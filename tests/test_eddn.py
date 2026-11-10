from __future__ import annotations

import json
import sqlite3
import unittest
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory

from edap.config import ConfigError, load_config
from edap.eddn.listener import EddnListener, apply_payload
from edap.eddn.messages import COMMODITY_SCHEMA, JOURNAL_SCHEMA, parse_eddn_message
from edap.eddn.store import EddnStore

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

    def test_station_update_keeps_known_details_and_flags_carrier_market(self) -> None:
        store = memory_store()
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

    def test_prune_drops_stale_markets_and_counts_report_the_rest(self) -> None:
        store = memory_store()
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


class EddnConfigTests(unittest.TestCase):
    def test_defaults_and_validation(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("", encoding="utf-8")
            eddn = load_config(path).eddn
            self.assertFalse(eddn.enabled)
            self.assertEqual(eddn.relay, "tcp://eddn.edcd.io:9500")
            self.assertEqual(eddn.database_file, Path(".eddn_markets.sqlite3"))
            self.assertEqual(eddn.max_age_days, 7.0)

            path.write_text("[eddn]\nmax_age_days = 0\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "eddn.max_age_days"):
                load_config(path)

if __name__ == "__main__":
    unittest.main()
