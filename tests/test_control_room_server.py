from __future__ import annotations

from dataclasses import asdict
from dataclasses import replace
import logging
import unittest
import warnings
from pathlib import Path
import tempfile

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated; install `httpx2` instead\.",
)

from starlette.testclient import TestClient

from edap.config import (
    AppConfig,
    CaptureConfig,
    CaptureRegionConfig,
    ControlRoomConfig,
    ControlsConfig,
    MarketBuyHoldSegmentConfig,
    PathsConfig,
    RuntimeConfig,
    ScreenConfig,
    TTSConfig,
)
from edap.control_room.protocol.events import AnnouncementEvent
from edap.control_room.protocol.sink import ControlRoomEventSink
from edap.control_room.dependencies import (
    ActivityLogReadModel,
    CommandHistoryReadModel,
    ControlRoomDataReadModel,
    RoutineReadModel,
    ServerStatusReadModel,
    SessionReadModel,
)
from edap.control_room.models import HaulStats, MarketData, ShipState
from edap.control_room.protocol.snapshot import (
    ActivityLogEntry,
    ActiveOperatorSnapshot,
    CommandHistoryEntrySnapshot,
    CommandHistorySnapshot,
    ControlRoomSnapshot,
    HaulSessionSnapshot,
    MarketSnapshot,
    ServerStatusSnapshot,
    SessionSnapshot,
    ShipSnapshot,
    UiStateSnapshot,
)
from edap.control_room.server.app import (
    BROWSER_PROBE_URL_PATH,
    CONTROL_ROOM_MESSAGE_SCHEMA,
    MESSAGE_SCHEMA_URL_PATH,
    SUPPORTED_COMMAND_MESSAGE_TYPES,
    SUPPORTED_EVENT_MESSAGE_TYPES,
    SUPPORTED_MESSAGE_TYPES,
    SUPPORTED_RESPONSE_MESSAGE_TYPES,
    _handle_session_message,
    build_observer_server_app,
)
from edap.control_room.server.auth import SharedAccessTokenAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.control_room.server.commands import ObserverSessionCommandHandler
from edap.control_room.server.host import HeadlessControlRoomHost
from edap.control_room.server.sink import DataHydrateFanoutSink, ServerActivityLogSink
from edap.control_room.server.state import ControlRoomServerState
from edap.control_room_state import CommandHistoryEntry
from edap.runtime import ResolvedPath, RuntimeContext
from edap.timing import TimingChannelConfig, TimingConfig, TimingSampler
from edap.tts import AnnouncementId


def _make_timing_config() -> TimingConfig:
    channel = TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.0)
    return TimingConfig(enabled=False, distribution="log_normal", delay=channel, hold=channel, typing=channel)


def _make_config(journal_dir: Path) -> AppConfig:
    return AppConfig(
        paths=PathsConfig(journal_dir=journal_dir, bindings_file=None),
        controls=ControlsConfig(
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
        screen=ScreenConfig(
            resolution_width=1920,
            resolution_height=1080,
            scale=1.0,
            capture_debug_path=None,
            capture=CaptureConfig(
                mode="fullscreen",
                base_region=CaptureRegionConfig(0.0, 0.0, 1.0, 1.0),
                regions={},
            ),
        ),
        runtime=RuntimeConfig(platform="macos", debug=False),
        timing=_make_timing_config(),
        control_room=ControlRoomConfig(
            state_file=journal_dir / ".control_room_state.json",
            history_limit=20,
            activity_log_max_lines=2000,
            command_delay_seconds=0.0,
            status_refresh_seconds=2.0,
        ),
        tts=TTSConfig(enabled=False, title="captain", disabled_messages=(), phrases={}),
    )


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
        screen_capture=None,
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
        screen_capture=ctx.screen_capture,
        timing_sampler=ctx.timing_sampler,
        binding_lookup=ctx.binding_lookup,
        config_path=ctx.config_path,
        used_example_config_fallback=ctx.used_example_config_fallback,
    )


def _base_snapshot() -> ControlRoomSnapshot:
    return ControlRoomSnapshot(
        session=SessionSnapshot(session_id="local-server", client_role="active_operator"),
        connected_clients=[],
        active_operator=ActiveOperatorSnapshot(session_id="local-server", client_name="local-server"),
        ship=ShipSnapshot(
            commander_name="CMDR TEST",
            ship_type="Type-9",
            system_name="Sol",
            station_name="Jameson Memorial",
            status="in_station",
            fuel_level=10.0,
            fuel_capacity=32.0,
            credits=1000,
            cargo_count=2,
            cargo_capacity=100,
            cargo_inventory=[],
        ),
        market=MarketSnapshot(
            station_name="Jameson Memorial",
            system_name="Sol",
            market_timestamp="2026-06-15T18:00:00Z",
            items=[],
        ),
        haul_session=HaulSessionSnapshot(
            station_1_buying="",
            station_2_buying="",
            station_1="",
            station_2="",
            session_started_at=None,
            session_elapsed_seconds=0.0,
            session_active=False,
            active=False,
            clean_run_active=False,
            waiting_for_station_1_departure=False,
            resumed_mid_run=False,
            docked_back_at_station_1=False,
            current_run_started_at=None,
            current_run_elapsed_seconds=None,
            current_run_profit=0,
            completed_runs=0,
            accumulated_profit=0,
            last_run_profit=None,
            last_run_elapsed_seconds=None,
            total_run_elapsed_seconds=0.0,
        ),
        ui_state=UiStateSnapshot(
            routine_active=False,
            active_routine_name=None,
            haul_stop_requested=False,
            verbose_controls=False,
            instant_mode=False,
            activity_auto_follow_paused=False,
            shutdown_requested=False,
            shutdown_finalized=False,
        ),
        command_history=CommandHistorySnapshot(history_limit=20),
        activity_log=[
            ActivityLogEntry(
                entry_id="activity-000001",
                timestamp="2026-06-15T18:00:00Z",
                message_text="Hello commander.",
                severity=None,
            )
        ],
        server_status=ServerStatusSnapshot(
            server_name="ED Control Room",
            server_version="1.2.3",
            runtime_platform="macos",
            journal_source_status="configured",
            bindings_source_status="configured",
            bindings_loaded=False,
            capability_names=["observer_http", "observer_websocket", "announcement_stream"],
            operator_mode="observer_only",
        ),
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
        ),
    )


class _SnapshotRecorder(ControlRoomEventSink):
    def __init__(self) -> None:
        self.activity_entries: list[ActivityLogEntry] = []
        self.announcements: list[AnnouncementEvent] = []
        self.snapshots: list[ControlRoomSnapshot] = []

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        self.activity_entries.append(entry)

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        self.announcements.append(event)

    def publish_snapshot(self, snapshot: ControlRoomSnapshot) -> None:
        self.snapshots.append(snapshot)


class _CommandHandlerRecorder(ObserverSessionCommandHandler):
    def __init__(self) -> None:
        self.submitted_inputs: list[tuple[str, bool | None]] = []
        self.dispatched_destinations: list[tuple[str, float, bool, str | None]] = []
        self.dispatched_hauls: list[tuple[dict[str, str] | None, bool, str | None]] = []
        self.loaded_trade_routes: list[tuple[object, str | None]] = []
        self.cancel_calls = 0

    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None:
        self.submitted_inputs.append((raw_input, skip_delay))

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

    def load_trade_route(self, route, *, raw_command: str | None = None) -> None:
        self.loaded_trade_routes.append((route, raw_command))

    def cancel_active_routine(self) -> None:
        self.cancel_calls += 1


class ControlRoomServerTests(unittest.TestCase):
    def test_headless_host_initializes_and_can_snapshot_before_mount(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))

            snapshot = host.snapshot()

        self.assertEqual(snapshot.session.session_id, "local-server")
        self.assertFalse(snapshot.ui_state.activity_auto_follow_paused)

    def test_headless_host_accepts_simple_remote_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))

            host.handle_remote_input("market filter gold")

        self.assertIsNone(host._market_filter)
        self.assertIn("Unknown command: market filter gold", "\n".join(content.plain for content, _ in host._activity_widget.writes))
        self.assertEqual(host._saved_state.history[-1].command, "market")

    def test_headless_host_submit_input_alias_accepts_simple_remote_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))

            host.submit_input("market filter gold")

        self.assertIsNone(host._market_filter)
        self.assertIn("Unknown command: market filter gold", "\n".join(content.plain for content, _ in host._activity_widget.writes))

    def test_headless_host_emits_announcement_events_without_local_speech(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context_with_tts(Path(temp_dir)))
            sink = _SnapshotRecorder()
            host._protocol_event_sink = sink

            host._announce_tts(AnnouncementId.ARRIVAL, system_name="Sol")

        self.assertEqual([event.announcement_id for event in sink.announcements], ["arrival"])
        self.assertIsNone(host._tts._speaker)

    def test_headless_host_start_bootstraps_commander_before_startup_greeting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = Path(temp_dir)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"LoadGame","Commander":"VRYAE"}\n',
                encoding="utf-8",
            )
            host = HeadlessControlRoomHost(_make_context_with_tts(journal_dir))
            host._start_watcher_loop = lambda: None

            host.start()

        self.assertEqual(host._protocol_announcements[0].message_text, "Hello VRYAE")

    def test_headless_host_publishes_snapshot_after_remote_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))
            sink = _SnapshotRecorder()
            host._protocol_event_sink = sink

            host.handle_remote_input("market filter gold")

        self.assertTrue(sink.snapshots)
        self.assertEqual(sink.snapshots[-1].command_history.history_entries[-1].raw_command, "market filter gold")

    def test_headless_host_remote_ctrl_c_cancels_prompt_flow_and_publishes_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))
            sink = _SnapshotRecorder()
            host._protocol_event_sink = sink
            host._start_dest_prompt("Achenar")

            host.cancel_active_routine()

        self.assertEqual(host._dest_prompt_destination, "")
        self.assertIsNone(host._dest_prompt_settle_default)
        self.assertTrue(sink.snapshots)
        self.assertEqual(sink.snapshots[-1].ship.commander_name, host.snapshot().ship.commander_name)

    def test_http_endpoints_and_websocket_observer_stream(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            snapshot_provider=_base_snapshot,
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
            snapshot_provider=_base_snapshot,
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
            snapshot_provider=_base_snapshot,
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

    def test_browser_probe_endpoint_is_public_html(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            snapshot_provider=_base_snapshot,
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

    def test_websocket_active_operator_failover_promotes_remaining_client(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            snapshot_provider=_base_snapshot,
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

                    first.close()

                    promoted_event = second.receive_json()
                    self.assertEqual(promoted_event["message_type"], "event.active_operator_changed")
                    self.assertEqual(
                        promoted_event["payload"]["active_operator_client_name"],
                        "bridge-mac",
                    )
                    self.assertEqual(
                        broker.current_session_role(promoted_event["payload"]["active_operator_session_id"]),
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
            server_state = ControlRoomServerState()
            broker = InMemoryObserverSessionBroker(server_state=server_state)
            host = HeadlessControlRoomHost(
                _make_context(Path(temp_dir)),
                server_state=server_state,
            )
            host._controls = object()
            app = build_observer_server_app(
                snapshot_provider=host.snapshot,
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
            snapshot_provider=_base_snapshot,
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

    def test_broker_retains_latest_snapshot_without_broadcasting_it(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")

        broker.publish_snapshot(_base_snapshot())

        self.assertTrue(observer.queue.empty())
        retained = broker.current_snapshot(snapshot_provider=_base_snapshot)
        self.assertEqual(retained.ship.system_name, "Sol")

    def test_data_hydrate_fanout_sink_broadcasts_data_message(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")
        sink = DataHydrateFanoutSink(
            data_provider=_base_data_read_model,
            broker=broker,
        )

        sink.publish_snapshot(_base_snapshot())

        message = observer.queue.get_nowait()
        self.assertEqual(message["schema"], "edcontrolroom.control_room_data_message")
        self.assertEqual(message["message_type"], "control_room.hydrate")
        self.assertEqual(message["payload"]["ship"]["system"], "Sol")

    def test_broker_retains_server_owned_activity_history_in_current_snapshot(self) -> None:
        broker = InMemoryObserverSessionBroker()
        broker.publish_snapshot(_base_snapshot())
        broker.publish_activity_log(
            ActivityLogEntry(
                entry_id="activity-000002",
                timestamp="2026-06-15T18:01:00Z",
                message_text="Market filter set to Gold.",
                severity=None,
            )
        )

        observer = broker.register_observer("bridge-ipad")

        self.assertTrue(observer.queue.empty())
        retained = broker.current_snapshot(snapshot_provider=_base_snapshot)
        self.assertEqual(
            [entry.message_text for entry in retained.activity_log],
            ["Hello commander.", "Market filter set to Gold."],
        )

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

    def test_server_state_retains_remote_command_history_session_state(self) -> None:
        server_state = ControlRoomServerState()
        history_entry = CommandHistoryEntry(
            raw="haul gold",
            command="haul",
            params={"station_1_buying": "gold"},
            timestamp="2026-06-15T18:00:00Z",
        )
        retained_snapshot = replace(
            _base_snapshot(),
            command_history=replace(
                _base_snapshot().command_history,
                default_haul={"station_1_buying": "gold"},
                history_entries=[
                    CommandHistoryEntrySnapshot(
                        raw_command=history_entry.raw,
                        command_name=history_entry.command,
                        arguments=history_entry.params,
                        timestamp=history_entry.timestamp,
                    )
                ],
            ),
        )
        server_state.capture_remote_session(retained_snapshot)

        merged = server_state.merge_snapshot(_base_snapshot())

        self.assertEqual(merged.command_history.default_haul, {"station_1_buying": "gold"})
        self.assertEqual(merged.command_history.history_entries[0].raw_command, "haul gold")

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
            snapshot_provider=_base_snapshot,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            snapshot = client.get(
                "/snapshot",
                headers={"Authorization": "Bearer secret-token"},
            )

        self.assertEqual(snapshot.status_code, 404)

    def test_observer_submit_input_command_is_rejected(self) -> None:
        broker = InMemoryObserverSessionBroker()

        response = _handle_session_message(
            {
                "message_type": "command.submit_input",
                "message_id": "message-99",
                "payload": {"raw_input": "dock"},
            },
            session_id="observer-unknown",
            client_role="observer",
            command_handler=None,
            broker=broker,
        )

        self.assertEqual(response["message_type"], "response.error")
        self.assertEqual(response["correlation_message_id"], "message-99")
        self.assertEqual(response["payload"]["error_code"], "observer_read_only")

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

        self.assertEqual(command_handler.cancel_calls, 1)
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-cancel")

    def test_observer_cancel_active_routine_is_rejected(self) -> None:
        broker = InMemoryObserverSessionBroker()

        response = _handle_session_message(
            {
                "message_type": "command.cancel_active_routine",
                "message_id": "message-cancel-observer",
                "payload": {},
            },
            session_id="observer-cancel-observer",
            client_role="observer",
            command_handler=None,
            broker=broker,
        )

        self.assertEqual(response["message_type"], "response.error")
        self.assertEqual(response["payload"]["error_code"], "observer_read_only")
    def test_broker_active_operator_claim_only_broadcasts_operator_event(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")
        broker.set_active_operator_session(observer.session_id)

        broker.publish_snapshot(_base_snapshot())

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
            snapshot_provider=_base_snapshot,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            capabilities = client.get("/capabilities")
            self.assertEqual(capabilities.status_code, 401)

            snapshot = client.get("/snapshot")
            self.assertEqual(snapshot.status_code, 404)

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
