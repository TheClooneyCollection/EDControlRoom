from __future__ import annotations

import asyncio
from dataclasses import replace
import logging
import unittest
import warnings
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated; install `httpx2` instead\.",
)


from edcr.config import (
    AppConfig,
    ControlRoomConfig,
    ControlsConfig,
    MarketBuyHoldSegmentConfig,
    PathsConfig,
    RuntimeConfig,
    TTSConfig,
)
from edcr.control_room.protocol.events import AnnouncementEvent
from edcr.control_room.protocol.sink import ControlRoomEventSink
from edcr.control_room.dependencies import (
    ActivityLogReadModel,
    CommandHistoryReadModel,
    ControlRoomDataReadModel,
    RoutineReadModel,
    ServerStatusReadModel,
    SessionReadModel,
)
from edcr.control_room.models import HaulStats, MarketData, ShipState
from edcr.control_room.protocol import ActivityLogEntry
from edcr.control_room.server import app as server_app
from edcr.control_room.server.app import (
    BROWSER_PROBE_URL_PATH,
    CONTROL_ROOM_MESSAGE_SCHEMA,
    HAUL_WEB_ENTRY_URL_PATH,
    HAUL_WEB_URL_PATH,
    MESSAGE_SCHEMA_URL_PATH,
    SUPPORTED_COMMAND_MESSAGE_TYPES,
    SUPPORTED_EVENT_MESSAGE_TYPES,
    SUPPORTED_MESSAGE_TYPES,
    SUPPORTED_RESPONSE_MESSAGE_TYPES,
    _handle_session_message,
    _render_haul_web_html,
    build_observer_server_app,
)
from edcr.control_room.server.auth import SharedAccessTokenAuth
from edcr.control_room.server.broker import InMemoryObserverSessionBroker
from edcr.control_room.server.commands import ObserverSessionCommandHandler
from edcr.control_room.server.host import HeadlessControlRoomHost
from tests.shared_loop import TestClient
from tests.test_control_room import _FakeVersionSource
from edcr.control_room.server.sink import DataHydrateFanoutSink, ServerActivityLogSink
from edcr.control_room.server.state import ControlRoomServerState
from edcr.inara.trade_routes import TradeRoute, TradeRouteSearchResult
from edcr.routing.route_cache import RouteRequestKey
from edcr.routing.types import Route, RouteWaypoint, SpanshMetadata
from edcr.runtime import ResolvedPath, RuntimeContext
from edcr.timing import TimingChannelConfig, TimingConfig, TimingSampler
from edcr.tts import AnnouncementId, NullSpeechBackend


def _make_timing_config() -> TimingConfig:
    channel = TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.0)
    return TimingConfig(enabled=False, distribution="log_normal", delay=channel, hold=channel, typing=channel)


def _make_config(journal_dir: Path) -> AppConfig:
    return AppConfig(
        paths=PathsConfig(journal_dir=journal_dir, bindings_file=None),
        controls=ControlsConfig(
            hardpoints_retract_timeout_seconds=5.0,
            start_hotkey="home",
            stop_hotkey="end",
            scanner_mode="off",
            minimum_action_hold_seconds=0.1,
            continuous_action_hold_seconds=0.2,
            step_delay_seconds=0.3,
            galaxy_map_settle_seconds=2.0,
            dock_supercruise_exit_settle_seconds=3.0,
            haul_dock_timeout_seconds=600.0,
            undock_timeout_seconds=30.0,
            undock_no_track_timeout_seconds=600.0,
            mass_lock_boost_delay_seconds=5.0,
            market_nav_delay_seconds=0.1,
            market_trade_max_attempts=3,
            market_buy_top_up_max_attempts=3,
            market_buy_max_hold_seconds=10.0,
            market_buy_hold_segments=(
                MarketBuyHoldSegmentConfig(start=0, function="flat", hold_seconds=1.0),
                MarketBuyHoldSegmentConfig(start=100, function="linear", seconds_per_ton=0.01),
                MarketBuyHoldSegmentConfig(start=301, function="log", base_seconds=-4.25, multiplier=1.1829),
            ),
            market_sell_quantity_restore_taps=5,
            market_sell_quantity_restore_tap_delay_seconds=0.05,
            market_critical_level_multiplier=10.0,
            haul_post_sell_settle_seconds=2.0,
            haul_two_way_auto_hyperspace_engage=True,
            haul_two_way_open_nav_panel_after_hyperspace_arrival=True,
            haul_two_way_nav_panel_open_delay_seconds=3.0,
        ),
        runtime=RuntimeConfig(platform="macos", debug=False),
        timing=_make_timing_config(),
        control_room=ControlRoomConfig(
            state_file=journal_dir / ".control_room_state.json",
            haul_runs_file=journal_dir / ".control_room_haul_runs.jsonl",
            recent_markets_file=journal_dir / ".control_room_recent_markets.json",
            history_limit=20,
            activity_log_max_lines=2000,
            command_delay_seconds=0.0,
            status_refresh_seconds=2.0,
        ),
        tts=TTSConfig(enabled=False, title="captain", disabled_messages=(), phrases={}),
    )


def _facts_db(directory: str, recent_markets: Path, events: list[dict]) -> Path:
    """A market store holding our recorded markets (with their Market.json types) and these journal events."""
    from edcr.eddn.game_markets import import_game_markets
    from edcr.eddn.messages import journal_event_updates
    from edcr.eddn.store import EddnStore

    path = Path(directory) / "markets.sqlite3"
    store = EddnStore.open(path)
    store.save([update for event in events for update in journal_event_updates(event)])
    import_game_markets(store, recent_markets)
    store.close()
    return path


def _drop_facts(updates: list) -> None:
    pass


def _make_context(journal_dir: Path) -> RuntimeContext:
    resolved = ResolvedPath(
        configured={"path": str(journal_dir), "status": "ok", "reason": "test journal dir"},
        auto_detected={"path": str(journal_dir), "status": "ok", "reason": "test journal dir"},
        effective={"path": str(journal_dir), "status": "ok", "source": "configured", "reason": "test journal dir"},
    )
    return RuntimeContext(
        config=_make_config(journal_dir),
        game_paths=None,
        journal=resolved,
        bindings=resolved,
        input_controller=None,
        timing_sampler=TimingSampler(_make_timing_config()),
        binding_lookup=None,
        config_path=journal_dir / "config.toml",
        used_example_config_fallback=False,
    )


def _make_context_with_tts(journal_dir: Path) -> RuntimeContext:
    ctx = _make_context(journal_dir)
    return RuntimeContext(
        config=replace(
            ctx.config,
            tts=replace(
                ctx.config.tts,
                enabled=True,
                title_mode="commander_name",
                phrases={
                    "arrival": "Arrived in {system_name}",
                    "startup_greeting": "Hello {title}",
                },
            ),
        ),
        game_paths=ctx.game_paths,
        journal=ctx.journal,
        bindings=ctx.bindings,
        input_controller=ctx.input_controller,
        timing_sampler=ctx.timing_sampler,
        binding_lookup=ctx.binding_lookup,
        config_path=ctx.config_path,
        used_example_config_fallback=ctx.used_example_config_fallback,
    )


def _base_data_read_model() -> ControlRoomDataReadModel:
    return ControlRoomDataReadModel(
        ship=ShipState(system="Sol", commander="CMDR TEST"),
        market=MarketData(station="Galileo", system="Sol"),
        haul_session=HaulStats(completed_runs=2),
        command_history=CommandHistoryReadModel(
            default_haul={},
            history_entries=(),
            history_limit=20,
        ),
        activity_log=ActivityLogReadModel(entries=()),
        routine=RoutineReadModel(
            routine_active=False,
            active_routine_name=None,
            haul_stop_requested=False,
            haul_pause_requested=False,
            haul_paused=False,
            verbose_controls=False,
            instant_mode=False,
            shutdown_requested=False,
            shutdown_finalized=False,
        ),
        session=SessionReadModel(
            session_id="local-server",
            client_role="active_operator",
            client_name="local-server",
            active_operator_name="local-server",
        ),
        server_status=ServerStatusReadModel(
            server_name="ED Control Room",
            server_version="1.2.3",
            runtime_platform="macos",
            journal_source_status="configured",
            bindings_source_status="configured",
            bindings_loaded=False,
            server_commit="b2a65e4+dirty",
        ),
    )


class _EventSinkRecorder(ControlRoomEventSink):
    def __init__(self) -> None:
        self.activity_entries: list[ActivityLogEntry] = []
        self.announcements: list[AnnouncementEvent] = []
        self.data_refresh_count = 0

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        self.activity_entries.append(entry)

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        self.announcements.append(event)

    def publish_data_refresh(self) -> None:
        self.data_refresh_count += 1


class _CommandHandlerRecorder(ObserverSessionCommandHandler):
    def __init__(self) -> None:
        self.submitted_inputs: list[tuple[str, bool | None]] = []
        self.accept_inputs = True
        self.dispatched_destinations: list[tuple[str, float, bool, str | None]] = []
        self.dispatched_hauls: list[tuple[dict[str, str] | None, bool, str | None]] = []
        self.dispatched_travels: list[tuple[str, str, bool, bool, str | None]] = []
        self.dispatched_spansh_routes: list[tuple[str, str, bool, str | None, int]] = []
        self.loaded_trade_routes: list[tuple[object, str | None]] = []
        self.cancel_modes: list[str] = []
        self.persisted_selected_trade_route = None
        self.persisted_running_trade_route = None

    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> bool:
        self.submitted_inputs.append((raw_input, skip_delay))
        return self.accept_inputs

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self.dispatched_destinations.append(
            (destination, galaxy_map_settle, skip_delay, raw_command)
        )

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self.dispatched_hauls.append((params, skip_delay, raw_command))

    def dispatch_travel(
        self,
        *,
        system: str,
        station: str,
        manual_landing: bool = False,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self.dispatched_travels.append((system, station, manual_landing, skip_delay, raw_command))

    def dispatch_spansh_route(
        self,
        *,
        route,
        station: str = "",
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self.dispatched_spansh_routes.append(
            (route.destination_system, station, skip_delay, raw_command, len(route.waypoints))
        )

    def load_trade_route(self, route, *, raw_command: str | None = None) -> None:
        self.loaded_trade_routes.append((route, raw_command))

    def cancel_active_routine(self, *, stop_mode="toggle") -> None:
        self.cancel_modes.append(stop_mode)

    def persist_trade_route_state(
        self,
        *,
        selected_trade_route=None,
        running_trade_route=None,
    ) -> None:
        if selected_trade_route is not None:
            self.persisted_selected_trade_route = selected_trade_route
        if running_trade_route is not None:
            self.persisted_running_trade_route = running_trade_route


class ControlRoomServerTests(unittest.TestCase):
    def test_headless_host_initializes_data_source_before_mount(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)

            data = host.dependencies.data_source.current()

        self.assertEqual(data.session.session_id, "local-session")
        self.assertFalse(data.routine.routine_active)

    def test_headless_host_accepts_simple_remote_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)

            host.handle_remote_input("market filter gold")

        self.assertIsNone(host._market_filter)
        self.assertIn("Unknown command: market filter gold", "\n".join(content.plain for content, _ in host._activity_widget.writes))
        self.assertEqual(host._saved_state.history[-1].command, "market")

    def test_headless_host_submit_input_alias_accepts_simple_remote_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)

            host.submit_input("market filter gold")

        self.assertIsNone(host._market_filter)
        self.assertIn("Unknown command: market filter gold", "\n".join(content.plain for content, _ in host._activity_widget.writes))

    def test_headless_host_accepts_stats_via_submit_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            host.submit_input("stats all")
            output = "\n".join(content.plain for content, _ in host._activity_widget.writes)
            self.assertIn("no haul runs recorded yet", output)
            self.assertNotIn("Unknown command", output)

    def test_headless_host_reloads_config_via_submit_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text("[controls.market]\nnav_delay_seconds = 0.25\n", encoding="utf-8")
            host._config_path = config_path

            host.submit_input("reload_config")

            output = "\n".join(content.plain for content, _ in host._activity_widget.writes)
        self.assertEqual(host._config.controls.market_nav_delay_seconds, 0.25)
        self.assertIn("Config reloaded from", output)
        self.assertNotIn("Unknown command", output)

    def test_headless_host_emits_announcement_events_without_local_speech(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context_with_tts(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            sink = _EventSinkRecorder()
            host._protocol_event_sink = sink

            host._announce_tts(AnnouncementId.ARRIVAL, system_name="Sol")

        self.assertEqual([event.announcement_id for event in sink.announcements], ["arrival"])
        self.assertIsNone(host._tts._speaker)

    def test_headless_host_speaks_announcements_on_its_own_backend(self) -> None:
        class _RecordingBackend:
            def __init__(self) -> None:
                self.spoken: list[str] = []
                self.done = threading.Event()

            def speak(self, text: str) -> None:
                self.spoken.append(text)
                self.done.set()

        backend = _RecordingBackend()
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context_with_tts(Path(temp_dir)), speech_backend=backend, version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            sink = _EventSinkRecorder()
            host._protocol_event_sink = sink

            host._announce_tts(AnnouncementId.ARRIVAL, system_name="Sol")
            self.assertTrue(backend.done.wait(timeout=1.0))

        self.assertEqual(backend.spoken, ["Arrived in Sol"])
        self.assertEqual([event.message_text for event in sink.announcements], ["Arrived in Sol"])

    def test_headless_host_start_bootstraps_commander_before_startup_greeting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = Path(temp_dir)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"LoadGame","Commander":"VRYAE"}\n',
                encoding="utf-8",
            )
            host = HeadlessControlRoomHost(_make_context_with_tts(journal_dir), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            host._start_watcher_loop = lambda: None

            host.start()

        self.assertEqual(host._protocol_announcements[0].message_text, "Hello VRYAE")

    def test_headless_host_publishes_data_refresh_after_remote_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            sink = _EventSinkRecorder()
            host._protocol_event_sink = sink

            host.handle_remote_input("market filter gold")

        self.assertEqual(sink.data_refresh_count, 1)
        self.assertEqual(host._saved_state.history[-1].raw, "market filter gold")

    def test_headless_host_remote_ctrl_c_cancels_prompt_flow_and_publishes_data_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            sink = _EventSinkRecorder()
            host._protocol_event_sink = sink
            host._start_dest_prompt("Achenar")

            host.cancel_active_routine()

        self.assertEqual(host._dest_prompt_destination, "")
        self.assertIsNone(host._dest_prompt_settle_default)
        self.assertEqual(sink.data_refresh_count, 1)

    def test_http_endpoints_and_websocket_observer_stream(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            health = client.get("/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["status"], "ok")
            self.assertTrue(health.json()["authentication_required"])
            self.assertEqual(health.json()["server_commit"], "b2a65e4+dirty")

            capabilities = client.get(
                "/capabilities",
                headers={"Authorization": "Bearer secret-token"},
            )
            self.assertEqual(capabilities.status_code, 200)
            self.assertEqual(
                capabilities.json()["supported_client_roles"],
                ["active_operator", "observer"],
            )
            self.assertEqual(
                capabilities.json()["supported_message_types"],
                SUPPORTED_MESSAGE_TYPES,
            )
            self.assertEqual(
                capabilities.json()["supported_command_message_types"],
                SUPPORTED_COMMAND_MESSAGE_TYPES,
            )
            self.assertEqual(
                capabilities.json()["supported_event_message_types"],
                SUPPORTED_EVENT_MESSAGE_TYPES,
            )
            self.assertEqual(
                capabilities.json()["supported_response_message_types"],
                SUPPORTED_RESPONSE_MESSAGE_TYPES,
            )
            self.assertEqual(
                capabilities.json()["message_schema_url"],
                MESSAGE_SCHEMA_URL_PATH,
            )
            self.assertEqual(
                capabilities.json()["browser_probe_url"],
                BROWSER_PROBE_URL_PATH,
            )
            self.assertEqual(
                capabilities.json()["authentication_query_parameter_name"],
                "access_token",
            )

            hydrate = client.get(
                "/hydrate",
                headers={"Authorization": "Bearer secret-token"},
            )
            self.assertEqual(hydrate.status_code, 200)
            self.assertEqual(hydrate.json()["message_type"], "control_room.hydrate")
            self.assertEqual(hydrate.json()["payload"]["ship"]["system"], "Sol")
            self.assertNotIn("prompt_state", hydrate.json()["payload"])

            with client.websocket_connect(
                "/session?client_name=bridge-ipad&access_token=secret-token"
            ) as websocket:
                ready = websocket.receive_json()
                self.assertEqual(ready["message_type"], "event.connection_ready")
                self.assertEqual(ready["payload"]["client_role"], "active_operator")

                hydrate_message = websocket.receive_json()
                self.assertEqual(hydrate_message["message_type"], "control_room.hydrate")
                self.assertEqual(hydrate_message["payload"]["ship"]["system"], "Sol")

                broker.publish_announcement(
                    AnnouncementEvent(
                        announcement_id="startup_greeting",
                        message_text="Hello commander.",
                        message_values={},
                    )
                )
                announcement = websocket.receive_json()
                self.assertEqual(announcement["message_type"], "event.announcement_emitted")
                self.assertEqual(announcement["payload"]["announcement_id"], "startup_greeting")

    def test_http_endpoints_include_cors_headers_for_browser_clients(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            capabilities = client.get(
                "/capabilities",
                headers={
                    "Authorization": "Bearer secret-token",
                    "Origin": "https://bridge.local",
                },
            )
            self.assertEqual(capabilities.status_code, 200)
            self.assertEqual(
                capabilities.headers.get("access-control-allow-origin"),
                "*",
            )

            preflight = client.options(
                "/capabilities",
                headers={
                    "Origin": "https://bridge.local",
                    "Access-Control-Request-Method": "GET",
                },
            )
            self.assertEqual(preflight.status_code, 200)
            self.assertEqual(preflight.headers.get("access-control-allow-origin"), "*")

    def test_message_schema_endpoint_is_public_and_matches_loaded_schema(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            response = client.get(
                MESSAGE_SCHEMA_URL_PATH,
                headers={"Origin": "https://bridge.local"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get("access-control-allow-origin"), "*")
            self.assertEqual(response.json(), CONTROL_ROOM_MESSAGE_SCHEMA)

    def test_haul_stats_api_auth_default_window_and_invalid_window(self) -> None:
        from datetime import datetime
        app = build_observer_server_app(data_provider=_base_data_read_model, command_handler=None,
                                        broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"))
        with TestClient(app) as client:
            self.assertEqual(client.get("/api/haul-stats").status_code, 401)
            response = client.get("/api/haul-stats", headers={"Authorization": "Bearer secret-token"})
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(set(payload), {"window", "label", "since", "until", "node", "ship", "nodes", "ships",
                                            "runs", "journal", "journal_node"})
            self.assertEqual((payload["node"], payload["ship"], payload["nodes"], payload["journal_node"]),
                             ("all", "all", [], None))
            self.assertEqual(payload["window"], "today")
            self.assertEqual(payload["label"], "today")
            self.assertEqual(datetime.fromisoformat(payload["since"]).hour, 0)
            self.assertIsNone(payload["journal"])
            self.assertEqual(payload["runs"]["all_in"]["count"], 0)
            bad = client.get("/api/haul-stats?window=invalid&access_token=secret-token")
            self.assertEqual(bad.status_code, 400)
            self.assertIn("Usage: stats", bad.json()["detail"])
            bad_ship = client.get("/api/haul-stats?ship=Cutter&access_token=secret-token")
            self.assertEqual(bad_ship.status_code, 400)

    def test_command_api_runs_command_text_and_rejects_bad_requests(self) -> None:
        recorder = _CommandHandlerRecorder()
        app = build_observer_server_app(data_provider=_base_data_read_model, command_handler=recorder,
                                        broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"))
        auth = {"Authorization": "Bearer secret-token"}
        with TestClient(app) as client:
            self.assertEqual(client.post("/api/command", json={"raw_input": "undock"}).status_code, 401)
            response = client.post("/api/command", json={"raw_input": " undock ", "skip_delay": True}, headers=auth)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"accepted": True, "raw_input": "undock",
                                               "routine_active": False, "active_routine_name": None})
            client.post("/api/command?access_token=secret-token", json={"raw_input": "dock"})
            for bad in ({"content": "not json"}, {"json": {}}, {"json": {"raw_input": "  "}},
                        {"json": ["undock"]}, {"json": {"raw_input": "dock", "skip_delay": "yes"}}):
                self.assertEqual(client.post("/api/command", headers=auth, **bad).status_code, 400, bad)
            self.assertEqual(client.get("/api/command", headers=auth).status_code, 405)
        self.assertEqual(recorder.submitted_inputs, [("undock", True), ("dock", None)])

    def test_command_api_reports_unavailable_handler(self) -> None:
        app = build_observer_server_app(data_provider=_base_data_read_model, command_handler=None,
                                        broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"))
        with TestClient(app) as client:
            response = client.post("/api/command?access_token=secret-token", json={"raw_input": "undock"})
        self.assertEqual(response.status_code, 503)

    def test_command_api_refuses_routine_command_while_busy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            host._controls = object()
            host._routine_active = True
            host._active_routine_name = "haul"
            app = build_observer_server_app(data_provider=host.dependencies.data_source.current, command_handler=host,
                                            broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"))
            with TestClient(app) as client:
                refused = client.post("/api/command?access_token=secret-token", json={"raw_input": "undock"})
                allowed = client.post("/api/command?access_token=secret-token", json={"raw_input": "stats all"})
        self.assertEqual(refused.status_code, 409)
        self.assertFalse(refused.json()["accepted"])
        self.assertTrue(refused.json()["routine_active"])
        self.assertEqual(refused.json()["active_routine_name"], "haul")
        self.assertIn("haul is already running", refused.json()["detail"])
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.json()["accepted"])

    def test_stop_api_cancels_running_routine_and_refuses_when_idle(self) -> None:
        recorder = _CommandHandlerRecorder()
        busy = lambda: replace(_base_data_read_model(), routine=replace(_base_data_read_model().routine,
                                                                       routine_active=True, active_routine_name="haul"))
        tracking = lambda: replace(_base_data_read_model(), haul_session=replace(_base_data_read_model().haul_session,
                                                                                 active=True, tracking=True))
        for provider, body, status, modes in ((busy, None, 200, ["now"]), (busy, {"mode": "after_run"}, 200, ["after_run"]),
                                              (tracking, None, 200, ["now"]),
                                              (busy, {"mode": "toggle"}, 400, []), (_base_data_read_model, None, 409, [])):
            recorder.cancel_modes.clear()
            app = build_observer_server_app(data_provider=provider, command_handler=recorder,
                                            broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"))
            with TestClient(app) as client:
                self.assertEqual(client.post("/api/stop").status_code, 401)
                response = client.post("/api/stop?access_token=secret-token", json=body)
            self.assertEqual(response.status_code, status, body)
            self.assertEqual(recorder.cancel_modes, modes)
        self.assertFalse(response.json()["accepted"])
        self.assertEqual(response.json()["detail"], "No routine is running.")

    def test_headless_host_submit_input_reports_busy_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            host._controls = object()
            host._routine_active = True
            host._haul_stats.active = True
            results = [host.submit_input(command) for command in ("jump", "reload_config", "reload_keymap", "stop", "stats all")]
        self.assertEqual(results, [False, False, False, False, True])

    def test_eddn_status_api_reports_disabled_or_service_status(self) -> None:
        for status, expected in ((None, {"enabled": False}),
                                 (lambda: {"listener": {"messages": 3}}, {"enabled": True, "listener": {"messages": 3}})):
            app = build_observer_server_app(data_provider=_base_data_read_model, command_handler=None,
                                            broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"),
                                            eddn_status=status)
            with TestClient(app) as client:
                self.assertEqual(client.get("/api/eddn-status").status_code, 401)
                response = client.get("/api/eddn-status?access_token=secret-token")
                self.assertEqual(response.json(), expected)

    def test_haul_stats_api_reads_configured_files_and_optional_journal(self) -> None:
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "runs.jsonl"
            path.write_text(json.dumps(dict(schema=1, kind="two_way", status="completed",
                started_at="2020-01-01T00:00:00Z", ended_at="2020-01-01T01:00:00Z",
                route={"station_1": "Alpha", "station_2": "Beta"}, cost=10, revenue=50,
                expected_profit=30, duration_s=3600, legs=[])) + "\n")
            (root / "Journal.2020-01-01T000000.01.log").write_text(json.dumps(dict(
                event="MarketSell", timestamp="2020-01-01T01:00:00Z", Type="gold", Count=1,
                TotalSale=50, AvgPricePaid=10)) + "\n")
            app = build_observer_server_app(data_provider=_base_data_read_model, command_handler=None,
                broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"),
                haul_runs_file=path, journal_dir=root)
            with TestClient(app) as client:
                response = client.get("/api/haul-stats?window=all&access_token=secret-token")
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertIsNone(payload["since"])
                self.assertEqual(payload["runs"]["completed"]["profit"], 40)
                self.assertEqual(payload["journal"]["sell_margin"], 40)
                self.assertEqual(payload["journal"]["coverage"]["files"], 1)
            unavailable = build_observer_server_app(data_provider=_base_data_read_model, command_handler=None,
                broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"),
                haul_runs_file=path, journal_dir=root / "missing")
            with TestClient(unavailable) as client:
                payload = client.get("/api/haul-stats?window=all&access_token=secret-token").json()
                self.assertEqual(payload["runs"]["completed"]["profit"], 40)
                self.assertIsNone(payload["journal"])


    def test_browser_probe_endpoint_is_public_html(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            response = client.get(
                BROWSER_PROBE_URL_PATH,
                headers={"Origin": "https://bridge.local"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get("access-control-allow-origin"), "*")
            self.assertIn("Control Room Remote Browser Probe", response.text)
            self.assertIn("command.submit_input", response.text)
            self.assertIn("command.cancel_active_routine", response.text)
            self.assertIn("Reconnecting in", response.text)
            self.assertIn("Observer connection restored.", response.text)
            self.assertIn("Observer mode: mutating controls disabled", response.text)
            self.assertIn("Connected Clients", response.text)
            self.assertIn("Recent Activity", response.text)
            self.assertIn("session ready role=", response.text)
            self.assertNotIn("requestSnapshot();", response.text)
            self.assertIn("authentication_supported_transports", response.text)
            self.assertIn("authentication_query_parameter_name", response.text)
            self.assertIn("Browser probe requires query-parameter websocket auth support.", response.text)

    def test_haul_web_endpoint_serves_static_page(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            response = client.get(HAUL_WEB_URL_PATH)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Two-way haul control", response.text)
        self.assertIn("Set destination", response.text)
        self.assertIn("Start route", response.text)
        self.assertIn('id="token-dialog"', response.text)
        self.assertIn('id="history-title"', response.text)
        self.assertIn('data-history-window="week"', response.text)
        self.assertIn('src="/assets/haul-ui.js"', response.text)
        self.assertIn('href="/assets/haul-ui.css"', response.text)
        self.assertNotIn("window.prompt", response.text)
        self.assertIn('"defaultAccessToken": ""', response.text)
        self.assertIn('"authQueryParameterName": "access_token"', response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_root_endpoint_serves_haul_web_entry_point(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            response = client.get(HAUL_WEB_ENTRY_URL_PATH)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Two-way haul control", response.text)
        self.assertIn("window.EDCR_WEB_CONFIG =", response.text)
        self.assertIn('"hostLabel": "testserver"', response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_multi_haul_endpoint_serves_shared_web_shell(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            response = client.get("/multi-haul")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Multi-leg haul", response.text)
        self.assertIn('id="multi-search-form"', response.text)
        self.assertIn('src="/assets/multi-haul.js"', response.text)
        self.assertNotIn('src="/assets/haul-ui.js"', response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_markets_page_lists_recent_markets_and_compares_two(self) -> None:
        from edcr.recent_markets import record_market_json

        def market(market_id: int, station: str, timestamp: str, items: list[dict]) -> dict:
            return {"MarketID": market_id, "StationName": station, "StarSystem": "Sol", "StationType": "Orbis",
                    "timestamp": timestamp, "Items": items}

        def data_provider() -> ControlRoomDataReadModel:
            return replace(_base_data_read_model(), ship=ShipState(system="Sol", cargo_capacity=256))

        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "recent.json"
            record_market_json(store, market(1, "Galileo", "2026-11-10T10:00:00Z", [
                {"Name": "$gold_name;", "Name_Localised": "Gold", "BuyPrice": 9000, "Stock": 100, "Demand": 0},
                {"Name": "$tea_name;", "Name_Localised": "Tea", "SellPrice": 2000, "Demand": 40},
            ]), lambda _: None, limit=10)
            record_market_json(store, market(2, "Abraham Lincoln", "2026-11-10T11:00:00Z", [
                {"Name": "$gold_name;", "Name_Localised": "Gold", "SellPrice": 9600, "Demand": 500},
                {"Name": "$tea_name;", "Name_Localised": "Tea", "BuyPrice": 1500, "Stock": 1000},
            ]), lambda _: None, limit=10)
            app = build_observer_server_app(
                data_provider=data_provider,
                command_handler=None,
                broker=InMemoryObserverSessionBroker(),
                auth=SharedAccessTokenAuth("secret-token"),
                recent_markets_file=store,
            )
            with TestClient(app) as client:
                page = client.get("/markets")
                script = client.get("/assets/markets.js")
                icons = [client.get(path) for path in
                         ("/assets/favicon.png", "/assets/apple-touch-icon.png", "/favicon.ico")]
                self.assertEqual(client.get("/api/recent-markets").status_code, 401)
                listing = client.get("/api/recent-markets?access_token=secret-token").json()
                comparison = client.get("/api/market-compare?x=1&y=2&access_token=secret-token").json()
                smaller = client.get("/api/market-compare?x=1&y=2&capacity=10&access_token=secret-token").json()
                missing = client.get("/api/market-compare?x=1&y=99&access_token=secret-token")
                invalid = client.get("/api/market-compare?x=one&y=2&access_token=secret-token")

        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertIn('src="/assets/markets.js"', page.text)
        for icon in icons:
            self.assertEqual((icon.status_code, icon.headers["content-type"]), (200, "image/png"))
            self.assertTrue(icon.content.startswith(b"\x89PNG"))
        for element_id in ("market-list", "market-table", "show-empty", "deal-x", "deal-y", "deal-capacity",
                           "deal-laden"):
            self.assertIn(f'id="{element_id}"', page.text)
        self.assertEqual(script.status_code, 200)
        self.assertEqual(script.headers["cache-control"], "no-store")
        for hook in ('"/api/recent-markets"', '"/api/market-compare"', "ageLabel(market.timestamp)", "/haul#route=",
                     "const DEAL_CHOICES = 3;", 'name="deal-${leg}"', "tradeRoute(marketX, marketY, out, back, perHour)",
                     '"Profit per ton"', '"Profit per trip", credits(perTrip), "Full-hold round trip"',
                     '"Profit per hour"', ">Measured per hour<", 'id="deal-window"', "window: measuredWindow",
                     "perTrip * 3600 / trip.trip_s",
                     'laden_jump_range_ly: document.getElementById("deal-laden").value.trim()'):
            self.assertIn(hook, script.text)
        self.assertEqual(listing["cargo_capacity"], 256)
        self.assertEqual([m["station"] for m in listing["markets"]], ["Abraham Lincoln", "Galileo"])
        self.assertEqual(listing["markets"][1]["station_type"], "Orbis")
        self.assertEqual(listing["markets"][1]["items"][0]["name"], "Gold")
        self.assertEqual(listing["markets"][1]["items"][0]["buy_price"], 9000)
        self.assertEqual(comparison["cargo_capacity"], 256)
        self.assertEqual(comparison["outbound"][0]["hold_profit"], 600 * 100)
        self.assertEqual(comparison["inbound"][0]["hold_profit"], 500 * 256)
        self.assertEqual(comparison["round_trip"]["profit_per_ton"], 1100)
        self.assertEqual(smaller["round_trip"]["hold_profit"], 1100 * 10)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(invalid.status_code, 400)
        # Without a market database (a peer) no station facts are known here; the hub supplies them.
        self.assertEqual(comparison["trip"]["missing"],
                         ["Galileo distance from star", "Galileo station type",
                          "Abraham Lincoln distance from star", "Abraham Lincoln station type"])
        self.assertEqual(comparison["trip"]["hint"], "Station facts come from the hub.")
        self.assertIsNone(comparison["trip"]["trip_s"])
        self.assertEqual(comparison["trip"]["jumps"], 0)
        self.assertIn("trip.hint", script.text)
        self.assertIsNone(comparison["measured"])

    def test_market_compare_estimates_trip_time_from_the_store_and_measures_haul_runs(self) -> None:
        import json

        from edcr.eddn.routes import TimeModel
        from edcr.recent_markets import record_market_json
        from edcr.trade_trip import StationFacts, estimate_trip

        def run(station_1: str, station_2: str, duration_s: float, ship_id: int | None) -> dict:
            row = {"schema": 1, "kind": "two_way", "status": "completed", "started_at": "2026-11-10T09:00:00Z",
                   "ended_at": "2026-11-10T10:00:00Z", "duration_s": duration_s, "cost": 1_000_000,
                   "revenue": 3_000_000, "profit": 2_000_000, "legs": [],
                   "route": {"station_1": station_1, "system_1": None, "station_2": station_2, "system_2": None}}
            if ship_id is not None:
                row["ship"] = {"id": ship_id, "type": "cutter", "laden_jump_range_ly": 21.5}
            return row

        def flying_ship_7():
            return replace(_base_data_read_model(), ship=ShipState(ship_id=7, ship_type="cutter", ship_name="Hauler",
                                                                      laden_jump_range_ly=24.5))

        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "recent.json"
            runs = Path(directory) / "runs.jsonl"
            runs.write_text("".join(json.dumps(row) + "\n" for row in (
                run("Galileo", "Alpha Port", 1500.0, 7), run("alpha port", "galileo", 900.0, None),
                run("Galileo", "Alpha Port", 60.0, 8))), encoding="utf-8")
            for market_id, station, system in ((1, "Galileo", "Sol"), (2, "Alpha Port", "Alpha")):
                record_market_json(store, {"MarketID": market_id, "StationName": station, "StarSystem": system,
                                           "StationType": "Coriolis", "timestamp": "2026-11-10T10:00:00Z",
                                           "Items": []}, lambda _: None, limit=10)
            database = _facts_db(directory, store, [
                {"event": "Location", "timestamp": "2026-11-10T10:30:00Z", "StarSystem": "Sol", "SystemAddress": 10,
                 "StarPos": [0, 0, 0], "Docked": True, "MarketID": 1, "StationName": "Galileo",
                 "StationType": "Coriolis", "DistFromStarLS": 500.0},
                {"event": "FSDJump", "timestamp": "2026-11-10T10:40:00Z", "StarSystem": "Alpha", "SystemAddress": 20,
                 "StarPos": [30.0, 0, 0]},
                {"event": "Docked", "timestamp": "2026-11-10T10:45:00Z", "StarSystem": "Alpha", "SystemAddress": 20,
                 "MarketID": 2, "StationName": "Alpha Port", "StationType": "CraterOutpost", "DistFromStarLS": 80.0},
            ])
            app = build_observer_server_app(
                data_provider=flying_ship_7, command_handler=None, broker=InMemoryObserverSessionBroker(),
                auth=SharedAccessTokenAuth("secret-token"), recent_markets_file=store, haul_runs_file=runs,
                market_database_file=database,
            )
            with TestClient(app) as client:
                url = "/api/market-compare?x=1&y=2&capacity=10&access_token=secret-token"
                # The runs are fixed in time, so `all` keeps them whatever today is.
                compared = client.get(f"{url}&laden_jump_range_ly=20&window=all").json()
                bad = client.get(f"{url}&laden_jump_range_ly=-3")
                bad_window = client.get(f"{url}&window=week")

        trip = compared["trip"]
        expected = estimate_trip(
            StationFacts("Galileo", "Sol", (0.0, 0.0, 0.0), "j", 500.0, "j", "Coriolis", "j"),
            StationFacts("Alpha Port", "Alpha", (30.0, 0.0, 0.0), "j", 80.0, "j", "CraterOutpost", "j"),
            laden_jump_range_ly=20.0, time_model=TimeModel(),
        )
        self.assertEqual((trip["jumps"], trip["distance_ly"], trip["missing"]), (2, 30.0, []))
        self.assertEqual(trip["trip_s"], expected.trip_s)
        self.assertEqual(trip["laden_jump_range_ly"], 20.0)
        self.assertEqual(trip["stations"]["y"]["station_type"], "CraterOutpost")
        self.assertEqual((trip["stations"]["x"]["dist_ls_source"], trip["hint"]), ("store", None))
        # Ship 8's run is left out; the run without ship data counts as ship unknown.
        self.assertEqual(compared["measured"],
                         {"runs": 2, "profit": 4_000_000, "duration_s": 2400.0, "profit_per_hour": 6_000_000,
                          "loop_s": 1200, "unknown_ship_runs": 1, "laden_jump_range_ly": 21.5})
        self.assertEqual(compared["measured_window"], "all")
        # The page's 20 Ly drives the estimate; the ship's own 24.5 Ly is what measured runs compare against.
        self.assertEqual(compared["measured_ship"],
                         {"id": 7, "type": "cutter", "name": "Hauler", "laden_jump_range_ly": 24.5})
        self.assertEqual((bad.status_code, bad_window.status_code), (400, 400))

    def test_market_compare_asks_ardent_only_for_what_the_store_lacks(self) -> None:
        from edcr.recent_markets import record_market_json
        from edcr.trade_trip import PartialFacts

        asked: list[str] = []

        def ardent(market_id: int, station: str, system: str) -> PartialFacts:
            asked.append(station)
            if system == "Down":
                return PartialFacts()
            return PartialFacts(coords=(40.0, 0.0, 0.0), dist_ls=100.0, station_type="Orbis")

        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "recent.json"
            for market_id, station, system in ((1, "Galileo", "Sol"), (2, "Far Port", "Far"), (3, "Dark", "Down")):
                record_market_json(store, {"MarketID": market_id, "StationName": station, "StarSystem": system,
                                           "StationType": "Coriolis", "timestamp": f"2026-11-10T10:0{market_id}:00Z",
                                           "Items": []}, lambda _: None, limit=10)
            database = _facts_db(directory, store, [
                {"event": "Location", "timestamp": "2026-11-10T10:30:00Z", "StarSystem": "Sol", "SystemAddress": 10,
                 "StarPos": [0, 0, 0], "Docked": True, "MarketID": 1, "StationName": "Galileo",
                 "StationType": "Coriolis", "DistFromStarLS": 500.0},
                # Coordinates only: Dark's Market.json type then lands in the store too.
                {"event": "FSDJump", "timestamp": "2026-11-10T09:00:00Z", "StarSystem": "Down", "SystemAddress": 30,
                 "StarPos": [50.0, 0, 0]},
            ])
            app = build_observer_server_app(
                data_provider=_base_data_read_model, command_handler=None, broker=InMemoryObserverSessionBroker(),
                auth=SharedAccessTokenAuth("secret-token"), recent_markets_file=store, ardent_lookup=ardent,
                market_database_file=database,
            )
            with TestClient(app) as client:
                url = "/api/market-compare?capacity=10&laden_jump_range_ly=20&access_token=secret-token"
                filled = client.get(f"{url}&x=1&y=2").json()["trip"]
                down = client.get(f"{url}&x=1&y=3").json()["trip"]

        self.assertEqual(asked, ["Far Port", "Dark"])
        self.assertEqual((filled["jumps"], filled["missing"]), (2, []))
        self.assertIsNotNone(filled["trip_s"])
        self.assertEqual(filled["stations"]["x"]["dist_ls_source"], "store")
        self.assertEqual((filled["stations"]["y"]["coords_source"], filled["stations"]["y"]["dist_ls_source"]),
                         ("ardent", "ardent"))
        # The store knows Down's coordinates and Dark's Market.json type; a failed Ardent lookup leaves the distance.
        self.assertEqual((down["stations"]["y"]["coords_source"], down["stations"]["y"]["station_type_source"]),
                         ("store", "store"))
        self.assertEqual(down["missing"], ["Dark distance from star"])
        self.assertIsNone(down["trip_s"])

    def test_every_page_renders_the_one_shared_nav(self) -> None:
        web_dir = Path(server_app.__file__).resolve().parents[3] / "web"
        nav = (web_dir / "nav.js").read_text(encoding="utf-8")
        for href in ("/haul", "/multi-haul", "/markets", "/routes", "/controls", "/travel", "/config"):
            self.assertIn(f'href: "{href}"', nav)
        self.assertIn('anchor.setAttribute("aria-current", "page")', nav)
        for page in ("haul-v1.html", "multi-haul.html", "controls.html", "markets.html", "routes.html", "travel.html",
                     "config.html"):
            html = (web_dir / page).read_text(encoding="utf-8")
            self.assertIn('<nav class="site-nav" id="site-nav" aria-label="Pages"></nav>\n'
                          '      <script src="/assets/nav.js"></script>', html, page)
            # No page keeps a hand-copied link list that could drift from nav.js again.
            self.assertNotIn('class="nav-item', html, page)
            self.assertIn('<link rel="icon" type="image/png" href="/assets/favicon.png">', html, page)
            # nav.js runs before the page sets EDCR_WEB_CONFIG, so it must not read the config (and its token) yet.
            self.assertLess(html.index("/assets/nav.js"), html.index("window.EDCR_WEB_CONFIG"), page)
        self.assertNotIn("const WEB_CONFIG = window.EDCR_WEB_CONFIG", nav)
        self.assertIn('document.addEventListener("DOMContentLoaded"', nav)

    def test_travel_page_hosts_the_route_panels_and_its_scripts_are_served(self) -> None:
        app = build_observer_server_app(data_provider=_base_data_read_model, command_handler=None,
                                        broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"))
        with TestClient(app) as client:
            page = client.get("/travel")
            assets = {name: client.get(f"/assets/{name}")
                      for name in ("travel.js", "nav.js", "active-route.js", "route-compare.js")}
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertIn('"authQueryParameterName": "access_token"', page.text)
        for name, response in assets.items():
            self.assertEqual(response.status_code, 200, name)
            self.assertIn(f'src="/assets/{name}"', page.text)
        # Active route sits above Route Comparison.
        self.assertLess(page.text.index('id="active-spansh-panel"'), page.text.index('id="route-compare-panel"'))
        for element_id in ("rc-all-in-one", "rc-switch", "active-spansh-waypoints", "access-token", "activity-list"):
            self.assertIn(f'id="{element_id}"', page.text)
        # travel.js loads first so the panels find the websocket bridge the haul page used to provide.
        self.assertLess(page.text.index('src="/assets/travel.js"'), page.text.index('src="/assets/route-compare.js"'))
        for hook in ("window.EDCR_HAUL.sendCommand = sendCommand;", "window.EDCR_HAUL.galmapSettleTime",
                     'new CustomEvent("edcr:hydrate"', 'new CustomEvent("edcr:ship-state"'):
            self.assertIn(hook, assets["travel.js"].text)

    def test_routes_page_and_script_are_served(self) -> None:
        app = build_observer_server_app(data_provider=_base_data_read_model, command_handler=None,
                                        broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"))
        with TestClient(app) as client:
            page = client.get("/routes")
            script = client.get("/assets/routes.js")
        self.assertEqual(page.status_code, 200)
        self.assertIn('src="/assets/routes.js"', page.text)
        for element_id in ("route-table", "route-system", "route-laden", "routes-search"):
            self.assertIn(f'id="{element_id}"', page.text)
        for hook in ('"/api/eddn-routes"', '"/api/eddn-status"', "params.max_route_ly"):
            self.assertIn(hook, script.text)
        # On phones haul-ui.css shows each row as a card labelled from data-label.
        for label in ("Stations", "Out", "Back", "Per hour", "Haul"):
            self.assertIn(f'data-label="{label}"', script.text)
        self.assertIn("@media (max-width: 760px)", page.text)
        # Open in haul hands the route to /haul the way /markets does.
        self.assertIn("/haul#route=${encodeURIComponent(JSON.stringify(tradeRoute))}", script.text)
        self.assertIn(">Open in haul</a>", script.text)

    def test_routes_page_starts_the_surface_checkbox_from_the_haul_search_choice(self) -> None:
        def data_provider() -> ControlRoomDataReadModel:
            data = _base_data_read_model()
            return replace(data, server_status=replace(
                data.server_status, web_form_defaults={"allowPlanetary": "true", "surfaceStations": "yes_with_odyssey"}))

        app = build_observer_server_app(data_provider=data_provider, command_handler=None,
                                        broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth("secret-token"))
        with TestClient(app) as client:
            page = client.get("/routes")
            script = client.get("/assets/routes.js")
        self.assertIn('"allowPlanetary": "true"', page.text)
        self.assertIn('getElementById("route-surface").checked = (WEB_CONFIG.webDefaults || {}).allowPlanetary === "true"',
                      script.text)
        # Blank min supply / station distance fall back to haul_search; the placeholders show those values.
        self.assertIn('["route-min-supply", "minSupply", "haul search"]', script.text)
        self.assertIn('["route-age", "maxPriceAgeHours", "haul search"]', script.text)
        self.assertIn('id="route-min-supply-on"', page.text)
        self.assertIn('params[key] = "any"', script.text)
        self.assertIn('placeholder = `${value} (${source})`', script.text)

    def test_controls_endpoint_serves_button_board(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            response = client.get("/controls")
            js_response = client.get("/assets/controls.js")
            dock_response = client.get("/assets/activity-dock.js")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        for command in ("undock", "dock", "jump", "escape", "boost", "pause", "resume", "reload_config"):
            self.assertIn(f'data-command="{command}"', response.text)
        self.assertIn('src="/assets/controls.js"', response.text)
        self.assertNotIn('src="/assets/haul-ui.js"', response.text)
        self.assertEqual(js_response.status_code, 200)
        self.assertIn("command.submit_input", js_response.text)
        self.assertIn("command.cancel_active_routine", js_response.text)
        self.assertEqual(dock_response.status_code, 200)
        self.assertIn("edcr.activityDock.expanded", dock_response.text)
        self.assertIn('"serverCommit": "b2a65e4+dirty"', response.text)
        self.assertIn('id="status-version"', response.text)
        for element_id in ("nav-system", "nav-station", "nav-manual-landing", "nav-plot", "nav-travel",
                           "nav-plot-home", "nav-set-home"):
            self.assertIn(f'id="{element_id}"', response.text)
        for hook in ('sendCommand("command.dispatch_destination"', 'sendCommand("command.dispatch_travel"',
                     'manual_landing: Boolean(station) && document.getElementById("nav-manual-landing").checked',
                     "plotDestination(homeSystem)",
                     'homeSystem = String(payload.home_system || "").trim()', "submitInput(`home set ",
                     "serverStatus.web_form_defaults"):
            self.assertIn(hook, js_response.text)
        self.assertNotIn('src="/assets/speech.js"', response.text)
        for element_id in ("voice-preset", "voice-say-text", "voice-say", "voice-model", "voice-test", "voice-save",
                           "voice-length_scale", "voice-noise_scale", "voice-noise_w_scale",
                           "voice-sentence_silence", "voice-volume"):
            self.assertIn(f'id="{element_id}"', response.text)
        for hook in ("submitInput(`say ${line}`", "submitInput(`voice set ${key}=${value}`", 'submitInput("voice save"',
                     "applyVoice(payload.voice || {})", '.replaceAll("{system_name}", currentShip.system'):
            self.assertIn(hook, js_response.text)

    def test_haul_web_endpoint_can_inject_implicit_serve_token(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("edcr"),
            web_default_access_token="edcr",
        )

        with TestClient(app) as client:
            response = client.get(HAUL_WEB_URL_PATH)

        self.assertEqual(response.status_code, 200)
        self.assertIn('"defaultAccessToken": "edcr"', response.text)

    def test_haul_web_endpoint_injects_runtime_labels_and_form_defaults(self) -> None:
        def data_provider() -> ControlRoomDataReadModel:
            data = _base_data_read_model()
            return replace(
                data,
                server_status=replace(
                    data.server_status,
                    input_target_summary="pid 4242 (EliteDangerous64.exe)",
                    web_form_defaults={
                        "cargoCapacity": "512",
                        "maxRouteDistanceLy": "750",
                        "galaxyMapSettle": "3.5",
                        "dockTimeout": "900",
                    },
                ),
            )

        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=data_provider,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("edcr"),
        )

        with TestClient(app) as client:
            response = client.get(HAUL_WEB_URL_PATH)

        self.assertEqual(response.status_code, 200)
        self.assertIn('"inputTargetSummary": "pid 4242 (EliteDangerous64.exe)"', response.text)
        self.assertIn('"cargoCapacity": "512"', response.text)
        self.assertIn('"maxRouteDistanceLy": "750"', response.text)
        self.assertIn('"galaxyMapSettle": "3.5"', response.text)
        self.assertIn('"dockTimeout": "900"', response.text)

    def test_haul_web_assets_are_served_without_cache(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("edcr"),
        )

        with TestClient(app) as client:
            css_response = client.get("/assets/haul-ui.css")
            js_response = client.get("/assets/haul-ui.js")
            multi_js_response = client.get("/assets/multi-haul.js")
            speech_js_response = client.get("/assets/speech.js")
            missing_response = client.get("/assets/unknown.js")

        self.assertEqual(css_response.status_code, 200)
        self.assertEqual(css_response.headers["cache-control"], "no-store")
        self.assertIn(".shell", css_response.text)
        self.assertEqual(js_response.status_code, 200)
        self.assertEqual(js_response.headers["cache-control"], "no-store")
        self.assertIn("function connectWebsocket", js_response.text)
        self.assertIn("showAccessTokenPrompt", js_response.text)
        self.assertIn("handleAccessTokenRejected", js_response.text)
        self.assertIn("Access token rejected", js_response.text)
        self.assertEqual(multi_js_response.status_code, 200)
        self.assertEqual(multi_js_response.headers["cache-control"], "no-store")
        self.assertIn("command.dispatch_multi_leg_haul", multi_js_response.text)
        self.assertEqual(speech_js_response.status_code, 200)
        self.assertIn("speechSynthesis", speech_js_response.text)
        self.assertEqual(missing_response.status_code, 404)

    def test_haul_web_renderer_rereads_html_file_without_server_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "haul-v1.html"
            html_path.write_text("first window.EDCR_WEB_CONFIG = {};", encoding="utf-8")

            with patch.object(server_app, "_HAUL_WEB_PATH", html_path):
                first_html = _render_haul_web_html(web_default_access_token="edcr")
                html_path.write_text("second window.EDCR_WEB_CONFIG = {};", encoding="utf-8")
                second_html = _render_haul_web_html(web_default_access_token="edcr")

        self.assertIn('first window.EDCR_WEB_CONFIG = {"defaultAccessToken": "edcr"};', first_html)
        self.assertIn('second window.EDCR_WEB_CONFIG = {"defaultAccessToken": "edcr"};', second_html)

    def test_haul_rest_action_endpoints_are_not_registered(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            search_response = client.post("/api/haul/search", json={"origin": "Sol"})
            start_response = client.post("/api/haul/start", json={"params": {}})

        self.assertEqual(search_response.status_code, 404)
        self.assertEqual(start_response.status_code, 404)

    def test_active_operator_search_haul_routes_returns_serialized_routes(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")
        result = TradeRouteSearchResult(
            system_name="Sol",
            query_url="https://inara.cz/elite/market-traderoutes/?ps1=Sol",
            searched_at="2026-07-04T08:00:00Z",
            routes=(
                TradeRoute(
                    index=1,
                    from_station="Galileo",
                    from_system="Sol",
                    to_station="Irkutsk",
                    to_system="Alioth",
                    source_buy_commodity="Agronomic Treatment",
                    target_buy_commodity="Gold",
                    from_station_distance="510 ls",
                    to_station_distance="1,200 ls",
                    route_distance="221.34 ly",
                    profit_per_trip="43.1m",
                    profit_per_hour="88.3m",
                ),
                TradeRoute(
                    index=2,
                    from_station="Galileo",
                    from_system="Sol",
                    to_station="Jameson Memorial",
                    to_system="Shinrarta Dezhra",
                    source_buy_commodity="Silver",
                ),
            ),
        )

        with (
            patch("edcr.control_room.server.app.search_trade_routes", return_value=result) as search,
            patch("edcr.control_room.server.app.save_haul_search_config") as save_defaults,
        ):
            response = _handle_session_message(
                {
                    "message_type": "command.search_haul_routes",
                    "message_id": "message-search",
                    "payload": {
                        "origin": "Sol",
                        "destination": "Alioth",
                        "cargo_capacity": "784",
                        "max_route_distance_ly": "500 ly",
                        "max_station_distance_ls": "Any",
                        "metric": "Profit / trip",
                    },
                },
                session_id=observer.session_id,
                client_role="active_operator",
                command_handler=None,
                broker=broker,
                data_provider=_base_data_read_model,
            )

        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-search")
        result_payload = response["payload"]["result"]
        self.assertEqual(result_payload["route_count"], 1)
        self.assertEqual(result_payload["unfiltered_route_count"], 2)
        self.assertTrue(result_payload["station_carrier_only"])
        self.assertEqual(result_payload["routes"][0]["source_buy_commodity"], "Agronomic Treatment")
        search.assert_called_once()
        self.assertEqual(search.call_args.args, ("Sol",))
        self.assertEqual(
            search.call_args.kwargs["query_params"],
            {
                "use_surface_stations": "no",
                "cargo_capacity": "784",
                "max_route_distance_ly": "500",
                "max_station_distance_ls": "any",
                "order_by": "best_profit",
            },
        )
        save_defaults.assert_called_once()
        self.assertEqual(save_defaults.call_args.args[0]["max_route_distance_ly"], "500")
        self.assertEqual(save_defaults.call_args.args[0]["max_station_distance_ls"], "any")
        self.assertEqual(save_defaults.call_args.kwargs["exclude"], ("cargo_capacity",))

    def test_search_haul_routes_passes_the_surface_station_choice_to_inara(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")
        result = TradeRouteSearchResult(system_name="Sol", query_url="", searched_at="", routes=())

        def search(surface: str) -> dict[str, object]:
            return _handle_session_message(
                {
                    "message_type": "command.search_haul_routes",
                    "message_id": "message-search",
                    "payload": {"origin": "Sol", "use_surface_stations": surface},
                },
                session_id=observer.session_id,
                client_role="active_operator",
                command_handler=None,
                broker=broker,
                data_provider=_base_data_read_model,
            )

        with (
            patch("edcr.control_room.server.app.search_trade_routes", return_value=result) as inara,
            patch("edcr.control_room.server.app.save_haul_search_config"),
        ):
            response = search("yes_exclude_odyssey")
            invalid = search("sometimes")

        self.assertEqual(inara.call_args.kwargs["query_params"]["use_surface_stations"], "yes_exclude_odyssey")
        self.assertFalse(response["payload"]["result"]["station_carrier_only"])
        self.assertEqual(response["payload"]["result"]["use_surface_stations"], "yes_exclude_odyssey")
        self.assertEqual(invalid["message_type"], "response.error")
        self.assertEqual(inara.call_count, 1)

    def test_connected_observer_search_haul_routes_is_allowed(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")

        with (
            patch("edcr.control_room.server.app.search_trade_routes") as search,
            patch("edcr.control_room.server.app.save_haul_search_config"),
        ):
            search.return_value = TradeRouteSearchResult(
                system_name="Sol",
                query_url="https://inara.cz/elite/market-traderoutes/?ps1=Sol",
                searched_at="2026-07-04T08:00:00Z",
                routes=(),
            )
            response = _handle_session_message(
                {
                    "message_type": "command.search_haul_routes",
                    "message_id": "message-search-observer",
                    "payload": {"origin": "Sol"},
                },
                session_id=observer.session_id,
                client_role="observer",
                command_handler=None,
                broker=broker,
                data_provider=_base_data_read_model,
            )

        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-search-observer")
        self.assertEqual(response["payload"]["result"]["route_count"], 0)

    def test_select_trade_route_stores_route_for_future_hydrate(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("web-haul")
        command_handler = _CommandHandlerRecorder()
        route_payload = {
            "index": 4,
            "from_station": "Galileo",
            "from_system": "Sol",
            "to_station": "Irkutsk",
            "to_system": "Alioth",
            "source_buy_commodity": "Agronomic Treatment",
            "target_buy_commodity": "Gold",
            "profit_per_hour": "88.3m",
            "from_supply": "52,113",
            "from_demand": "1,204",
            "to_supply": "8,870",
            "to_demand": "96,431",
            "from_buy_price": "3,420 Cr",
            "to_sell_price": "40,684 Cr",
            "to_buy_price": "2,022 Cr",
            "from_sell_price": "2,661 Cr",
            "from_manual_landing": True,
        }

        response = _handle_session_message(
            {
                "message_type": "command.select_trade_route",
                "message_id": "message-select-route",
                "payload": {"route": route_payload},
            },
            session_id=observer.session_id,
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
            data_provider=_base_data_read_model,
        )

        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-select-route")
        self.assertEqual(broker.server_state.selected_trade_route().to_system, "Alioth")
        self.assertEqual(command_handler.persisted_selected_trade_route.to_system, "Alioth")
        self.assertIsNone(command_handler.persisted_running_trade_route)
        hydrate = observer.queue.get_nowait()
        self.assertEqual(hydrate["message_type"], "control_room.hydrate")
        self.assertEqual(
            hydrate["payload"]["selected_trade_route"]["source_buy_commodity"],
            "Agronomic Treatment",
        )
        selected = hydrate["payload"]["selected_trade_route"]
        self.assertEqual(
            [selected[key] for key in ("from_supply", "from_demand", "to_supply", "to_demand")],
            ["52,113", "1,204", "8,870", "96,431"],
        )
        self.assertEqual(
            [selected[key] for key in ("from_buy_price", "to_sell_price", "to_buy_price", "from_sell_price")],
            ["3,420 Cr", "40,684 Cr", "2,022 Cr", "2,661 Cr"],
        )
        self.assertEqual(
            [selected[key] for key in ("from_manual_landing", "to_manual_landing")],
            [True, False],
        )
        self.assertIsNone(hydrate["payload"]["running_trade_route"])

    def test_websocket_search_and_dispatch_haul_commands(self) -> None:
        def _receive_until_response(websocket, correlation_id: str) -> dict[str, object]:
            for _ in range(8):
                message = websocket.receive_json()
                if message.get("correlation_message_id") == correlation_id:
                    return message
            self.fail(f"Did not receive response for {correlation_id}")

        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=command_handler,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )
        result = TradeRouteSearchResult(
            system_name="Sol",
            query_url="https://inara.cz/elite/market-traderoutes/?ps1=Sol",
            searched_at="2026-07-04T08:00:00Z",
            routes=(
                TradeRoute(
                    index=1,
                    from_station="Galileo",
                    from_system="Sol",
                    to_station="Irkutsk",
                    to_system="Alioth",
                    source_buy_commodity="Agronomic Treatment",
                    route_distance="221.34 ly",
                    profit_per_hour="88.3m",
                ),
            ),
        )

        search_ran_outside_event_loop = False

        def fake_search_trade_routes(*args, **kwargs):
            nonlocal search_ran_outside_event_loop
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                search_ran_outside_event_loop = True
            return result

        with (
            patch("edcr.control_room.server.app.search_trade_routes", side_effect=fake_search_trade_routes),
            patch("edcr.control_room.server.app.save_haul_search_config"),
        ):
            with TestClient(app) as client:
                with client.websocket_connect(
                    "/session?client_name=web-haul&access_token=secret-token"
                ) as websocket:
                    websocket.receive_json()
                    websocket.receive_json()

                    websocket.send_json(
                        {
                            "message_type": "command.search_haul_routes",
                            "message_id": "message-web-search",
                            "payload": {"origin": "Sol", "destination": "Alioth"},
                        }
                    )
                    search_response = _receive_until_response(websocket, "message-web-search")
                    self.assertEqual(search_response["message_type"], "response.success")
                    self.assertEqual(
                        search_response["payload"]["result"]["routes"][0]["from_station"],
                        "Galileo",
                    )
                    self.assertTrue(search_ran_outside_event_loop)

                    websocket.send_json(
                        {
                            "message_type": "command.dispatch_haul_loop",
                            "message_id": "message-web-haul",
                            "payload": {
                                "params": {
                                    "station_1_buying": "Agronomic Treatment",
                                    "station_1": "Galileo",
                                    "station_1_system": "Sol",
                                    "station_1_manual_landing": "false",
                                    "station_2": "Irkutsk",
                                    "station_2_system": "Alioth",
                                    "station_2_manual_landing": "false",
                                },
                                "trade_route": {
                                    "index": 1,
                                    "from_station": "Galileo",
                                    "from_system": "Sol",
                                    "to_station": "Irkutsk",
                                    "to_system": "Alioth",
                                    "source_buy_commodity": "Agronomic Treatment",
                                    "route_distance": "221.34 ly",
                                    "profit_per_trip": "43.1m",
                                },
                                "raw_command": "web haul start Galileo -> Irkutsk",
                            },
                        }
                    )
                    dispatch_response = _receive_until_response(websocket, "message-web-haul")
                    self.assertEqual(dispatch_response["message_type"], "response.success")

        self.assertEqual(len(command_handler.dispatched_hauls), 1)
        params, skip_delay, raw_command = command_handler.dispatched_hauls[0]
        self.assertFalse(skip_delay)
        self.assertEqual(raw_command, "web haul start Galileo -> Irkutsk")
        self.assertEqual(
            params,
            {
                "station_1_buying": "Agronomic Treatment",
                "station_1": "Galileo",
                "station_1_system": "Sol",
                "station_1_manual_landing": "false",
                "station_2": "Irkutsk",
                "station_2_system": "Alioth",
                "station_2_manual_landing": "false",
                "route_profit_per_trip": "43.1m",
            },
        )
        self.assertEqual(broker.server_state.running_trade_route().from_station, "Galileo")
        self.assertEqual(command_handler.persisted_selected_trade_route.from_station, "Galileo")
        self.assertEqual(command_handler.persisted_running_trade_route.from_station, "Galileo")

    def test_websocket_clients_are_all_active_operators(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/session?client_name=bridge-ipad&access_token=secret-token"
            ) as first:
                first_ready = first.receive_json()
                with client.websocket_connect(
                    "/session?client_name=bridge-mac&access_token=secret-token"
                ) as second:
                    second_ready = second.receive_json()
                    second.receive_json()

                    self.assertEqual(first_ready["payload"]["client_role"], "active_operator")
                    self.assertEqual(second_ready["payload"]["client_role"], "active_operator")
                    self.assertEqual(
                        [client.client_role for client in broker.connected_clients()],
                        ["active_operator", "active_operator"],
                    )

                    first.close()

                    operator_event = second.receive_json()
                    self.assertEqual(operator_event["message_type"], "event.active_operator_changed")
                    self.assertEqual(
                        operator_event["payload"]["active_operator_client_name"],
                        "bridge-mac",
                    )
                    self.assertEqual(
                        broker.current_session_role(operator_event["payload"]["active_operator_session_id"]),
                        "active_operator",
                    )

    def test_websocket_session_client_local_command_is_treated_as_unknown(self) -> None:
        def _receive_until_message_type(websocket, expected_type: str) -> dict[str, object]:
            for _ in range(6):
                message = websocket.receive_json()
                if message["message_type"] == expected_type:
                    return message
            self.fail(f"Did not receive {expected_type}")

        with tempfile.TemporaryDirectory() as temp_dir:
            broker = InMemoryObserverSessionBroker()
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)), speech_backend=NullSpeechBackend(), version_source=_FakeVersionSource(), record_station_facts=_drop_facts)
            host._controls = object()
            app = build_observer_server_app(
                data_provider=host.dependencies.data_source.current,
                command_handler=host,
                broker=broker,
                auth=SharedAccessTokenAuth("secret-token"),
            )

            with TestClient(app) as client:
                with client.websocket_connect(
                    "/session?client_name=bridge-ipad&access_token=secret-token"
                ) as websocket:
                    websocket.receive_json()

                    websocket.send_json(
                        {
                            "message_type": "command.submit_input",
                            "message_id": "message-market",
                            "payload": {"raw_input": "market filter gold"},
                        }
                    )
                    response = _receive_until_message_type(websocket, "response.success")
                    self.assertEqual(response["correlation_message_id"], "message-market")
                    self.assertIsNone(host._market_filter)
                    self.assertIn(
                        "Unknown command: market filter gold",
                        "\n".join(
                            content.plain
                            for content, _ in host._activity_widget.writes
                        ),
                    )

            host.close()

    def test_websocket_session_active_operator_claim_updates_broker_role(self) -> None:
        def _receive_until_message_type(websocket, expected_type: str) -> dict[str, object]:
            for _ in range(6):
                message = websocket.receive_json()
                if message["message_type"] == expected_type:
                    return message
            self.fail(f"Did not receive {expected_type}")

        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/session?client_name=bridge-ipad&access_token=secret-token"
            ) as first:
                first.receive_json()
                with client.websocket_connect(
                    "/session?client_name=bridge-mac&access_token=secret-token"
                ) as second:
                    second.receive_json()

                    second_session_id = next(
                        session_id
                        for session_id, session in broker._sessions.items()
                        if session.client_name == "bridge-mac"
                    )

                    second.send_json(
                        {
                            "message_type": "command.request_active_operator",
                            "message_id": "message-claim-live",
                            "payload": {},
                        }
                    )
                    response = _receive_until_message_type(second, "response.success")
                    self.assertEqual(response["correlation_message_id"], "message-claim-live")
                    self.assertEqual(
                        broker.current_session_role(second_session_id),
                        "active_operator",
                    )

    def test_data_hydrate_fanout_sink_broadcasts_data_message(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")
        sink = DataHydrateFanoutSink(
            data_provider=_base_data_read_model,
            broker=broker,
        )

        sink.publish_data_refresh()

        message = observer.queue.get_nowait()
        self.assertEqual(message["schema"], "edcontrolroom.control_room_data_message")
        self.assertEqual(message["message_type"], "control_room.hydrate")
        self.assertEqual(message["payload"]["ship"]["system"], "Sol")

    def test_server_state_keeps_recent_announcements_for_future_sessions(self) -> None:
        server_state = ControlRoomServerState(announcement_limit=2)
        server_state.record_announcement(
            AnnouncementEvent(
                announcement_id="startup_greeting",
                message_text="Hello commander.",
                message_values={},
            )
        )
        server_state.record_announcement(
            AnnouncementEvent(
                announcement_id="arrival",
                message_text="Arrived in Sol.",
                message_values={"system_name": "Sol"},
            )
        )
        server_state.record_announcement(
            AnnouncementEvent(
                announcement_id="approaching_station",
                message_text="Approaching Jameson Memorial.",
                message_values={"station_name": "Jameson Memorial"},
            )
        )

        self.assertEqual(
            [event.announcement_id for event in server_state.announcements()],
            ["arrival", "approaching_station"],
        )

    def test_request_snapshot_command_is_unknown(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")

        response = _handle_session_message(
            {
                "message_type": "command.request_snapshot",
                "message_id": "message-42",
                "payload": {
                    "include_activity_log": True,
                    "include_market_state": True,
                },
            },
            session_id=observer.session_id,
            client_role="observer",
            command_handler=None,
            broker=broker,
        )

        self.assertEqual(response["message_type"], "response.error")
        self.assertEqual(response["correlation_message_id"], "message-42")
        self.assertEqual(response["payload"]["error_code"], "unsupported_message_type")

    def test_snapshot_endpoint_is_not_registered(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            response = client.get(
                "/snapshot",
                headers={"Authorization": "Bearer secret-token"},
            )

        self.assertEqual(response.status_code, 404)

    def test_observer_role_submit_input_command_calls_handler(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.submit_input",
                "message_id": "message-99",
                "payload": {"raw_input": "dock"},
            },
            session_id="observer-unknown",
            client_role="observer",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(command_handler.submitted_inputs, [("dock", None)])
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-99")

    def test_active_operator_submit_input_command_calls_handler(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.submit_input",
                "message_id": "message-100",
                "payload": {"raw_input": "market filter gold", "skip_delay": True},
            },
            session_id="observer-100",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(command_handler.submitted_inputs, [("market filter gold", True)])
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-100")

    def test_active_operator_submit_input_allows_blank_prompt_submission(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.submit_input",
                "message_id": "message-blank",
                "payload": {"raw_input": "", "skip_delay": None},
            },
            session_id="observer-blank",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(command_handler.submitted_inputs, [("", None)])
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-blank")

    def test_active_operator_dispatch_destination_calls_handler(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.dispatch_destination",
                "message_id": "message-dest",
                "payload": {
                    "destination": "Achenar",
                    "galaxy_map_settle": 3.5,
                    "skip_delay": True,
                    "raw_command": "!dest Achenar",
                },
            },
            session_id="observer-dest",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(
            command_handler.dispatched_destinations,
            [("Achenar", 3.5, True, "!dest Achenar")],
        )
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-dest")

    def test_active_operator_dispatch_haul_loop_calls_handler(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.dispatch_haul_loop",
                "message_id": "message-haul",
                "payload": {
                    "params": {
                        "station_1_buying": "Silver",
                        "station_1": "Savitskaya Orbital",
                        "station_1_system": "TSONGORIS",
                        "station_2": "Nyberg Vision",
                        "station_2_system": "NJOKUJINUN",
                    },
                    "skip_delay": False,
                    "raw_command": "haul Silver",
                },
            },
            session_id="observer-haul",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(
            command_handler.dispatched_hauls,
            [
                (
                    {
                        "station_1_buying": "Silver",
                        "station_1": "Savitskaya Orbital",
                        "station_1_system": "TSONGORIS",
                        "station_2": "Nyberg Vision",
                        "station_2_system": "NJOKUJINUN",
                    },
                    False,
                    "haul Silver",
                )
            ],
        )
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-haul")

    def test_active_operator_dispatch_travel_calls_handler(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.dispatch_travel",
                "message_id": "message-travel",
                "payload": {
                    "system": "Sol",
                    "station": "Abraham Lincoln",
                    "manual_landing": False,
                    "skip_delay": True,
                    "raw_command": "web travel Sol / Abraham Lincoln",
                },
            },
            session_id="observer-travel",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(
            command_handler.dispatched_travels,
            [("Sol", "Abraham Lincoln", False, True, "web travel Sol / Abraham Lincoln")],
        )
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-travel")

    def test_active_operator_dispatch_travel_allows_system_only_target(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.dispatch_travel",
                "message_id": "message-travel",
                "payload": {
                    "system": "Sol",
                    "raw_command": "web travel Sol",
                },
            },
            session_id="observer-travel",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(
            command_handler.dispatched_travels,
            [("Sol", "", False, False, "web travel Sol")],
        )
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["payload"]["result"], {"system": "Sol", "station": ""})

    def test_active_operator_dispatch_spansh_route_resolves_cached_route(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()
        route = Route(
            waypoints=(
                RouteWaypoint(system="Sol", star_class=None, neutron_boost=False, x=0.0, y=0.0, z=0.0, ly_from_prev=0.0, jumps_from_prev=0),
                RouteWaypoint(system="Xinca", star_class=None, neutron_boost=False, x=0.0, y=0.0, z=0.0, ly_from_prev=0.0, jumps_from_prev=1),
            ),
            total_ly=0.0, total_jumps=1, neutron_count=0,
            source="spansh", source_system="Sol", destination_system="Xinca",
            metadata=SpanshMetadata(efficiency=60, supercharge_multiplier=6, galaxy_map_visits=1),
        )
        route_id = broker.server_state.cache_spansh_route(
            route,
            request_key=RouteRequestKey(
                source_system="Sol", destination_system="Xinca",
                range_ly=60.0, efficiency=60, supercharge_multiplier=6,
            ),
        )

        response = _handle_session_message(
            {
                "message_type": "command.dispatch_spansh_route",
                "message_id": "message-spansh",
                "payload": {"route_id": route_id, "station": "Abraham Lincoln"},
            },
            session_id="observer-spansh",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(
            command_handler.dispatched_spansh_routes,
            [("Xinca", "Abraham Lincoln", False, None, 2)],
        )

    def test_active_operator_dispatch_spansh_route_unknown_id_returns_error(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.dispatch_spansh_route",
                "message_id": "message-spansh",
                "payload": {"route_id": "does-not-exist"},
            },
            session_id="observer-spansh",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(response["message_type"], "response.error")
        self.assertEqual(response["payload"]["error_code"], "invalid_command")
        self.assertEqual(command_handler.dispatched_spansh_routes, [])

    def test_active_operator_cancel_active_routine_calls_handler(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.cancel_active_routine",
                "message_id": "message-cancel",
                "payload": {},
            },
            session_id="observer-cancel",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(command_handler.cancel_modes, ["toggle"])
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-cancel")

    def test_active_operator_cancel_active_routine_passes_stop_mode(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.cancel_active_routine",
                "message_id": "message-stop-after-run",
                "payload": {"mode": "after_run"},
            },
            session_id="observer-stop-after-run",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(command_handler.cancel_modes, ["after_run"])
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["payload"]["message_text"], "Routine stop-after-run requested.")

    def test_active_operator_cancel_active_routine_passes_now_mode(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.cancel_active_routine",
                "message_id": "message-stop-now",
                "payload": {"mode": "now"},
            },
            session_id="observer-stop-now",
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(command_handler.cancel_modes, ["now"])
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["payload"]["message_text"], "Routine cancellation requested.")

    def test_observer_role_cancel_active_routine_calls_handler(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        response = _handle_session_message(
            {
                "message_type": "command.cancel_active_routine",
                "message_id": "message-cancel-observer",
                "payload": {},
            },
            session_id="observer-cancel-observer",
            client_role="observer",
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(command_handler.cancel_modes, ["toggle"])
        self.assertEqual(response["message_type"], "response.success")

    def test_broker_active_operator_claim_only_broadcasts_operator_event(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")
        broker.set_active_operator_session(observer.session_id)

        event = observer.queue.get_nowait()
        self.assertEqual(event["message_type"], "event.active_operator_changed")
        self.assertEqual(event["payload"]["active_operator_client_name"], "bridge-ipad")
        self.assertTrue(observer.queue.empty())

    def test_request_active_operator_claim_reassigns_session(self) -> None:
        broker = InMemoryObserverSessionBroker()
        first = broker.register_observer("bridge-ipad")
        second = broker.register_observer("bridge-mac")

        response = _handle_session_message(
            {
                "message_type": "command.request_active_operator",
                "message_id": "message-101",
                "payload": {},
            },
            session_id=second.session_id,
            client_role=broker.current_session_role(second.session_id),
            command_handler=None,
            broker=broker,
        )

        self.assertEqual(first.client_name, "bridge-ipad")
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-101")
        self.assertEqual(broker.current_session_role(second.session_id), "active_operator")

    def test_observer_endpoints_reject_missing_token(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            capabilities = client.get("/capabilities")
            self.assertEqual(capabilities.status_code, 401)

            response = client.get("/snapshot")
            self.assertEqual(response.status_code, 404)

    def test_server_activity_log_sink_mirrors_activity_messages(self) -> None:
        logger = logging.getLogger("tests.control_room.server.activity")
        records: list[str] = []

        class _Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Handler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        try:
            sink = ServerActivityLogSink(logger)
            sink.publish_activity_log(
                ActivityLogEntry(
                    entry_id="activity-000100",
                    timestamp="2026-06-19T12:20:00Z",
                    message_text="[green]Command accepted.[/]",
                    severity=None,
                )
            )
        finally:
            logger.removeHandler(handler)

        self.assertEqual(records, ["Command accepted."])
