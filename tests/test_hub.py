from __future__ import annotations

import asyncio
import json
import sqlite3
import unittest
import warnings
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated; install `httpx2` instead\.",
)

from starlette.websockets import WebSocketDisconnect

from edap.config import ConfigError, load_config, with_hub_role
from edap.control_room.models import ShipState
from edap.control_room.server.app import _handle_session_message_async, build_observer_server_app
from edap.control_room.server.auth import SharedAccessTokenAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.eddn.messages import StationInfo, SystemPosition
from edap.eddn.route_query import parse_route_query, resolve_route_params
from edap.eddn.store import EddnStore
from edap.hub.history import CentralHistory, HubRuns
from edap.hub.nodes import BadItem, HubLinkSession, HubSide, NodeRegistry, store_link_item
from edap.hub.outbox import Outbox
from edap.hub.peer import NodeHello, PeerLink, load_node_id, peer_link_url
from edap.hub.relay import HubRelay
from edap.hub.voice import HubVoice, node_muter
from edap.hub.protocol import (
    REQUEST_EDDN_STATUS, HubUnreachable, LinkClosed, LinkReply, decode_update, encode_update,
)
from edap.inara.trade_routes import TradeRoute, TradeRouteSearchResult
from edap.recent_markets import MarketSnapshot, save_recent_markets, snapshot_entry, snapshot_from_market_json
from tests.shared_loop import TestClient
from tests.test_eddn import memory_store, prices

TOKEN = "page-token"
HUB_TOKEN = "hub-token"
HUB_URL = "http://hub.local:8765"
NOW = 1794387600.0  # 2026-11-11T09:00:00Z
HUB_NODE = NodeHello(node_id="hub-node", name="Home", version="1.0.0")
PEER_NODE = NodeHello(node_id="peer-node", name="Deck", version="1.0.0")
SOL = SystemPosition(address=10477373803, name="Sol", x=0.0, y=0.0, z=0.0, timestamp=NOW - 60)
GALILEO = StationInfo(market_id=128016640, system_address=10477373803, system_name="Sol", name="Galileo",
                      type="Ocellus", dist_ls=505.0, max_pad="L", timestamp=NOW - 60)


class FakeClock:
    """Wall-clock seconds that move only when a test calls `advance`."""

    def __init__(self, now: float = NOW) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def market(timestamp: str = "2026-11-10T14:00:00Z", market_id: int = 3229359104, station: str = "Galileo",
           system: str = "Sol", sell_gold: int = 9400) -> MarketSnapshot:
    snapshot = snapshot_from_market_json({
        "timestamp": timestamp, "MarketID": market_id, "StationName": station, "StarSystem": system,
        "StationType": "Ocellus",
        "Items": [{"Name": "$gold_name;", "BuyPrice": 9500, "SellPrice": sell_gold, "Stock": 700, "Demand": 900}],
    })
    assert snapshot is not None
    return snapshot


def haul_run(ended_at: str, *, ship_id: int | None = 7, station_1: str = "Galileo", station_2: str = "Abraham",
             profit: int = 2_000_000, status: str = "completed") -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema": 1, "kind": "two_way", "status": status, "started_at": "2026-11-10T08:00:00Z", "ended_at": ended_at,
        "duration_s": 1800.0, "cost": 1_000_000, "revenue": 1_000_000 + profit, "profit": profit, "legs": [],
        "route": {"station_1": station_1, "system_1": "Sol", "station_2": station_2, "system_2": "Sol"},
    }
    if ship_id is not None:
        row["ship"] = {"id": ship_id, "type": "cutter", "name": f"Ship {ship_id}", "laden_jump_range_ly": 20.0}
    return row


@dataclass(frozen=True)
class Ledger:
    """Stands in for the journal trade ledger."""

    available: bool
    profit: int


def write_runs(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def memory_outbox() -> Outbox:
    return Outbox(sqlite3.connect(":memory:", check_same_thread=False), now=NOW)


def ship_data(system: str = "Sol", cargo_capacity: int = 784) -> object:
    return SimpleNamespace(ship=ShipState(system=system, cargo_capacity=cargo_capacity))


def server(**options: object):
    options.setdefault("data_provider", ship_data)
    options.setdefault("broker", InMemoryObserverSessionBroker())
    options.setdefault("command_handler", None)
    return build_observer_server_app(auth=SharedAccessTokenAuth(TOKEN), **options)


def roundtrip(frame: Any) -> Any:
    """What the other end reads: frames must survive JSON."""
    return json.loads(json.dumps(frame))


class QuietRelay:
    """A peer relay for tests that do not look at hub pages."""

    def link_up(self, send: Callable[[dict[str, Any]], None]) -> None:
        pass

    def link_down(self) -> None:
        pass

    def on_frame(self, frame: dict[str, Any]) -> None:
        pass


class Loopback:
    """An in-memory link: the hub session answers inside `send`, straight into the peer."""

    def __init__(self, peer: PeerLink) -> None:
        self.peer = peer
        self.session: HubLinkSession
        self.sent: list[dict[str, Any]] = []
        self.up = True
        self.closed = False
        # Frames `receive` hands out before the link reports itself closed.
        self.incoming: list[dict[str, Any] | None] = []

    def send(self, frame: dict[str, Any]) -> None:
        if not self.up:
            raise LinkClosed("cable pulled")
        self.sent.append(roundtrip(frame))
        for reply in self.session.receive(roundtrip(frame)):
            self.peer.on_frame(roundtrip(reply))

    def down(self, frame: dict[str, Any]) -> None:
        """The hub sends a frame of its own (a relay frame) down to the peer."""
        if not self.up:
            raise LinkClosed("cable pulled")
        self.peer.on_frame(roundtrip(frame))

    def receive(self, timeout_s: float) -> dict[str, Any] | None:
        if self.incoming:
            return self.incoming.pop(0)
        raise LinkClosed("closed by the test")

    def close(self) -> None:
        self.closed = True


class Rig:
    """A hub (registry, store, link session) and a peer, joined by `Loopback` links."""

    def __init__(self, *, handlers: dict[str, Callable[[Any], LinkReply]] | None = None,
                 store_item: Callable[[NodeHello, str, Any], None] | None = None, peer_relay: Any = None) -> None:
        self.clock = FakeClock()
        self.store = memory_store()
        self.hub_logs: list[str] = []
        self.peer_logs: list[str] = []
        self.registry = NodeRegistry(HUB_NODE, self.clock)
        self.tmp = TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.hub_runs = HubRuns.open(Path(self.tmp.name) / "hub_runs.jsonl", self.hub_logs.append)
        # The hub's own game's runs, which join the central view under its node id.
        self.own_runs = Path(self.tmp.name) / "own_runs.jsonl"
        self.history = CentralHistory(local=HUB_NODE, local_file=self.own_runs, runs=self.hub_runs)
        # The markets the hub listed on its Markets page.
        self.recorded_markets: list[Any] = []
        self.store_item = store_item or store_link_item(self.store, self.hub_runs, self.recorded_markets.append,
                                                        self.hub_logs.append)
        self.handlers = handlers or {}
        self.outbox = memory_outbox()
        self.relay = HubRelay(log=self.hub_logs.append, read_timeout_s=10.0, slow_read_timeout_s=60.0)
        # What the hub speakers said, and the WAVs Piper made (bytes of the text, so tests read them).
        self.spoken: list[str] = []
        # Each mute the hub set on its own game.
        self.hub_mutes: list[bool] = []
        self.voice = HubVoice(
            local_node_id=HUB_NODE.node_id, settings_file=Path(self.tmp.name) / "voice.json",
            speak=lambda text: self.spoken.append(text) is None, synthesize=lambda text: f"WAV {text}".encode(),
            names=lambda node_id: HUB_NODE.name if node_id == HUB_NODE.node_id else self.relay.name(node_id),
            set_muted=node_muter(HUB_NODE.node_id, self.hub_mutes.append, self.relay.send),
            run_in_background=lambda work: work(), log=self.hub_logs.append,
        )
        self.peer = PeerLink(hello=PEER_NODE, hub_url=lambda: HUB_URL, outbox=self.outbox,
                             relay=peer_relay or QuietRelay(), connect=self.connect,
                             accept_hub=lambda hub_id, name, url: self.refuse_hub,
                             now=self.clock, log=self.peer_logs.append, heartbeat_s=30.0,
                             request_timeout_s=10.0, search_timeout_s=180.0)
        self.links: list[Loopback] = []
        # What `accept_hub` answers on welcome: "" links, anything else refuses the hub.
        self.refuse_hub = ""

    def connect(self) -> Loopback:
        link = Loopback(self.peer)
        link.session = HubLinkSession(registry=self.registry, store_item=self.store_item, handlers=self.handlers,
                                      relay=self.relay, callout=self.voice.callout,
                                      linked=self.voice.node_linked, send=link.down,
                                      log=self.hub_logs.append)
        self.links.append(link)
        return link

    def hub_side(self) -> HubSide:
        return HubSide(self.registry, self.store_item, HUB_TOKEN, self.history, self.relay, self.voice)

    def attach(self) -> Loopback:
        link = self.connect()
        self.peer.attach(link)
        return link

    def drop(self, link: Loopback) -> None:
        link.up = False
        self.peer.detach(link, "cable pulled")
        link.session.close()

    def close(self) -> None:
        self.store.close()
        self.outbox.close()
        self.tmp.cleanup()


def rig(test: unittest.TestCase, **options: Any) -> Rig:
    made = Rig(**options)
    test.addCleanup(made.close)
    return made


class HubConfigTests(unittest.TestCase):
    def test_roles_names_and_tokens_are_validated(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("", encoding="utf-8")
            hub = load_config(path).hub
            self.assertEqual((hub.role, hub.owns_data, hub.enabled, hub.name), ("standalone", True, False, ""))
            self.assertEqual((hub.outbox_file, hub.runs_file),
                             (Path(".control_room_hub_outbox.sqlite3"), Path(".control_room_hub_runs.jsonl")))
            self.assertEqual((hub.timeout_s, hub.search_timeout_s, hub.heartbeat_s), (10.0, 180.0, 30.0))

            path.write_text('[hub]\nrole = "Hub"\ntoken = "t"\nname = " Home "\n', encoding="utf-8")
            hub = load_config(path).hub
            self.assertEqual((hub.role, hub.owns_data, hub.enabled, hub.name), ("hub", True, False, "Home"))
            path.write_text('[hub]\nrole = "peer"\nurl = "http://192.168.1.20:8765/"\ntoken = "t"\n'
                            "outbox_file = 'q/outbox.sqlite3'\n", encoding="utf-8")
            hub = load_config(path).hub
            self.assertEqual((hub.url, hub.owns_data, hub.enabled, hub.outbox_file),
                             ("http://192.168.1.20:8765", False, True, Path("q") / "outbox.sqlite3"))
            # No url: the peer still links, to the hub it finds on the LAN.
            path.write_text('[hub]\nrole = "peer"\ntoken = "t"\n', encoding="utf-8")
            self.assertEqual((load_config(path).hub.url, load_config(path).hub.enabled), ("", True))

            for text, key in (
                ('[hub]\nrole = "server"\n', "hub.role"),
                ('[hub]\nurl = "http://192.168.1.20:8765"\n', "hub.url"),
                ('[hub]\nrole = "peer"\nurl = "192.168.1.20"\ntoken = "t"\n', "hub.url"),
                ('[hub]\nrole = "hub"\n', "hub.token"),
                ('[hub]\nrole = "peer"\nurl = "http://192.168.1.20:8765"\n', "hub.token"),
                ('[hub]\nrole = "peer"\n', "hub.token"),
                ("[hub]\ntimeout_s = 0\n", "hub.timeout_s"),
                ("[hub]\nheartbeat_s = -1\n", "hub.heartbeat_s"),
            ):
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaisesRegex(ConfigError, key):
                        load_config(path)

    def test_hub_and_peer_commands_set_the_role_and_fall_back_to_the_web_token(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("", encoding="utf-8")
            hub = with_hub_role(load_config(path), "hub", "edcr").hub
            self.assertEqual((hub.role, hub.token), ("hub", "edcr"))
            # A config token wins, and a config role is overridden.
            path.write_text('[hub]\nrole = "hub"\ntoken = "t"\n', encoding="utf-8")
            peer = with_hub_role(load_config(path), "peer", "edcr").hub
            self.assertEqual((peer.role, peer.token, peer.enabled), ("peer", "t", True))
            # A url only a peer uses still fails as a hub.
            path.write_text('[hub]\nrole = "peer"\nurl = "http://192.168.1.20:8765"\ntoken = "t"\n', encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "hub.url"):
                with_hub_role(load_config(path), "hub", "edcr")

    def test_node_id_is_made_once_and_kept(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".control_room_node_id"
            ids = iter(["first", "second"])
            self.assertEqual(load_node_id(path, lambda: next(ids)), "first")
            self.assertEqual(load_node_id(path, lambda: next(ids)), "first")
            self.assertEqual(path.read_text(encoding="utf-8"), "first\n")

    def test_link_url_follows_the_hub_scheme(self) -> None:
        self.assertEqual(peer_link_url("http://hub.local:8765"), "ws://hub.local:8765/api/peer-link")
        self.assertEqual(peer_link_url("https://hub.local"), "wss://hub.local/api/peer-link")


class OutboxTests(unittest.TestCase):
    def test_items_keep_their_order_survive_a_restart_and_a_key_queues_once(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "outbox" / "hub.sqlite3"
            outbox = Outbox.open(path, now=NOW)
            first = outbox.add("market", {"n": 1}, key="a", now=NOW)
            second = outbox.add("station_facts", {"n": 2}, key="b", now=NOW)
            self.assertIsNone(outbox.add("market", {"n": 1}, key="a", now=NOW))
            outbox.close()

            # Closed before the directory goes: Windows cannot delete an open SQLite file.
            outbox = Outbox.open(path, now=NOW + 86400)
            try:
                self.assertEqual([(item.seq, item.kind, item.body) for item in outbox.pending(after=0)],
                                 [(first, "market", {"n": 1}), (second, "station_facts", {"n": 2})])
                outbox.remove(first)
                self.assertEqual([item.seq for item in outbox.pending(after=0)], [second])
                self.assertEqual(outbox.pending(after=second), [])
                self.assertEqual(outbox.count(), 1)
            finally:
                outbox.close()

    def test_old_keys_are_forgotten_after_thirty_days_but_haul_run_keys_never(self) -> None:
        outbox = memory_outbox()
        self.addCleanup(outbox.close)
        outbox.add("market", {}, key="a", now=NOW)
        outbox.add("haul_run", {}, key="run", now=NOW, forever=True)
        later = NOW + 365 * 86400
        reopened = Outbox(outbox._db, now=later)
        self.assertIsNotNone(reopened.add("market", {}, key="a", now=later))
        self.assertIsNone(reopened.add("haul_run", {}, key="run", now=later, forever=True))


class LinkTests(unittest.TestCase):
    def test_hello_registers_the_peer_and_a_drop_keeps_it_listed_offline(self) -> None:
        r = rig(self)
        link = r.attach()
        status = r.peer.status()
        self.assertEqual((status["connected"], status["hub_name"], status["hub_version"]), (True, "Home", "1.0.0"))
        self.assertEqual(link.sent[0], {"type": "hello", "node_id": "peer-node", "name": "Deck", "version": "1.0.0"})
        self.assertEqual([(n["name"], n["local"], n["connected"]) for n in r.registry.nodes()],
                         [("Home", True, True), ("Deck", False, True)])
        self.assertEqual(r.registry.connected_peers(), 1)

        r.clock.advance(90)
        r.drop(link)
        deck = r.registry.nodes()[1]
        self.assertEqual((deck["connected"], deck["last_contact_at"]), (False, "2026-11-11T09:00:00Z"))
        self.assertEqual(r.registry.nodes()[0]["last_contact_at"], "2026-11-11T09:01:30Z")
        self.assertEqual(r.peer.status()["connected"], False)
        self.assertEqual(r.peer.status()["last_error"], "cable pulled")
        self.assertEqual(r.hub_logs, ["Peer Deck connected (node peer-node, version 1.0.0)", "Peer Deck disconnected"])
        self.assertEqual(r.peer_logs, ["Hub link up: Home (hub.local:8765); sending 0 queued item(s)",
                                       "Hub link to Home lost: cable pulled; redialling"])

    def test_a_replaced_connection_closing_late_leaves_the_node_online(self) -> None:
        r = rig(self)
        old = r.connect()
        old.session.receive({"type": "hello", "node_id": "peer-node", "name": "Deck"})
        r.attach()
        old.session.close()
        self.assertTrue(r.registry.nodes()[1]["connected"])

    def test_the_hub_refuses_peers_without_hello_or_with_its_own_node_id(self) -> None:
        r = rig(self)
        for frames, detail in (
            ([{"type": "ping"}], "say hello first"),
            ([{"type": "hello", "node_id": " "}], "hello needs a node_id"),
            ([{"type": "hello", "node_id": "hub-node"}], "this peer has the hub's own node id"),
            ([[1, 2]], "frames must be JSON objects"),
        ):
            with self.subTest(detail=detail):
                session = r.connect().session
                [reply] = session.receive(frames[0])
                self.assertEqual(reply["type"], "error")
                self.assertIn(detail, reply["detail"])
                self.assertTrue(session.closed)
        self.assertEqual(len(r.registry.nodes()), 1)

    def test_a_refused_hello_ends_the_connection_with_the_reason(self) -> None:
        r = rig(self)
        r.peer.hello = HUB_NODE
        link = r.connect()
        self.assertFalse(r.peer.serve(link))
        self.assertTrue(link.closed)
        self.assertIn("own node id", r.peer.status()["last_error"])

    def test_outbox_drains_in_order_on_connect_and_new_items_go_out_at_once(self) -> None:
        r = rig(self)
        r.peer.enqueue_markets((market("2026-11-10T14:00:00Z"), market("2026-11-10T13:00:00Z", 1, "Abraham")))
        r.peer.enqueue_station_facts([SOL, GALILEO])
        r.peer.enqueue_station_facts([SOL])  # the journal replay at the next start
        self.assertEqual(r.peer.status()["outbox_pending"], 4)

        link = r.attach()
        self.assertEqual([(f["type"], f.get("kind")) for f in link.sent[1:]],
                         [("item", "market"), ("item", "market"), ("item", "station_facts"), ("item", "station_facts")])
        self.assertEqual(r.outbox.count(), 0)
        self.assertEqual(r.store.counts().markets, 2)
        self.assertEqual((r.store.counts().systems, r.store.counts().stations), (1, 1))

        r.peer.enqueue_market(market("2026-11-10T15:00:00Z", sell_gold=9900))
        self.assertEqual(link.sent[-1]["type"], "item")
        self.assertEqual(r.outbox.count(), 0)
        self.assertEqual(prices(r.store)[-1][3], 9900)
        self.assertEqual(r.peer_logs[0], "Hub link up: Home (hub.local:8765); sending 4 queued item(s)")

    def test_items_wait_while_the_hub_is_away_and_a_failed_store_is_sent_again_next_time(self) -> None:
        failures = [sqlite3.OperationalError("database is locked")]
        r = rig(self)
        real_store = r.store_item

        def flaky_store(node: NodeHello, kind: str, body: Any) -> None:
            if failures:
                raise failures.pop()
            real_store(node, kind, body)

        r.store_item = flaky_store
        link = r.attach()
        r.drop(link)
        r.peer.enqueue_market(market())
        self.assertEqual(r.outbox.count(), 1)

        r.attach()
        self.assertEqual(r.outbox.count(), 1)  # nacked: kept
        self.assertIn("could not store outbox item 1: database is locked", r.peer_logs[-1])
        r.attach()
        self.assertEqual((r.outbox.count(), r.store.counts().markets), (0, 1))

    def test_hub_stores_idempotently_newest_wins_and_drops_bad_items(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        logs: list[str] = []
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        listed: list[Any] = []
        store_item = store_link_item(store, HubRuns.open(Path(tmp.name) / "runs.jsonl", logs.append), listed.append,
                                     logs.append)
        newer = market("2026-11-10T15:00:00Z", sell_gold=9900)
        store_item(PEER_NODE, "market", roundtrip(snapshot_entry(newer)))
        store_item(PEER_NODE, "market", roundtrip(snapshot_entry(newer)))
        store_item(PEER_NODE, "market", roundtrip(snapshot_entry(market("2026-11-10T14:00:00Z"))))
        store_item(PEER_NODE, "station_facts", roundtrip(encode_update(GALILEO)))
        older = replace(GALILEO, type="Coriolis", timestamp=NOW - 600)
        store_item(PEER_NODE, "station_facts", roundtrip(encode_update(older)))

        self.assertEqual(prices(store), [(3229359104, "gold", 9500, 9900, 700, 900)])
        self.assertEqual(store._db.execute("SELECT type FROM station").fetchall(), [("Ocellus",)])
        self.assertEqual(logs, ["Market DB peer market Galileo: written", "Market DB peer market Galileo: already in the DB",
                                "Market DB peer market Galileo: already in the DB"])
        # Every market is also offered to the Markets page list, which keeps the newest per station.
        self.assertEqual([snapshot.timestamp for snapshot in listed],
                         ["2026-11-10T15:00:00Z", "2026-11-10T15:00:00Z", "2026-11-10T14:00:00Z"])
        for kind, body in (("market", {"station": "x"}), ("station_facts", {"kind": "planet"}), ("ship", {}),
                           ("haul_run", {"schema": 1}), ("haul_run", [1])):
            with self.subTest(kind=kind), self.assertRaises(BadItem):
                store_item(PEER_NODE, kind, body)

    def test_finished_runs_go_up_once_and_join_the_hubs_own_under_its_node_id(self) -> None:
        r = rig(self)
        first, second = haul_run("2026-11-10T09:00:00Z"), haul_run("2026-11-10T10:00:00Z", status="aborted")
        # The first start with a link backfills the whole file while the hub is away.
        r.peer.enqueue_runs([first, second])
        self.assertEqual(r.outbox.count(), 2)
        link = r.attach()
        self.assertEqual([f.get("kind") for f in link.sent[1:]], ["haul_run", "haul_run"])
        self.assertEqual(r.outbox.count(), 0)

        # Every later start and file change rescans the file: only the new run goes up.
        third = haul_run("2026-11-10T11:00:00Z")
        r.peer.enqueue_runs([first, second, third])
        self.assertEqual(len(link.sent), 4)
        # A run delivered twice (its ack lost) is stored once.
        r.peer._enqueue("haul_run", first, key="replayed")
        write_runs(r.own_runs, [haul_run("2026-11-10T09:00:00Z")])

        rows, skipped = r.history.rows()
        self.assertEqual(skipped, 0)
        self.assertEqual([(row["node"], row["ended_at"]) for row in rows], [
            ({"id": "hub-node", "name": "Home"}, "2026-11-10T09:00:00Z"),
            ({"id": "peer-node", "name": "Deck"}, "2026-11-10T09:00:00Z"),
            ({"id": "peer-node", "name": "Deck"}, "2026-11-10T10:00:00Z"),
            ({"id": "peer-node", "name": "Deck"}, "2026-11-10T11:00:00Z"),
        ])
        self.assertEqual(r.hub_logs.count("Haul history: run from Deck (completed, ended 2026-11-10T09:00:00Z)"), 1)
        # The file survives a hub restart and still knows what it has.
        reopened = HubRuns.open(r.hub_runs.path, r.hub_logs.append)
        self.assertFalse(reopened.add(PEER_NODE, first))
        self.assertTrue(reopened.add(replace(PEER_NODE, node_id="other"), first))

    def test_a_bad_item_is_dropped_with_a_log_on_both_sides(self) -> None:
        r = rig(self)
        r.peer._enqueue("market", {"station": "x"}, key="bad")
        r.attach()
        self.assertEqual(r.outbox.count(), 0)
        self.assertIn("dropped outbox item 1: not a recent market entry", r.peer_logs[-1])
        self.assertIn("dropped outbox item 1", r.hub_logs[-1])

    def test_facts_survive_json_both_ways(self) -> None:
        for update in (SOL, GALILEO):
            self.assertEqual(decode_update(roundtrip(encode_update(update))), update)
        self.assertIsNone(decode_update({"kind": "system", "address": 1}))

    def test_requests_get_answers_and_fail_fast_when_the_link_is_down_or_silent(self) -> None:
        r = rig(self, handlers={REQUEST_EDDN_STATUS: lambda body: LinkReply(200, {"enabled": True, "asked": body}),
                                "boom": lambda body: 1 / 0})
        with self.assertRaisesRegex(HubUnreachable, "not connected to the hub"):
            r.peer.request(REQUEST_EDDN_STATUS, {}, timeout_s=1.0)
        link = r.attach()
        self.assertEqual(r.peer.request(REQUEST_EDDN_STATUS, {"x": 1}, timeout_s=1.0),
                         LinkReply(200, {"enabled": True, "asked": {"x": 1}}))
        self.assertEqual(r.peer.request("routes?", {}, timeout_s=1.0).status, 404)
        self.assertEqual(r.peer.request("boom", {}, timeout_s=1.0), LinkReply(500, {"detail": "division by zero"}))

        link.session = SimpleNamespace(receive=lambda frame: [], close=link.session.close)  # the hub stops answering
        with self.assertRaisesRegex(HubUnreachable, "no answer in 0.001 s"):
            r.peer.request(REQUEST_EDDN_STATUS, {}, timeout_s=0.001)
        r.drop(link)
        with self.assertRaisesRegex(HubUnreachable, "not connected to the hub: cable pulled"):
            r.peer.request(REQUEST_EDDN_STATUS, {}, timeout_s=1.0)

    def test_quiet_link_pings_then_gives_up_after_two_heartbeats(self) -> None:
        r = rig(self)
        link = r.connect()
        clock = r.clock
        hub_session = link.session
        # The hub welcomes the peer, then goes quiet.
        link.session = SimpleNamespace(receive=lambda frame: hub_session.receive(frame) if frame["type"] == "hello" else [])

        def receive(timeout_s: float) -> dict[str, Any] | None:
            clock.advance(timeout_s)
            return None

        link.receive = receive  # type: ignore[method-assign]
        self.assertTrue(r.peer.serve(link))
        self.assertEqual([frame["type"] for frame in link.sent], ["hello", "ping"])
        self.assertEqual(r.peer.status()["last_error"], "no answer for 60 s")
        self.assertTrue(link.closed)

    def test_run_redials_with_backoff_and_starts_over_after_a_good_connection(self) -> None:
        r = rig(self)
        attempts: list[str] = ["refused", "refused", "ok", "refused", "refused"]
        waits: list[float] = []

        def connect() -> Loopback:
            if attempts.pop(0) == "refused":
                raise OSError("connection refused")
            return r.connect()

        r.peer._connect = connect

        def wait(seconds: float) -> bool:
            waits.append(seconds)
            return not attempts

        r.peer.run(wait)
        self.assertEqual(waits, [1.0, 2.0, 1.0, 2.0, 5.0])
        self.assertEqual(r.peer_logs, [
            "Hub link to hub.local:8765 failed: connection refused; redialling with backoff",
            "Hub link up: Home (hub.local:8765); sending 0 queued item(s)",
            "Hub link to Home lost: closed by the test; redialling",
            "Hub link to hub.local:8765 failed: connection refused; redialling with backoff",
        ])


class LinkedServerTests(unittest.TestCase):
    """A peer server asking a real hub app through a link session, no sockets."""

    @classmethod
    def setUpClass(cls) -> None:
        # Files the tests only read, made once for the class.
        tmp = TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.database = Path(tmp.name) / "markets.sqlite3"
        store = EddnStore.open(cls.database)
        store.save([SOL, GALILEO])
        store.close()
        cls.recent = Path(tmp.name) / "recent.json"
        save_recent_markets(cls.recent, (market(market_id=GALILEO.market_id), market(market_id=2, station="Abraham")))

    def setUp(self) -> None:
        self.r = rig(self)
        self.hub_app = server(market_database_file=self.database, hub_side=self.r.hub_side(),
                              eddn_status=lambda: {"store": {"markets": 3}}, ardent_lookup=None)
        self.r.handlers.update(self.hub_app.state.link_handlers)

    def peer_app(self, **options: Any):
        return server(peer_link=self.r.peer, recent_markets_file=self.recent, **options)

    def test_routes_status_and_best_deal_facts_come_from_the_hub_with_this_ships_inputs(self) -> None:
        saved = {"max_route_distance_ly": "17.2", "min_supply": "5000", "use_surface_stations": "no"}
        asked: list[dict[str, str]] = []
        real_parse = parse_route_query

        def spy(params, **inputs):
            asked.append(dict(params))
            return real_parse(params, **inputs)

        self.r.attach()
        peer = self.peer_app(data_provider=lambda: ship_data(system="Achenar", cargo_capacity=720))
        params = {"access_token": TOKEN}
        with (
            patch("edap.control_room.server.app.load_haul_search_config", return_value=saved),
            patch("edap.control_room.server.app.parse_route_query", side_effect=spy),
            TestClient(peer) as client,
        ):
            routes = client.get("/api/eddn-routes", params={**params, "jumps": "2", "min_supply": "any"})
            status = client.get("/api/eddn-status", params=params)
            deal = client.get("/api/market-compare", params={**params, "x": GALILEO.market_id, "y": 2})
            self.r.drop(self.r.links[-1])
            down = client.get("/api/eddn-routes", params=params)
            deal_down = client.get("/api/market-compare", params={**params, "x": GALILEO.market_id, "y": 2})

        self.assertEqual(asked[0]["system"], "Achenar")
        self.assertEqual((asked[0]["capacity"], asked[0]["laden_jump_range_ly"]), ("720", "17.2"))
        self.assertEqual(routes.json()["hub"], "Home")
        self.assertEqual(status.json(), {"enabled": True, "store": {"markets": 3}, "hub": "Home"})
        galileo = deal.json()["trip"]["stations"]["x"]
        self.assertEqual((galileo["dist_ls"], galileo["station_type"], galileo["coords_source"]), (505.0, "Ocellus", "store"))
        self.assertEqual((deal.json()["trip"]["hub"], deal.json()["trip"]["hint"]), ("Home", None))
        self.assertEqual(down.status_code, 502)
        self.assertEqual(down.json()["detail"], "Hub Home is unreachable: not connected to the hub: cable pulled")
        self.assertEqual(deal_down.json()["trip"]["hint"], "Hub Home is unreachable: not connected to the hub: cable pulled")

    def test_history_and_measured_profit_come_from_the_hubs_central_history(self) -> None:
        write_runs(self.r.own_runs, [haul_run("2026-11-10T09:00:00Z", ship_id=7, profit=1_000_000)])
        self.r.peer.enqueue_runs([haul_run("2026-11-10T10:00:00Z", ship_id=8, profit=3_000_000),
                                  haul_run("2026-11-10T11:00:00Z", ship_id=None, profit=5_000_000)])
        self.r.attach()
        params = {"access_token": TOKEN, "window": "all"}
        with (
            patch("edap.control_room.server.app.journal_trade_ledger", return_value=Ledger(True, 1)) as ledger,
            TestClient(self.hub_app) as hub, TestClient(self.peer_app(journal_dir=Path("journals"))) as peer,
        ):
            every = hub.get("/api/haul-stats", params=params).json()
            deck = hub.get("/api/haul-stats", params={**params, "node": "peer-node"}).json()
            ship_8 = hub.get("/api/haul-stats", params={**params, "ship": "8"}).json()
            from_peer = peer.get("/api/haul-stats", params=params).json()
            from_peer_hub_node = peer.get("/api/haul-stats", params={**params, "node": "hub-node"}).json()
            deal = peer.get("/api/market-compare", params={"access_token": TOKEN, "x": GALILEO.market_id, "y": 2,
                                                           "window": "all"}).json()
            self.r.drop(self.r.links[-1])
            down = peer.get("/api/haul-stats", params=params)
            deal_down = peer.get("/api/market-compare", params={"access_token": TOKEN, "x": GALILEO.market_id, "y": 2})

        self.assertEqual((every["runs"]["all_in"]["count"], every["runs"]["all_in"]["profit"]), (3, 9_000_000))
        self.assertEqual([(n["name"], n["local"]) for n in every["nodes"]], [("Home", True), ("Deck", False)])
        self.assertEqual([s["id"] for s in every["ships"]], [7, 8])
        self.assertEqual((deck["node"], deck["runs"]["all_in"]["profit"]), ("peer-node", 8_000_000))
        self.assertEqual((ship_8["ship"], ship_8["runs"]["all_in"]["count"]), (8, 1))
        # The peer shows the hub's answer with its own journal ledger, and none for another node's runs.
        self.assertEqual((from_peer["hub"], from_peer["runs"]["all_in"]["count"]), ("Home", 3))
        self.assertEqual((from_peer["journal"], from_peer["journal_node"]), ({"available": True, "profit": 1}, "Deck"))
        self.assertEqual((from_peer_hub_node["journal"], from_peer_hub_node["runs"]["all_in"]["count"]), (None, 1))
        self.assertEqual(ledger.call_count, 1)
        # This ship is unknown, so Best deal counts every node's runs on the pair.
        self.assertEqual((deal["measured"]["runs"], deal["measured"]["profit"], deal["measured_hint"]),
                         (3, 9_000_000, None))
        self.assertEqual(down.status_code, 502)
        self.assertEqual(down.json()["detail"], "Hub Home is unreachable: not connected to the hub: cable pulled")
        self.assertIsNone(deal_down.json()["measured"])
        self.assertEqual(deal_down.json()["measured_hint"], "Hub Home is unreachable: not connected to the hub: cable pulled")

    def test_measured_requests_are_checked_and_filter_by_ship(self) -> None:
        answer = self.hub_app.state.link_handlers["measured"]
        write_runs(self.r.own_runs, [haul_run("2026-11-10T09:00:00Z", ship_id=7),
                                     haul_run("2026-11-10T10:00:00Z", ship_id=8)])
        pair = [{"station": "Abraham", "system": "Sol"}, {"station": "Galileo", "system": "Sol"}]
        found = answer({"stations": pair, "ship_id": 8, "window": "all"})
        self.assertEqual((found.status, found.body["measured"]["runs"]), (200, 1))
        for body in ([], {"stations": pair[:1], "window": "all"}, {"stations": pair, "ship_id": "8", "window": "all"},
                     {"stations": pair, "window": "week"}):
            with self.subTest(body=body):
                self.assertEqual(answer(body).status, 400)
        self.assertEqual(self.hub_app.state.link_handlers["haul_stats"]({"ship": "Cutter"}).status, 400)

    def test_haul_search_runs_on_the_hub_and_reports_it_unreachable(self) -> None:
        result = TradeRouteSearchResult(system_name="Sol", query_url="https://inara.cz/x", searched_at="",
                                        routes=(TradeRoute(index=1, from_station="A", from_system="Sol",
                                                           to_station="B", to_system="Alioth"),))

        def search() -> dict[str, Any]:
            return asyncio.run(_handle_session_message_async(
                {"message_type": "command.search_haul_routes", "message_id": "m1",
                 "payload": {"max_route_distance_ly": "40 ly", "use_surface_stations": "no"}},
                session_id="s", client_role="active_operator", command_handler=None,
                broker=InMemoryObserverSessionBroker(), data_provider=ship_data, peer_link=self.r.peer,
            ))

        with (
            patch("edap.control_room.server.app.search_trade_routes", return_value=result) as inara,
            patch("edap.control_room.server.app.save_haul_search_config") as save_defaults,
        ):
            self.r.attach()
            found = search()
            self.r.drop(self.r.links[-1])
            down = search()

        self.assertEqual(save_defaults.call_count, 2)  # only the peer's own form defaults, never the hub's
        self.assertEqual(found["payload"]["result"]["hub"], "Home")
        self.assertEqual(found["payload"]["result"]["routes"][0]["to_system"], "Alioth")
        self.assertEqual(inara.call_args.kwargs["query_params"]["cargo_capacity"], "784")
        self.assertEqual(down["payload"]["error_code"], "hub_unreachable")
        self.assertIn("Hub Home is unreachable", down["payload"]["error_message"])

    def test_a_bad_search_from_a_peer_is_refused_by_the_hub(self) -> None:
        answer = self.hub_app.state.link_handlers["haul_search"]
        with (
            patch("edap.control_room.server.app.search_trade_routes", side_effect=RuntimeError("Inara is down")),
            self.assertLogs("edap.control_room.server.app", "ERROR"),
        ):
            not_an_object = answer([])
            failed = answer({})
        self.assertEqual((not_an_object.status, not_an_object.body["error_code"]), (400, "invalid_search"))
        self.assertEqual((failed.status, failed.body), (502, {"detail": "Inara is down", "error_code": "haul_search_failed"}))
        self.assertEqual(self.hub_app.state.link_handlers["station_facts"]({"stations": [{}]}).status, 400)

    def test_hub_status_and_nodes_for_each_role(self) -> None:
        self.r.attach()
        params = {"access_token": TOKEN}
        peer_broker = InMemoryObserverSessionBroker()
        with (
            TestClient(self.hub_app) as hub, TestClient(self.peer_app(broker=peer_broker)) as peer,
            TestClient(server()) as standalone,
        ):
            hub_status = hub.get("/api/hub-status", params=params).json()
            nodes = hub.get("/api/nodes", params=params)
            peer_status = peer.get("/api/hub-status", params=params).json()
            # The hub voices the peer: its own pages say it is muted, and stop saying so once unmuted.
            peer_broker.mute_callouts(True)
            muted = peer.get("/api/hub-status", params=params).json()["muted"]
            peer_broker.mute_callouts(False)
            unmuted = peer.get("/api/hub-status", params=params).json()["muted"]
            alone = standalone.get("/api/hub-status", params=params).json()
            not_a_hub = peer.get("/api/nodes", params=params)
            unauthorized = hub.get("/api/nodes")
            gone = [hub.post("/api/markets", json={}).status_code, hub.get("/api/hub-ping").status_code,
                    hub.post("/api/haul-search", json={}).status_code]

        self.assertEqual(hub_status, {"configured": True, "role": "hub", "node_id": "hub-node", "node_name": "Home",
                                      "peers_connected": 1, "muted": False})
        self.assertEqual([node["name"] for node in nodes.json()["nodes"]], ["Home", "Deck"])
        self.assertEqual(
            {key: peer_status[key] for key in ("role", "connected", "hub_name", "host", "outbox_pending", "node_name",
                                               "muted")},
            {"role": "peer", "connected": True, "hub_name": "Home", "host": "hub.local:8765", "outbox_pending": 0,
             "node_name": "Deck", "muted": False},
        )
        self.assertEqual((muted, unmuted), (True, False))
        self.assertEqual(alone, {"configured": False, "role": "standalone"})
        self.assertEqual((not_a_hub.status_code, unauthorized.status_code), (404, 401))
        self.assertEqual(gone, [404, 404, 404])

    def test_the_websocket_endpoint_needs_the_hub_token_and_carries_frames(self) -> None:
        self.r.handlers.clear()
        entry = roundtrip(snapshot_entry(market()))
        with TestClient(self.hub_app) as client:
            for headers in ({}, {"Authorization": f"Bearer {TOKEN}"}):
                with self.subTest(headers=headers), self.assertRaises(WebSocketDisconnect):
                    with client.websocket_connect("/api/peer-link", headers=headers):
                        pass
            with client.websocket_connect("/api/peer-link", headers={"Authorization": f"Bearer {HUB_TOKEN}"}) as ws:
                ws.send_json({"type": "hello", "node_id": "peer-node", "name": "Deck", "version": "1.0.0"})
                welcome = ws.receive_json()
                ws.send_json({"type": "item", "seq": 7, "kind": "market", "body": entry})
                ack = ws.receive_json()
                ws.send_json({"type": "request", "id": "1", "kind": "eddn_status", "body": {}})
                response = ws.receive_json()
                ws.send_json({"type": "ping"})
                pong = ws.receive_json()
            with TestClient(server()) as standalone, self.assertRaises(WebSocketDisconnect):
                with standalone.websocket_connect("/api/peer-link"):
                    pass

        self.assertEqual(welcome, {"type": "welcome", "node_id": "hub-node", "name": "Home", "version": "1.0.0"})
        self.assertEqual(ack, {"type": "ack", "seq": 7})
        self.assertEqual(self.r.store.counts().markets, 1)
        self.assertEqual(response, {"type": "response", "id": "1", "status": 200,
                                    "body": {"enabled": True, "store": {"markets": 3}}})
        self.assertEqual(pong, {"type": "pong"})
        self.assertFalse(self.r.registry.nodes()[1]["connected"])

    def test_resolved_params_parse_the_same_on_a_hub_without_defaults(self) -> None:
        saved = {"max_route_distance_ly": "17.2", "min_supply": "5000", "min_landing_pad": "medium",
                 "use_surface_stations": "yes_with_odyssey", "max_price_age_hours": "8", "max_station_distance_ls": "1000"}
        for params in ({}, {"jumps": "2", "pad": "S", "max_age_hours": "any"}, {"view": "global", "system": "Lave"}):
            here = parse_route_query(params, search_defaults=saved, current_system="Sol", cargo_capacity=720)
            resolved = resolve_route_params(params, search_defaults=saved, current_system="Sol", cargo_capacity=720)
            self.assertEqual(parse_route_query(resolved, search_defaults={}, current_system="", cargo_capacity=0), here)

    def test_every_page_with_a_sidebar_loads_the_hub_chip(self) -> None:
        with TestClient(server()) as client:
            script = client.get("/assets/hub-status.js")
            pages = {path: client.get(path, params={"access_token": TOKEN}).text
                     for path in ("/haul", "/multi-haul", "/controls", "/markets", "/routes")}
        self.assertIn("/api/hub-status", script.text)
        for path, page in pages.items():
            with self.subTest(path=path):
                self.assertIn('id="hub-chip" hidden', page)
                self.assertIn('src="/assets/hub-status.js"', page)


if __name__ == "__main__":
    unittest.main()
