"""Plan 0015 steps 5 and 6: hub pages look at and drive a peer through the link (no sockets, an in-memory link)."""
from __future__ import annotations

import base64
import json
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from starlette.websockets import WebSocketDisconnect
from textual import work
from textual.app import App

from edap.control_room.protocol import ActivityLogEntry
from edap.control_room.protocol.events import AnnouncementEvent
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.eddn.store import EddnStore
from edap.hub.relay import HubRelay, NodeOffline, PeerRelay, node_state
from edap.hub.voice import HubVoice
from edap.recent_markets import save_recent_markets
from tests.shared_loop import TestClient
from tests.test_control_room_server import _base_data_read_model, _CommandHandlerRecorder
from tests.test_hub import GALILEO, HUB_TOKEN, PEER_NODE, SOL, TOKEN, market, rig, server

PAGE = {"access_token": TOKEN}


def peer_data(routine: str | None = None) -> object:
    data = _base_data_read_model()
    ship = replace(data.ship, system="Achenar", ship_id=8, ship_type="type9", ship_name="Lugger", cargo_capacity=720,
                   laden_jump_range_ly=31.5)
    return replace(data, ship=ship, routine=replace(data.routine, routine_active=routine is not None,
                                                    active_routine_name=routine))


def hub_data() -> object:
    data = _base_data_read_model()
    return replace(data, ship=replace(data.ship, ship_id=7, ship_type="cutter", ship_name="Home Run"))


def run_now(work) -> None:
    work()


class PeerCommands(_CommandHandlerRecorder):
    """The peer's command handler; `during` runs inside each command, so a test can pull the cable then."""

    def __init__(self) -> None:
        super().__init__()
        self.during = lambda raw_input: None

    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> bool:
        self.during(raw_input)
        return super().submit_input(raw_input, skip_delay=skip_delay)


class RoutineHost(App):
    """Starts a routine as the headless host does: a Textual thread worker of an app that is never run.
    The routine flies until it is stopped, or gives up after a guard so a broken stop cannot hang the test."""

    def __init__(self) -> None:
        super().__init__()
        self.stop = threading.Event()
        self.ended = threading.Event()
        self.stopped = False

    def call_from_thread(self, callback, *args, **kwargs):  # type: ignore[override]
        # As the headless host: Textual starts a worker through this when called off the app's thread.
        return callback(*args, **kwargs)

    @work(thread=True, group="routines", exclusive=True)
    def fly(self) -> None:
        self.stopped = self.stop.wait(2.0)
        self.ended.set()


class RoutineCommands(PeerCommands):
    """`haul` starts a routine on a real worker; a stop cancels it, as the host's commands do."""

    def __init__(self) -> None:
        super().__init__()
        self.host = RoutineHost()
        self.worker: Any = None

    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> bool:
        if raw_input == "haul":
            self.worker = self.host.fly()
        return super().submit_input(raw_input, skip_delay=skip_delay)

    def cancel_active_routine(self, *, stop_mode: str = "toggle") -> None:
        super().cancel_active_routine(stop_mode=stop_mode)
        self.worker.cancel()
        self.host.stop.set()


def journal(directory: Path, total_sale: int) -> Path:
    """A journal folder with one sale bought at 10 per ton."""
    directory.mkdir()
    (directory / "Journal.2020-01-01T000000.01.log").write_text(json.dumps({
        "event": "MarketSell", "timestamp": "2020-01-01T01:00:00Z", "Type": "gold", "Count": 1,
        "TotalSale": total_sale, "AvgPricePaid": 10}) + "\n", encoding="utf-8")
    return directory


class RelayTests(unittest.TestCase):
    """A hub app and a peer app joined by the in-memory link, as a hub page sees them."""

    @classmethod
    def setUpClass(cls) -> None:
        # Files the tests only read, made once for the class.
        tmp = TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        root = Path(tmp.name)
        cls.database = root / "markets.sqlite3"
        store = EddnStore.open(cls.database)
        store.save([SOL, GALILEO])
        store.close()
        cls.peer_recent = root / "peer_recent.json"
        save_recent_markets(cls.peer_recent, (market(market_id=GALILEO.market_id), market(market_id=2, station="Abraham")))
        cls.hub_recent = root / "hub_recent.json"
        # The hub lists the peer's markets beside its own: the peer pushed them up.
        save_recent_markets(cls.hub_recent, (market(market_id=5, station="Jameson Memorial", system="Shinrarta"),
                                             market(market_id=GALILEO.market_id), market(market_id=2, station="Abraham")))
        cls.hub_journals = journal(root / "hub_journals", 50)
        cls.peer_journals = journal(root / "peer_journals", 90)

    def setUp(self) -> None:
        self.routine: str | None = None
        self.peer_broker = InMemoryObserverSessionBroker()
        self.commands = PeerCommands()
        self.logs: list[str] = []
        # How the peer runs reads and commands off the link thread; a test may hold them back.
        self.background = run_now
        # Each mute the hub set on the peer's own callouts.
        self.peer_mutes: list[bool] = []
        self.peer_relay = PeerRelay(
            open_session=lambda channel_id: self.peer_app.state.open_node_session(channel_id),
            add_listener=self.peer_broker.add_listener,
            answer_command=lambda channel_id, message: self.peer_app.state.answer_node_command(channel_id, message),
            answer_read=lambda path, params: self.peer_app.state.answer_node_read(path, params),
            answer_action=lambda path, body: self.peer_app.state.answer_node_action(path, body),
            state=lambda: node_state(peer_data(self.routine)),
            set_muted=self.peer_mutes.append,
            run_in_background=lambda work: self.background(work),
            log=self.logs.append,
        )
        self.r = rig(self, peer_relay=self.peer_relay)
        self.hub_app = server(data_provider=hub_data, market_database_file=self.database,
                              recent_markets_file=self.hub_recent, ardent_lookup=None,
                              journal_dir=self.hub_journals,
                              hub_side=self.r.hub_side())
        self.r.handlers.update(self.hub_app.state.link_handlers)
        self.peer_app = server(data_provider=lambda: peer_data(self.routine), broker=self.peer_broker,
                               peer_link=self.r.peer, recent_markets_file=self.peer_recent,
                               command_handler=self.commands,
                               journal_dir=self.peer_journals)

    def activity(self, text: str) -> None:
        self.peer_broker.publish_activity_log(ActivityLogEntry(entry_id=text, timestamp="2026-11-11T09:00:00Z",
                                                               message_text=text))

    def test_a_hub_page_sees_the_peers_session_and_drives_it(self) -> None:
        self.r.attach()
        with TestClient(self.hub_app) as hub:
            with hub.websocket_connect("/session", params={**PAGE, "node": "peer-node", "client_name": "web-haul"}) as page:
                ready = page.receive_json()
                hydrate = page.receive_json()
                self.assertEqual(self.peer_relay.channels(), 1)
                self.activity("Undocked at Galileo")
                event = page.receive_json()
                page.send_json({"message_type": "command.submit_input", "message_id": "m1",
                                "payload": {"raw_input": "say hello", "skip_delay": True}})
                ran = page.receive_json()
                page.send_json({"message_type": "command.cancel_active_routine", "message_id": "m2",
                                "payload": {"mode": "after_run"}})
                stopped = page.receive_json()
                page.send_json({"message_type": "command.request_active_operator", "message_id": "m3"})
                operator = page.receive_json()
                page.send_json({"message_type": "command.fly_to_the_moon", "message_id": "m4"})
                bad = page.receive_json()
            with hub.websocket_connect("/session", params={**PAGE, "node": "hub-node"}) as local:
                local.receive_json()
                local_hydrate = local.receive_json()

        self.assertEqual((ready["message_type"], ready["payload"]["client_role"]), ("event.connection_ready", "active_operator"))
        self.assertEqual(hydrate["payload"]["ship"]["system"], "Achenar")
        self.assertEqual(event["payload"]["entry"]["message_text"], "Undocked at Galileo")
        # The peer ran them through its own handler; the answers come back as a local page gets them.
        self.assertEqual(self.commands.submitted_inputs, [("say hello", True)])
        self.assertEqual(self.commands.cancel_modes, ["after_run"])
        self.assertEqual((ran["message_type"], ran["correlation_message_id"], ran["payload"]["message_text"]),
                         ("response.success", "m1", "Command accepted."))
        self.assertEqual((stopped["correlation_message_id"], stopped["payload"]["message_text"]),
                         ("m2", "Routine stop-after-run requested."))
        self.assertEqual((operator["correlation_message_id"], operator["payload"]["error_code"]),
                         ("m3", "unsupported_message_type"))
        self.assertEqual((bad["correlation_message_id"], bad["payload"]["error_message"]),
                         ("m4", "Unsupported message type: command.fly_to_the_moon"))
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
            config = hub.get("/api/route-compare/config", params=on_peer)
            bad = hub.get("/api/route-compare", params=on_peer)
            stats = hub.get("/api/haul-stats", params={**PAGE, "node": "peer-node", "window": "all"}).json()
            self.r.drop(self.r.links[-1])
            gone = hub.get("/api/route-compare/config", params=on_peer)

        self.assertEqual(config.json(), {"navroute_wait_seconds": 6.0, "compare_retry_attempts": 3})
        self.assertEqual(bad.status_code, 400)
        # Haul history is the hub's own: `node` there filters the central history.
        self.assertEqual(stats["node"], "peer-node")
        self.assertEqual(gone.status_code, 502)
        self.assertEqual(gone.json()["detail"], "Node Deck is unreachable: not linked to the hub")

    def test_markets_are_the_hubs_own_list_priced_for_the_picked_nodes_last_ship(self) -> None:
        self.r.attach()
        on_peer = {**PAGE, "node": "peer-node"}
        with TestClient(self.hub_app) as hub:
            peer_markets = hub.get("/api/recent-markets", params=on_peer).json()
            hub_markets = hub.get("/api/recent-markets", params=PAGE).json()
            deal = hub.get("/api/market-compare", params={**on_peer, "x": GALILEO.market_id, "y": 2}).json()
            self.r.drop(self.r.links[-1])
            offline = hub.get("/api/recent-markets", params=on_peer)
            offline_deal = hub.get("/api/market-compare", params={**on_peer, "x": GALILEO.market_id, "y": 2})

        # One list, whichever node is picked: the hub's own markets and the ones its peers pushed.
        stations = ["Jameson Memorial", "Galileo", "Abraham"]
        self.assertEqual([m["station"] for m in hub_markets["markets"]], stations)
        self.assertEqual([m["station"] for m in peer_markets["markets"]], stations)
        # Hold and laden range are the picked node's ship; the hub's own otherwise.
        self.assertEqual((peer_markets["cargo_capacity"], peer_markets["laden_jump_range_ly"]), (720, 31.5))
        self.assertNotEqual(hub_markets["cargo_capacity"], 720)
        self.assertEqual(deal["trip"]["stations"]["x"]["dist_ls"], 505.0)
        self.assertEqual((deal["measured_ship"]["id"], deal["measured_ship"]["laden_jump_range_ly"]), (8, 31.5))
        # Offline, the node's last reported ship still prices the page.
        self.assertEqual((offline.status_code, offline.json()["cargo_capacity"]), (200, 720))
        self.assertEqual((offline_deal.status_code, offline_deal.json()["measured_ship"]["id"]), (200, 8))

    def test_command_and_stop_posts_run_on_the_peer_with_its_own_refusals(self) -> None:
        self.r.attach()
        on_peer = {**PAGE, "node": "peer-node"}
        with TestClient(self.hub_app) as hub:
            ran = hub.post("/api/command", params=on_peer, json={"raw_input": "say hello"})
            idle_stop = hub.post("/api/stop", params=on_peer)
            self.routine = "haul"
            self.commands.accept_inputs = False
            busy = hub.post("/api/command", params=on_peer, json={"raw_input": "undock"})
            stop = hub.post("/api/stop", params=on_peer, json={"mode": "after_run"})
            empty = hub.post("/api/command", params=on_peer, json={"raw_input": " "})
            self.r.drop(self.r.links[-1])
            gone = hub.post("/api/command", params=on_peer, json={"raw_input": "undock"})

        self.assertEqual((ran.status_code, ran.json()["accepted"]), (200, True))
        self.assertEqual((idle_stop.status_code, idle_stop.json()["detail"]), (409, "No routine is running."))
        self.assertEqual((busy.status_code, busy.json()["detail"]),
                         (409, "Refused: haul is already running. Stop it or wait for it to finish."))
        self.assertEqual((stop.status_code, stop.json()["stopped_routine_name"]), (200, "haul"))
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(self.commands.submitted_inputs, [("say hello", None), ("undock", None)])
        self.assertEqual(self.commands.cancel_modes, ["after_run"])
        self.assertEqual((gone.status_code, gone.json()["detail"]), (502, "Node Deck is unreachable: not linked to the hub"))

    def test_a_command_cut_off_or_unanswered_gets_an_error_instead_of_a_hang(self) -> None:
        link = self.r.attach()
        # Off the link thread, as live: the hub holds its relay lock while it sends a command down.
        self.background = lambda work: threading.Thread(target=work, daemon=True).start()
        self.commands.during = lambda raw_input: self.r.drop(link)
        held: list[Any] = []
        with patch("edap.control_room.server.app.NODE_RETRY_S", 60.0), TestClient(self.hub_app) as hub:
            with hub.websocket_connect("/session", params={**PAGE, "node": "peer-node"}) as page:
                page.receive_json()
                page.receive_json()
                page.send_json({"message_type": "command.submit_input", "message_id": "m1",
                                "payload": {"raw_input": "undock"}})
                cut = page.receive_json()
                offline = page.receive_json()
                page.send_json({"message_type": "command.submit_input", "message_id": "m2",
                                "payload": {"raw_input": "undock"}})
                while_offline = page.receive_json()
            self.r.attach()
            self.background = held.append
            with patch.object(self.r.relay, "command_timeout_s", return_value=0.002), \
                    hub.websocket_connect("/session", params={**PAGE, "node": "peer-node"}) as page:
                page.receive_json()
                page.receive_json()
                page.send_json({"message_type": "command.submit_input", "message_id": "m3",
                                "payload": {"raw_input": "undock"}})
                late = page.receive_json()

        self.assertEqual((cut["message_type"], cut["correlation_message_id"]), ("response.error", "m1"))
        self.assertEqual((cut["payload"]["error_code"], cut["payload"]["error_message"]),
                         ("node_unreachable", "Node Deck is unreachable: the link closed"))
        self.assertEqual(offline["message_type"], "event.activity_log_appended")
        self.assertEqual((while_offline["correlation_message_id"], while_offline["payload"]["error_message"]),
                         ("m2", "Node Deck is unreachable: not linked to the hub"))
        self.assertEqual((late["correlation_message_id"], late["payload"]["error_message"]),
                         ("m3", "Node Deck is unreachable: no answer in 0.002 s"))
        self.assertEqual(len(held), 1)

    def test_a_channels_commands_run_one_at_a_time_in_order(self) -> None:
        sent: list[dict[str, Any]] = []
        held: list[Any] = []
        self.background = held.append
        self.peer_relay.link_up(sent.append)
        self.peer_relay.on_frame({"type": "channel_open", "channel": "c1", "client_name": "web"})
        for number in (1, 2):
            self.peer_relay.on_frame({"type": "channel_command", "channel": "c1", "message": {
                "message_type": "command.submit_input", "message_id": f"m{number}",
                "payload": {"raw_input": f"say {number}"}}})
        self.peer_relay.on_frame({"type": "channel_command", "channel": "c1",
                                  "message": {"message_type": "event.hydrate", "message_id": "m3"}})
        self.peer_relay.on_frame({"type": "channel_command", "channel": "c9", "message": {}})
        self.assertEqual(len(held), 1)
        held.pop()()
        answers = [f["message"] for f in sent if f["type"] == "channel" and "correlation_message_id" in f["message"]]
        self.assertEqual([(a["correlation_message_id"], a["message_type"]) for a in answers],
                         [("m1", "response.success"), ("m2", "response.success"), ("m3", "response.error")])
        self.assertEqual(answers[2]["payload"]["error_code"], "invalid_command")
        self.assertEqual(self.commands.submitted_inputs, [("say 1", None), ("say 2", None)])
        self.assertEqual(self.logs, ["Hub command for channel c9, which is not open here: dropped"])

    def test_a_hub_page_stops_a_routine_it_started_at_once(self) -> None:
        # The peer runs hub commands off the link thread, as it does live; the routine is a real worker.
        self.background = lambda work: threading.Thread(target=work, daemon=True).start()
        self.commands = RoutineCommands()
        self.peer_app = server(data_provider=lambda: peer_data(self.routine), broker=self.peer_broker,
                               peer_link=self.r.peer, command_handler=self.commands)
        self.r.attach()
        with TestClient(self.hub_app) as hub:
            with hub.websocket_connect("/session", params={**PAGE, "node": "peer-node"}) as page:
                page.receive_json()
                page.receive_json()
                page.send_json({"message_type": "command.submit_input", "message_id": "m1",
                                "payload": {"raw_input": "haul", "skip_delay": True}})
                started = page.receive_json()
                running_when_answered = not self.commands.host.ended.is_set()
                page.send_json({"message_type": "command.cancel_active_routine", "message_id": "m2",
                                "payload": {"mode": "now"}})
                stopped = page.receive_json()
        self.assertTrue(self.commands.host.ended.wait(2.0))

        self.assertEqual((started["correlation_message_id"], started["message_type"]), ("m1", "response.success"))
        self.assertTrue(running_when_answered)
        self.assertEqual((stopped["correlation_message_id"], stopped["message_type"]), ("m2", "response.success"))
        self.assertTrue(self.commands.host.stopped)
        self.assertEqual(self.commands.cancel_modes, ["now"])

    def test_only_the_hub_sends_commands_down_never_a_peer_up(self) -> None:
        link = self.r.attach()
        self.assertEqual(link.session.receive({"type": "channel_command", "channel": "c1", "message": {
            "message_type": "command.submit_input", "message_id": "m1", "payload": {"raw_input": "undock"}}}), [])
        self.assertEqual(link.session.receive({"type": "act", "id": "a1", "path": "/api/command",
                                               "body": {"raw_input": "undock"}}), [])
        self.assertEqual(self.r.relay.act("peer-node", "/api/eddn-routes", {}).status, 403)
        # Nothing on a peer listens for the hub's frames: it gets them only on the link it dialled.
        with TestClient(self.peer_app) as peer, self.assertRaises(WebSocketDisconnect) as refused:
            peer.websocket_connect("/api/peer-link", params=PAGE).__enter__()
        self.assertEqual(refused.exception.code, 4404)
        self.assertEqual(self.commands.submitted_inputs, [])

    def test_the_haul_journal_ledger_is_the_viewed_nodes(self) -> None:
        self.r.attach()
        with TestClient(self.hub_app) as hub:
            def stats(**params: str) -> dict[str, Any]:
                return hub.get("/api/haul-stats", params={**PAGE, "window": "all", **params}).json()

            own = stats()
            viewed = stats(view_node="peer-node")
            filtered_away = stats(view_node="peer-node", node="hub-node")
            self.r.drop(self.r.links[-1])
            offline = stats(view_node="peer-node")

        self.assertEqual((own["journal_node"], own["journal"]["sell_margin"]), ("Home", 40))
        self.assertEqual((viewed["journal_node"], viewed["journal"]["sell_margin"]), ("Deck", 80))
        self.assertEqual((filtered_away["journal_node"], filtered_away["journal"]), ("Deck", None))
        self.assertEqual((offline["journal_node"], offline["journal"]), ("Deck", None))

    def test_only_allowlisted_reads_reach_a_peer(self) -> None:
        self.r.attach()
        self.assertEqual(self.r.relay.read("peer-node", "/api/haul-stats", {}).status, 403)
        sent: list[dict[str, Any]] = []
        self.peer_relay.link_up(sent.append)
        self.peer_relay.on_frame({"type": "read", "id": "r1", "path": "/api/command", "params": {}})
        self.peer_relay.on_frame({"type": "read", "id": "r2", "path": "/api/route-compare/config", "params": []})
        self.assertEqual([(f["id"], f["status"]) for f in sent if f["type"] == "read_response"],
                         [("r1", 403), ("r2", 400)])
        with self.assertRaises(NodeOffline):
            self.r.relay.read("nobody", "/api/route-compare/config", {})

    def test_the_node_list_shows_each_nodes_ship_and_routine(self) -> None:
        self.r.attach()
        with TestClient(self.hub_app) as hub:
            first = hub.get("/api/nodes", params=PAGE).json()["nodes"]
            self.routine = "haul"
            self.activity("Haul started")
            hauling = hub.get("/api/nodes", params=PAGE).json()["nodes"]
            self.r.drop(self.r.links[-1])
            offline = hub.get("/api/nodes", params=PAGE).json()["nodes"]

        self.assertEqual({key: first[0]["state"]["ship"][key] for key in ("id", "type", "name")},
                         {"id": 7, "type": "cutter", "name": "Home Run"})
        self.assertEqual(first[1]["state"], {"ship": {"id": 8, "type": "type9", "name": "Lugger", "cargo_capacity": 720,
                                                      "laden_jump_range_ly": 31.5}, "routine": None})
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

    def callout(self, text: str) -> None:
        """The peer speaks a callout, as its Control Room publishes it."""
        self.peer_broker.publish_announcement(AnnouncementEvent(announcement_id="docking_complete", message_text=text))

    def test_the_hub_voices_the_picked_node_and_its_speakers_only_when_on(self) -> None:
        voice = self.r.voice
        heard: list[dict[str, Any]] = []
        voice.add_listener(heard.append)
        self.callout("Missed while the link is down.")
        link = self.r.attach()
        self.callout("Docked at Galileo.")  # nothing picked: the hub's own game is voiced
        voice.callout("hub-node", "Hub game docked.")
        voice.update({"node_id": "peer-node"})
        self.callout("Undocking,  commander.")
        voice.update({"speakers": True})
        self.callout("Jump initiated.")
        voice.callout("hub-node", "Hub game docked again.")  # not the voiced node
        voice.update({"node_id": None})
        voice.callout("hub-node", "Hub game undocking.")
        self.callout("Peer not voiced now.")
        saved = HubVoice(local_node_id="hub-node", settings_file=self.r.tmp_path / "voice.json", speak=self.fail,
                         synthesize=None, names=str, set_muted=self.fail, run_in_background=run_now,
                         log=self.logs.append).settings()

        self.assertEqual([frame["text"] for frame in link.sent if frame["type"] == "callout"],
                         ["Docked at Galileo.", "Undocking,  commander.", "Jump initiated.", "Peer not voiced now."])
        # Hub speakers: the voiced peer only, never the hub's own game (it already spoke there).
        self.assertEqual(self.r.spoken, ["Jump initiated."])
        callouts = [(m["node_name"], m["text"], base64.b64decode(m["wav"]).decode()) for m in heard if m["type"] == "callout"]
        self.assertEqual(callouts, [("Home", "Hub game docked.", "WAV Hub game docked."),
                                    ("Deck", "Undocking, commander.", "WAV Undocking, commander."),
                                    ("Deck", "Jump initiated.", "WAV Jump initiated."),
                                    ("Home", "Hub game undocking.", "WAV Hub game undocking.")])
        self.assertEqual([m["settings"]["node_name"] for m in heard if m["type"] == "settings"],
                         ["Home", "Deck", "Deck", "Home"])
        self.assertEqual((saved["node_id"], saved["speakers"], saved["mute"], saved["piper"]),
                         ("hub-node", True, False, False))

    def test_a_muted_node_plays_only_on_the_hub_and_unmutes_whenever_it_could_be_lost(self) -> None:
        voice = self.r.voice
        link = self.r.attach()
        voice.update({"node_id": "peer-node", "mute": True})  # nothing plays on the hub yet
        unheard = list(self.peer_mutes)
        voice.update({"speakers": True})
        self.callout("Docked at Galileo.")
        on_the_link = [frame["text"] for frame in link.sent if frame["type"] == "callout"]
        self.r.drop(link)  # the peer unmutes itself
        dropped = list(self.peer_mutes)
        self.r.attach()  # the hub mutes it again
        relinked = list(self.peer_mutes)
        voice.update({"speakers": False})  # nothing plays on the hub: unmuted
        remove = voice.add_listener(lambda message: None)  # a page listens: muted again
        listening = list(self.peer_mutes)
        remove()
        voice.add_listener(lambda message: None)
        voice.update({"node_id": "hub-node"})  # another node: the peer unmutes and the mute clears

        self.assertEqual(unheard, [])
        self.assertEqual(on_the_link, ["Docked at Galileo."])
        self.assertEqual(self.r.spoken, ["Docked at Galileo."])
        self.assertEqual(dropped, [True, False])
        self.assertEqual(relinked, [True, False, True])
        self.assertEqual(listening, [True, False, True, False, True])
        self.assertEqual(self.peer_mutes, [True, False, True, False, True, False, True, False])
        self.assertEqual(self.r.hub_mutes, [])
        self.assertFalse(voice.settings()["mute"])
        # The hub's own game mutes directly; its speakers do not count, they are its own.
        voice.update({"mute": True})
        self.assertEqual((self.r.hub_mutes, voice.settings()["muted"]), ([True], True))
        voice.update({"mute": False})
        self.assertEqual(self.r.hub_mutes, [True, False])
        self.assertIn("The hub voices this node: its own speakers are muted", self.logs)

    def test_a_muted_node_stamps_its_announcements_so_its_pages_stay_quiet(self) -> None:
        sent: list[dict[str, Any]] = []
        self.peer_broker.add_listener(sent.append)
        self.peer_broker.mute_callouts(True)
        self.callout("Docked.")
        self.peer_broker.mute_callouts(False)
        self.callout("Undocking.")
        self.assertEqual([(m["payload"]["message_text"], m["payload"].get("muted")) for m in sent],
                         [("Docked.", True), ("Undocking.", None)])

    def test_without_piper_pages_get_the_text_to_speak_themselves(self) -> None:
        heard: list[dict[str, Any]] = []
        logs: list[str] = []

        def broken(text: str) -> bytes:
            raise OSError("Piper wrote no audio")

        for synthesize in (None, broken):
            voice = HubVoice(local_node_id="hub-node", settings_file=self.r.tmp_path / "voice.json", speak=self.fail,
                             synthesize=synthesize, names=lambda node_id: "Deck", set_muted=self.fail,
                             run_in_background=run_now, log=logs.append)
            voice.update({"node_id": "peer-node"})
            voice.add_listener(heard.append)
            voice.callout("peer-node", "Docked.")

        self.assertEqual([(m["text"], m["wav"]) for m in heard if m["type"] == "callout"], [("Docked.", None)] * 2)
        self.assertIn("Hub voice: Piper failed, pages speak the text: Piper wrote no audio", logs)
        with self.assertRaises(ValueError):
            voice.update({"speakers": "yes"})
        with self.assertRaises(ValueError):
            voice.update({"volume": 3})

    def test_a_hub_page_sets_the_voice_and_listens(self) -> None:
        self.r.attach()
        with TestClient(self.hub_app) as hub, TestClient(self.peer_app) as peer:
            default = hub.get("/api/hub-voice", params=PAGE).json()
            bad = hub.post("/api/hub-voice", params=PAGE, json={"speakers": 1})
            with hub.websocket_connect("/api/hub-voice/listen", params=PAGE) as page:
                first = page.receive_json()
                chosen = hub.post("/api/hub-voice", params=PAGE, json={"node_id": "peer-node", "speakers": True}).json()
                told = page.receive_json()
                self.callout("Docked at Galileo.")
                heard = page.receive_json()
            not_a_hub = peer.get("/api/hub-voice", params=PAGE)
            with self.assertRaises(WebSocketDisconnect):
                with hub.websocket_connect("/api/hub-voice/listen") as stranger:
                    stranger.receive_json()

        self.assertEqual((default["node_id"], default["speakers"], default["mute"], default["piper"]),
                         ("hub-node", False, False, True))
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(first, {"type": "settings", "settings": default})
        self.assertEqual((chosen["node_name"], chosen["speakers"]), ("Deck", True))
        self.assertEqual(told["settings"], chosen)
        self.assertEqual((heard["node_id"], heard["text"], base64.b64decode(heard["wav"])),
                         ("peer-node", "Docked at Galileo.", b"WAV Docked at Galileo."))
        self.assertEqual(self.r.spoken, ["Docked at Galileo."])
        self.assertEqual(not_a_hub.status_code, 404)


if __name__ == "__main__":
    unittest.main()
