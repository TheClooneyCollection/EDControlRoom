"""Plan 0015 step 5: hub pages look at a peer through the link (no sockets, an in-memory link)."""
from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from starlette.testclient import TestClient

from edap.control_room.protocol import ActivityLogEntry
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.eddn.store import EddnStore
from edap.hub.nodes import HubSide
from edap.hub.relay import HubRelay, NodeOffline, PeerRelay, node_state
from edap.recent_markets import save_recent_markets
from tests.test_control_room_server import _base_data_read_model
from tests.test_hub import GALILEO, HUB_TOKEN, PEER_NODE, SOL, TOKEN, market, rig, server

PAGE = {"access_token": TOKEN}


def peer_data(routine: str | None = None) -> object:
    data = _base_data_read_model()
    ship = replace(data.ship, system="Achenar", ship_id=8, ship_type="type9", ship_name="Lugger", cargo_capacity=720)
    return replace(data, ship=ship, routine=replace(data.routine, routine_active=routine is not None,
                                                    active_routine_name=routine))


def hub_data() -> object:
    data = _base_data_read_model()
    return replace(data, ship=replace(data.ship, ship_id=7, ship_type="cutter", ship_name="Home Run"))


def run_now(work) -> None:
    work()


class RelayTests(unittest.TestCase):
    """A hub app and a peer app joined by the in-memory link, as a hub page sees them."""

    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.database = Path(tmp.name) / "markets.sqlite3"
        store = EddnStore.open(self.database)
        store.save([SOL, GALILEO])
        store.close()
        self.peer_recent = Path(tmp.name) / "peer_recent.json"
        save_recent_markets(self.peer_recent, (market(market_id=GALILEO.market_id), market(market_id=2, station="Abraham")))
        self.hub_recent = Path(tmp.name) / "hub_recent.json"
        save_recent_markets(self.hub_recent, (market(market_id=5, station="Jameson Memorial", system="Shinrarta"),))
        self.routine: str | None = None
        self.peer_broker = InMemoryObserverSessionBroker()
        self.logs: list[str] = []
        self.peer_relay = PeerRelay(
            open_session=lambda channel_id: self.peer_app.state.open_node_session(channel_id),
            add_listener=self.peer_broker.add_listener,
            answer_read=lambda path, params: self.peer_app.state.answer_node_read(path, params),
            state=lambda: node_state(peer_data(self.routine)),
            run_in_background=run_now,
            log=self.logs.append,
        )
        self.r = rig(self, peer_relay=self.peer_relay)
        self.hub_app = server(data_provider=hub_data, market_database_file=self.database,
                              recent_markets_file=self.hub_recent, ardent_lookup=None,
                              hub_side=HubSide(self.r.registry, self.r.store_item, HUB_TOKEN, self.r.history, self.r.relay))
        self.r.handlers.update(self.hub_app.state.link_handlers)
        self.peer_app = server(data_provider=lambda: peer_data(self.routine), broker=self.peer_broker,
                               peer_link=self.r.peer, recent_markets_file=self.peer_recent)

    def activity(self, text: str) -> None:
        self.peer_broker.publish_activity_log(ActivityLogEntry(entry_id=text, timestamp="2026-11-11T09:00:00Z",
                                                               message_text=text))

    def test_a_hub_page_sees_the_peers_session_and_its_commands_are_refused(self) -> None:
        self.r.attach()
        with TestClient(self.hub_app) as hub:
            with hub.websocket_connect("/session", params={**PAGE, "node": "peer-node", "client_name": "web-haul"}) as page:
                ready = page.receive_json()
                hydrate = page.receive_json()
                self.assertEqual(self.peer_relay.channels(), 1)
                self.activity("Undocked at Galileo")
                event = page.receive_json()
                page.send_json({"message_type": "command.submit_input", "message_id": "m1",
                                "payload": {"raw_input": "undock"}})
                refused = page.receive_json()
            with hub.websocket_connect("/session", params={**PAGE, "node": "hub-node"}) as local:
                local.receive_json()
                local_hydrate = local.receive_json()

        self.assertEqual((ready["message_type"], ready["payload"]["client_role"]), ("event.connection_ready", "observer"))
        self.assertEqual(hydrate["payload"]["ship"]["system"], "Achenar")
        self.assertEqual(event["payload"]["entry"]["message_text"], "Undocked at Galileo")
        self.assertEqual((refused["message_type"], refused["correlation_message_id"]), ("response.error", "m1"))
        self.assertEqual(refused["payload"]["error_code"], "node_view_only")
        self.assertEqual(refused["payload"]["error_message"],
                         "Deck is view-only from the hub for now: run commands on its own pages.")
        # The page left: the peer dropped its listener; the node state listener stays.
        self.assertEqual(self.peer_relay.channels(), 0)
        self.assertEqual(len(self.peer_broker._listeners), 1)
        # The hub's own node needs no relay.
        self.assertEqual(local_hydrate["payload"]["ship"]["system"], "Sol")

    def test_the_page_is_told_when_the_node_goes_offline_and_sees_it_again_when_it_links(self) -> None:
        link = self.r.attach()
        with patch("edap.control_room.server.app.NODE_RETRY_S", 0.001), TestClient(self.hub_app) as hub:
            with hub.websocket_connect("/session", params={**PAGE, "node": "peer-node"}) as page:
                page.receive_json()
                page.receive_json()
                self.r.drop(link)
                offline = page.receive_json()
                self.assertEqual(self.peer_relay.channels(), 0)
                self.r.attach()
                again = page.receive_json()
                hydrate = page.receive_json()
            with hub.websocket_connect("/session", params={**PAGE, "node": "nobody"}) as stray:
                unknown = stray.receive_json()

        self.assertEqual(offline["message_type"], "event.activity_log_appended")
        self.assertEqual((offline["payload"]["entry"]["severity"], offline["payload"]["entry"]["message_text"]),
                         ("error", "Node Deck is offline (the link closed); showing it again when it links."))
        self.assertEqual((again["message_type"], hydrate["payload"]["ship"]["system"]),
                         ("event.connection_ready", "Achenar"))
        self.assertEqual(unknown["payload"]["entry"]["message_text"],
                         "Node nobody is offline (not linked to the hub); showing it again when it links.")

    def test_node_reads_are_relayed_and_hub_owned_reads_are_not(self) -> None:
        self.r.attach()
        on_peer = {**PAGE, "node": "peer-node"}
        with TestClient(self.hub_app) as hub:
            peer_markets = hub.get("/api/recent-markets", params=on_peer).json()
            hub_markets = hub.get("/api/recent-markets", params=PAGE).json()
            # The peer's Best deal: its markets and cargo, station facts asked back from the hub.
            deal = hub.get("/api/market-compare", params={**on_peer, "x": GALILEO.market_id, "y": 2}).json()
            config = hub.get("/api/route-compare/config", params=on_peer)
            bad = hub.get("/api/route-compare", params=on_peer)
            stats = hub.get("/api/haul-stats", params={**PAGE, "node": "peer-node", "window": "all"}).json()
            command = hub.post("/api/command", params=on_peer, json={"raw_input": "undock"})
            stop = hub.post("/api/stop", params=on_peer)
            self.r.drop(self.r.links[-1])
            gone = hub.get("/api/recent-markets", params=on_peer)

        self.assertEqual([m["station"] for m in peer_markets["markets"]], ["Galileo", "Abraham"])
        self.assertEqual(peer_markets["cargo_capacity"], 720)
        self.assertEqual([m["station"] for m in hub_markets["markets"]], ["Jameson Memorial"])
        self.assertEqual(deal["trip"]["stations"]["x"]["dist_ls"], 505.0)
        self.assertEqual((deal["trip"]["hub"], deal["measured_ship"]["id"]), ("Home", 8))
        self.assertEqual(config.json(), {"navroute_wait_seconds": 6.0, "compare_retry_attempts": 3})
        self.assertEqual(bad.status_code, 400)
        # Haul history is the hub's own: `node` there filters the central history.
        self.assertEqual(stats["node"], "peer-node")
        self.assertEqual([c.status_code for c in (command, stop)], [403, 403])
        self.assertIn("view-only from the hub", command.json()["detail"])
        self.assertEqual(gone.status_code, 502)
        self.assertEqual(gone.json()["detail"], "Node Deck is unreachable: not linked to the hub")

    def test_only_allowlisted_reads_reach_a_peer(self) -> None:
        self.r.attach()
        self.assertEqual(self.r.relay.read("peer-node", "/api/haul-stats", {}).status, 403)
        sent: list[dict[str, Any]] = []
        self.peer_relay.link_up(sent.append)
        self.peer_relay.on_frame({"type": "read", "id": "r1", "path": "/api/command", "params": {}})
        self.peer_relay.on_frame({"type": "read", "id": "r2", "path": "/api/recent-markets", "params": []})
        self.assertEqual([(f["id"], f["status"]) for f in sent if f["type"] == "read_response"],
                         [("r1", 403), ("r2", 400)])
        with self.assertRaises(NodeOffline):
            self.r.relay.read("nobody", "/api/recent-markets", {})

    def test_the_node_list_shows_each_nodes_ship_and_routine(self) -> None:
        self.r.attach()
        with TestClient(self.hub_app) as hub:
            first = hub.get("/api/nodes", params=PAGE).json()["nodes"]
            self.routine = "haul"
            self.activity("Haul started")
            hauling = hub.get("/api/nodes", params=PAGE).json()["nodes"]
            self.r.drop(self.r.links[-1])
            offline = hub.get("/api/nodes", params=PAGE).json()["nodes"]

        self.assertEqual(first[0]["state"], {"ship": {"id": 7, "type": "cutter", "name": "Home Run"}, "routine": None})
        self.assertEqual(first[1]["state"], {"ship": {"id": 8, "type": "type9", "name": "Lugger"}, "routine": None})
        self.assertEqual(hauling[1]["state"]["routine"], "haul")
        self.assertEqual((offline[1]["connected"], offline[1]["state"]), (False, None))

    def test_a_channel_opened_before_the_welcome_starts_once_the_link_is_up(self) -> None:
        sent: list[dict[str, Any]] = []
        self.peer_relay.on_frame({"type": "channel_open", "channel": "c1", "client_name": "web"})
        self.peer_relay.on_frame({"type": "channel_open", "channel": "c2", "client_name": "web"})
        self.peer_relay.on_frame({"type": "channel_close", "channel": "c2"})
        self.peer_relay.link_up(sent.append)
        self.assertEqual([f["type"] for f in sent], ["node_state", "channel", "channel"])
        self.assertEqual(self.peer_relay.channels(), 1)
        self.peer_relay.link_down()
        self.assertEqual((self.peer_relay.channels(), len(self.peer_broker._listeners)), (0, 0))

    def test_a_reconnecting_peer_ends_pages_on_its_old_connection(self) -> None:
        relay = HubRelay(log=self.logs.append, read_timeout_s=1.0, slow_read_timeout_s=1.0)
        ended: list[str] = []
        relay.attach(PEER_NODE, 1, lambda frame: None)
        relay.open_channel("peer-node", "web", lambda message: None, ended.append)
        relay.attach(PEER_NODE, 2, lambda frame: None)
        relay.detach("peer-node", 1)  # the old connection's late close changes nothing
        self.assertEqual(ended, ["it reconnected"])
        self.assertEqual(relay.name("peer-node"), "Deck")


if __name__ == "__main__":
    unittest.main()
