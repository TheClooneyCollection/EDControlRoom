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
from edap.control_room.protocol.snapshot import (
    ActivityLogEntry,
    ActiveOperatorSnapshot,
    CommandHistorySnapshot,
    ControlRoomSnapshot,
    HaulSessionSnapshot,
    MarketSnapshot,
    PromptStateSnapshot,
    ReplayBrowserSnapshot,
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
from edap.control_room.server.sink import ServerActivityLogSink
from edap.control_room.server.state import ControlRoomServerState
from edap.control_room_state import CommandHistoryEntry
from edap.runtime import ResolvedPath, RuntimeContext
from edap.tts import AnnouncementId


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
            market_filter_text=None,
            locked=False,
            items=[],
        ),
        haul_session=HaulSessionSnapshot(
            station_1_buying="",
            station_2_buying="",
            station_1="",
            station_2="",
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
            replay_browser_open=False,
            shutdown_requested=False,
            shutdown_finalized=False,
        ),
        command_history=CommandHistorySnapshot(history_limit=20),
        prompt_state=PromptStateSnapshot(),
        replay_browser=ReplayBrowserSnapshot(open=False, filter_text=""),
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
        self.cancel_calls = 0
        self.opened_replay_browser = 0
        self.closed_replay_browser = 0
        self.replay_filters: list[str] = []
        self.replay_selection_offsets: list[int] = []
        self.replayed_entries: list[tuple[str, str, bool, bool]] = []
        self.toggled_default_hauls: list[str] = []

    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None:
        self.submitted_inputs.append((raw_input, skip_delay))

    def cancel_active_routine(self) -> None:
        self.cancel_calls += 1

    def open_replay_browser(self) -> None:
        self.opened_replay_browser += 1

    def close_replay_browser(self) -> None:
        self.closed_replay_browser += 1

    def set_replay_filter(self, filter_text: str) -> None:
        self.replay_filters.append(filter_text)

    def move_replay_selection(self, offset: int) -> None:
        self.replay_selection_offsets.append(offset)

    def replay_history_entry(
        self,
        entry,
        *,
        edit: bool,
        skip_delay: bool = False,
    ) -> None:
        self.replayed_entries.append((entry.raw, entry.command, edit, skip_delay))

    def toggle_replay_default_haul(self, entry) -> None:
        self.toggled_default_hauls.append(entry.raw)
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

        self.assertEqual(host._market_filter, "Gold")

    def test_headless_host_submit_input_alias_accepts_simple_remote_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))

            host.submit_input("market filter gold")

        self.assertEqual(host._market_filter, "Gold")

    def test_headless_host_emits_announcement_events_without_local_speech(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context_with_tts(Path(temp_dir)))
            sink = _SnapshotRecorder()
            host._protocol_event_sink = sink

            host._announce_tts(AnnouncementId.ARRIVAL, system_name="Sol")

        self.assertEqual([event.announcement_id for event in sink.announcements], ["arrival"])
        self.assertIsNone(host._tts._speaker)

    def test_headless_host_publishes_snapshot_after_remote_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))
            sink = _SnapshotRecorder()
            host._protocol_event_sink = sink

            host.handle_remote_input("market filter gold")

        self.assertTrue(sink.snapshots)
        self.assertEqual(
            sink.snapshots[-1].market.market_filter_text,
            "Gold",
        )

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
        self.assertEqual(sink.snapshots[-1].prompt_state.destination_prompt_destination, "")

    def test_http_endpoints_and_websocket_observer_stream(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            snapshot_provider=_base_snapshot,
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
                capabilities.json()["authentication_query_parameter_name"],
                "access_token",
            )

            snapshot = client.get(
                "/snapshot",
                headers={"Authorization": "Bearer secret-token"},
            )
            self.assertEqual(snapshot.status_code, 200)
            self.assertEqual(snapshot.json()["ship"]["commander_name"], "CMDR TEST")

            with client.websocket_connect(
                "/session?client_name=bridge-ipad&access_token=secret-token"
            ) as websocket:
                ready = websocket.receive_json()
                self.assertEqual(ready["message_type"], "event.connection_ready")
                self.assertEqual(ready["payload"]["client_role"], "active_operator")

                state = websocket.receive_json()
                self.assertEqual(state["message_type"], "state.snapshot")
                self.assertEqual(state["payload"]["session"]["client_role"], "active_operator")
                self.assertEqual(
                    state["payload"]["connected_clients"][0]["client_name"],
                    "bridge-ipad",
                )

                broker.publish_announcement(
                    AnnouncementEvent(
                        announcement_id="startup_greeting",
                        message_text="Hello commander.",
                        message_values={},
                    )
                )
                announcement = websocket.receive_json()
                while announcement["message_type"] == "state.snapshot":
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
            self.assertIn("command.open_replay_browser", response.text)
            self.assertIn("command.replay_history_entry", response.text)
            self.assertIn("command.toggle_replay_default_haul", response.text)
            self.assertIn("Reconnecting in", response.text)
            self.assertIn("Observer connection restored.", response.text)

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
                first.receive_json()
                with client.websocket_connect(
                    "/session?client_name=bridge-mac&access_token=secret-token"
                ) as second:
                    second.receive_json()
                    second.receive_json()

                    first.close()

                    promoted_event = second.receive_json()
                    while promoted_event["message_type"] == "state.snapshot":
                        promoted_event = second.receive_json()
                    self.assertEqual(promoted_event["message_type"], "event.active_operator_changed")
                    self.assertEqual(
                        promoted_event["payload"]["active_operator_client_name"],
                        "bridge-mac",
                    )

                    promoted_snapshot = second.receive_json()
                    while promoted_snapshot["message_type"] != "state.snapshot":
                        promoted_snapshot = second.receive_json()
                    self.assertEqual(
                        promoted_snapshot["payload"]["session"]["client_role"],
                        "active_operator",
                    )
                    self.assertEqual(
                        promoted_snapshot["payload"]["active_operator"]["client_name"],
                        "bridge-mac",
                    )

    def test_websocket_session_routes_replay_navigation_command(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()
        app = build_observer_server_app(
            snapshot_provider=_base_snapshot,
            command_handler=command_handler,
            broker=broker,
            auth=SharedAccessTokenAuth("secret-token"),
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/session?client_name=bridge-ipad&access_token=secret-token"
            ) as websocket:
                websocket.receive_json()
                websocket.receive_json()

                websocket.send_json(
                    {
                        "message_type": "command.move_replay_selection",
                        "message_id": "message-move-1",
                        "payload": {"offset": -1},
                    }
                )

                response = websocket.receive_json()
                self.assertEqual(response["message_type"], "response.success")
                self.assertEqual(response["correlation_message_id"], "message-move-1")
                self.assertEqual(command_handler.replay_selection_offsets, [-1])

    def test_websocket_session_destination_prompt_flow_updates_headless_snapshot(self) -> None:
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
            dispatched_destinations: list[tuple[str, float, bool, str | None]] = []
            host._backend.dispatch_destination = (  # type: ignore[method-assign]
                lambda destination, galaxy_map_settle, *, skip_delay=False, raw_command=None: (
                    dispatched_destinations.append(
                        (destination, galaxy_map_settle, skip_delay, raw_command)
                    )
                )
            )
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
                    websocket.receive_json()

                    websocket.send_json(
                        {
                            "message_type": "command.submit_input",
                            "message_id": "message-dest-open",
                            "payload": {"raw_input": "dest achenar"},
                        }
                    )
                    response = _receive_until_message_type(websocket, "response.success")
                    self.assertEqual(response["correlation_message_id"], "message-dest-open")
                    current_snapshot = broker.current_snapshot(
                        snapshot_provider=host.snapshot,
                        session_id=next(iter(broker._sessions.keys())),
                    )
                    self.assertEqual(
                        current_snapshot.prompt_state.destination_prompt_destination,
                        "achenar",
                    )

                    websocket.send_json(
                        {
                            "message_type": "command.submit_input",
                            "message_id": "message-dest-submit",
                            "payload": {"raw_input": ""},
                        }
                    )
                    response = _receive_until_message_type(websocket, "response.success")
                    self.assertEqual(response["correlation_message_id"], "message-dest-submit")
                    current_snapshot = broker.current_snapshot(
                        snapshot_provider=host.snapshot,
                        session_id=next(iter(broker._sessions.keys())),
                    )
                    self.assertEqual(
                        current_snapshot.prompt_state.destination_prompt_destination,
                        "",
                    )
                    self.assertEqual(
                        dispatched_destinations,
                        [("achenar", 2.0, False, "dest achenar")],
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
                first.receive_json()
                with client.websocket_connect(
                    "/session?client_name=bridge-mac&access_token=secret-token"
                ) as second:
                    second.receive_json()
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

    def test_broker_broadcasts_live_snapshot_updates(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")

        broker.publish_snapshot(_base_snapshot())

        message = observer.queue.get_nowait()
        self.assertEqual(message["message_type"], "state.snapshot")
        self.assertEqual(message["payload"]["session"]["client_role"], "active_operator")
        self.assertEqual(
            message["payload"]["connected_clients"][0]["client_name"],
            "bridge-ipad",
        )

    def test_broker_replays_server_owned_activity_history_in_new_snapshots(self) -> None:
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

        message = observer.queue.get_nowait()
        self.assertEqual(message["message_type"], "state.snapshot")
        self.assertEqual(
            [entry["message_text"] for entry in message["payload"]["activity_log"]],
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

    def test_server_state_retains_remote_prompt_and_replay_session_state(self) -> None:
        server_state = ControlRoomServerState()
        retained_snapshot = replace(
            _base_snapshot(),
            command_history=replace(
                _base_snapshot().command_history,
                draft_command="haul gold",
                replay_filter_text="haul",
            ),
            prompt_state=PromptStateSnapshot(
                destination_prompt_destination="Achenar",
                destination_prompt_settle_default=2.0,
                destination_prompt_raw_command="dest achenar",
            ),
            replay_browser=ReplayBrowserSnapshot(
                open=True,
                filter_text="haul",
            ),
            ui_state=replace(_base_snapshot().ui_state, replay_browser_open=True),
        )
        server_state.capture_remote_session(retained_snapshot)

        merged = server_state.merge_snapshot(_base_snapshot())

        self.assertEqual(merged.command_history.draft_command, "haul gold")
        self.assertEqual(merged.command_history.replay_filter_text, "haul")
        self.assertEqual(merged.prompt_state.destination_prompt_destination, "Achenar")
        self.assertTrue(merged.replay_browser.open)
        self.assertEqual(merged.replay_browser.filter_text, "haul")
        self.assertTrue(merged.ui_state.replay_browser_open)

    def test_request_snapshot_command_returns_correlated_snapshot(self) -> None:
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
            snapshot_provider=_base_snapshot,
            command_handler=None,
            broker=broker,
        )

        self.assertEqual(response["message_type"], "state.snapshot")
        self.assertEqual(response["correlation_message_id"], "message-42")
        self.assertEqual(response["payload"]["session"]["client_role"], "active_operator")
        self.assertEqual(response["payload"]["connected_clients"][0]["client_name"], "bridge-ipad")

    def test_snapshot_endpoint_prefers_broker_retained_snapshot(self) -> None:
        broker = InMemoryObserverSessionBroker()
        retained_snapshot = ControlRoomSnapshot(
            session=_base_snapshot().session,
            connected_clients=_base_snapshot().connected_clients,
            active_operator=_base_snapshot().active_operator,
            ship=ShipSnapshot(**{**asdict(_base_snapshot().ship), "system_name": "Achenar"}),
            market=_base_snapshot().market,
            haul_session=_base_snapshot().haul_session,
            ui_state=_base_snapshot().ui_state,
            command_history=_base_snapshot().command_history,
            prompt_state=_base_snapshot().prompt_state,
            replay_browser=_base_snapshot().replay_browser,
            activity_log=_base_snapshot().activity_log,
            server_status=_base_snapshot().server_status,
        )
        broker.publish_snapshot(retained_snapshot)
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

        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(snapshot.json()["ship"]["system_name"], "Achenar")

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
            snapshot_provider=_base_snapshot,
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
            snapshot_provider=_base_snapshot,
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
            snapshot_provider=_base_snapshot,
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(command_handler.submitted_inputs, [("", None)])
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(response["correlation_message_id"], "message-blank")

    def test_active_operator_replay_commands_call_handler(self) -> None:
        broker = InMemoryObserverSessionBroker()
        command_handler = _CommandHandlerRecorder()

        open_response = _handle_session_message(
            {
                "message_type": "command.open_replay_browser",
                "message_id": "message-open",
                "payload": {},
            },
            session_id="observer-open",
            client_role="active_operator",
            snapshot_provider=_base_snapshot,
            command_handler=command_handler,
            broker=broker,
        )
        filter_response = _handle_session_message(
            {
                "message_type": "command.set_replay_filter",
                "message_id": "message-filter",
                "payload": {"filter_text": "haul"},
            },
            session_id="observer-open",
            client_role="active_operator",
            snapshot_provider=_base_snapshot,
            command_handler=command_handler,
            broker=broker,
        )
        move_response = _handle_session_message(
            {
                "message_type": "command.move_replay_selection",
                "message_id": "message-move",
                "payload": {"offset": 1},
            },
            session_id="observer-open",
            client_role="active_operator",
            snapshot_provider=_base_snapshot,
            command_handler=command_handler,
            broker=broker,
        )
        replay_response = _handle_session_message(
            {
                "message_type": "command.replay_history_entry",
                "message_id": "message-replay",
                "payload": {
                    "raw_command": "haul gold",
                    "command_name": "haul",
                    "arguments": {"station_1_buying": "gold"},
                    "timestamp": "2026-06-15T18:00:00Z",
                    "edit": True,
                    "skip_delay": True,
                },
            },
            session_id="observer-open",
            client_role="active_operator",
            snapshot_provider=_base_snapshot,
            command_handler=command_handler,
            broker=broker,
        )
        toggle_response = _handle_session_message(
            {
                "message_type": "command.toggle_replay_default_haul",
                "message_id": "message-toggle",
                "payload": {
                    "raw_command": "haul gold",
                    "command_name": "haul",
                    "arguments": {"station_1_buying": "gold"},
                    "timestamp": "2026-06-15T18:00:00Z",
                },
            },
            session_id="observer-open",
            client_role="active_operator",
            snapshot_provider=_base_snapshot,
            command_handler=command_handler,
            broker=broker,
        )
        close_response = _handle_session_message(
            {
                "message_type": "command.close_replay_browser",
                "message_id": "message-close",
                "payload": {},
            },
            session_id="observer-open",
            client_role="active_operator",
            snapshot_provider=_base_snapshot,
            command_handler=command_handler,
            broker=broker,
        )

        self.assertEqual(open_response["message_type"], "response.success")
        self.assertEqual(filter_response["message_type"], "response.success")
        self.assertEqual(move_response["message_type"], "response.success")
        self.assertEqual(replay_response["message_type"], "response.success")
        self.assertEqual(toggle_response["message_type"], "response.success")
        self.assertEqual(close_response["message_type"], "response.success")
        self.assertEqual(command_handler.opened_replay_browser, 1)
        self.assertEqual(command_handler.closed_replay_browser, 1)
        self.assertEqual(command_handler.replay_filters, ["haul"])
        self.assertEqual(command_handler.replay_selection_offsets, [1])
        self.assertEqual(
            command_handler.replayed_entries,
            [("haul gold", "haul", True, True)],
        )
        self.assertEqual(command_handler.toggled_default_hauls, ["haul gold"])

    def test_headless_host_remote_replay_commands_update_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))
            host._saved_state.history = [
                CommandHistoryEntry(
                    raw="haul gold",
                    command="haul",
                    params={
                        "station_1_buying": "gold",
                        "station_2_buying": "silver",
                        "station_1": "Jameson Memorial",
                        "station_2": "Hutton Orbital",
                    },
                    timestamp="2026-06-15T18:00:00Z",
                )
            ]
            sink = _SnapshotRecorder()
            host._protocol_event_sink = sink

            host.open_replay_browser()
            host.set_replay_filter("haul")
            host.move_replay_selection(0)
            host.toggle_replay_default_haul(host._saved_state.history[0])

        self.assertTrue(sink.snapshots)
        latest = sink.snapshots[-1]
        self.assertTrue(latest.replay_browser.open)
        self.assertEqual(latest.replay_browser.filter_text, "haul")
        self.assertEqual(latest.command_history.default_haul["station_1_buying"], "gold")
        self.assertIsNotNone(latest.replay_browser.selected_history_entry)
        self.assertEqual(
            latest.replay_browser.selected_history_entry.raw_command,
            "haul gold",
        )

    def test_headless_host_replay_selection_moves_and_updates_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = HeadlessControlRoomHost(_make_context(Path(temp_dir)))
            host._saved_state.history = [
                CommandHistoryEntry(raw="dock", command="dock", timestamp="1"),
                CommandHistoryEntry(raw="jump", command="jump", timestamp="2"),
            ]
            sink = _SnapshotRecorder()
            host._protocol_event_sink = sink

            host.open_replay_browser()
            host.move_replay_selection(1)

        initial = sink.snapshots[0]
        latest = sink.snapshots[-1]
        self.assertIsNotNone(initial.replay_browser.selected_history_entry)
        self.assertIsNotNone(latest.replay_browser.selected_history_entry)
        self.assertEqual(initial.replay_browser.selected_history_entry.raw_command, "jump")
        self.assertEqual(latest.replay_browser.selected_history_entry.raw_command, "dock")

    def test_headless_host_feeds_retained_server_session_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            server_state = ControlRoomServerState()
            host = HeadlessControlRoomHost(
                _make_context(Path(temp_dir)),
                server_state=server_state,
            )
            host._start_dest_prompt("Achenar")
            host._publish_snapshot()

            merged = server_state.merge_snapshot(_base_snapshot())

        self.assertEqual(merged.prompt_state.destination_prompt_destination, "Achenar")
        self.assertEqual(merged.prompt_state.destination_prompt_raw_command, "dest Achenar")

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
            snapshot_provider=_base_snapshot,
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
            snapshot_provider=_base_snapshot,
            command_handler=None,
            broker=broker,
        )

        self.assertEqual(response["message_type"], "response.error")
        self.assertEqual(response["payload"]["error_code"], "observer_read_only")
    def test_broker_personalizes_snapshot_for_active_operator_session(self) -> None:
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("bridge-ipad")
        broker.set_active_operator_session(observer.session_id)

        broker.publish_snapshot(_base_snapshot())

        first = observer.queue.get_nowait()
        second = observer.queue.get_nowait()
        self.assertEqual(first["message_type"], "event.active_operator_changed")
        self.assertEqual(first["payload"]["active_operator_client_name"], "bridge-ipad")
        self.assertEqual(second["message_type"], "state.snapshot")
        self.assertEqual(second["payload"]["session"]["client_role"], "active_operator")
        self.assertEqual(second["payload"]["active_operator"]["client_name"], "bridge-ipad")

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
            snapshot_provider=_base_snapshot,
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
            self.assertEqual(snapshot.status_code, 401)

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
                    message_text="Command accepted.",
                    severity=None,
                )
            )
        finally:
            logger.removeHandler(handler)

        self.assertEqual(records, ["Command accepted."])
