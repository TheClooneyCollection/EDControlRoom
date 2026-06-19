from __future__ import annotations

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
from edap.control_room.server.app import _handle_session_message, build_observer_server_app
from edap.control_room.server.auth import SharedAccessTokenAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.control_room.server.commands import ObserverSessionCommandHandler
from edap.control_room.server.host import HeadlessControlRoomHost
from edap.control_room.server.state import ControlRoomServerState
from edap.control_room_state import CommandHistoryEntry
from edap.runtime import ResolvedPath, RuntimeContext


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
        self.opened_replay_browser = 0
        self.closed_replay_browser = 0
        self.replay_filters: list[str] = []
        self.replayed_entries: list[tuple[str, str, bool, bool]] = []
        self.toggled_default_hauls: list[str] = []

    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None:
        self.submitted_inputs.append((raw_input, skip_delay))

    def open_replay_browser(self) -> None:
        self.opened_replay_browser += 1

    def close_replay_browser(self) -> None:
        self.closed_replay_browser += 1

    def set_replay_filter(self, filter_text: str) -> None:
        self.replay_filters.append(filter_text)

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
                self.assertEqual(announcement["message_type"], "event.announcement_emitted")
                self.assertEqual(announcement["payload"]["announcement_id"], "startup_greeting")

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
        self.assertEqual(replay_response["message_type"], "response.success")
        self.assertEqual(toggle_response["message_type"], "response.success")
        self.assertEqual(close_response["message_type"], "response.success")
        self.assertEqual(command_handler.opened_replay_browser, 1)
        self.assertEqual(command_handler.closed_replay_browser, 1)
        self.assertEqual(command_handler.replay_filters, ["haul"])
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
            host.toggle_replay_default_haul(host._saved_state.history[0])

        self.assertTrue(sink.snapshots)
        latest = sink.snapshots[-1]
        self.assertTrue(latest.replay_browser.open)
        self.assertEqual(latest.replay_browser.filter_text, "haul")
        self.assertEqual(latest.command_history.default_haul["station_1_buying"], "gold")

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
