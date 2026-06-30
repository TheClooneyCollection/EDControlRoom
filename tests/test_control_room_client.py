from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
import unittest
from unittest.mock import patch

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
from edap.control_room.client.connect import ObserverControlRoomApp
from edap.control_room.client.backend import (
    RemoteObserverBackend,
    RemoteObserverDataSource,
    RemoteObserverExecution,
    _validate_remote_observer_capabilities,
    initial_remote_snapshot_from_data,
)
from edap.control_room.dependencies import (
    ActivityLogReadModel,
    CommandHistoryReadModel,
    ControlRoomDataReadModel,
    RoutineReadModel,
    ServerStatusReadModel,
    SessionReadModel,
)
from edap.control_room import commands as control_room_commands
from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.models import TradeRoutePickerState, TradeRoutesData
from edap.control_room.models import HaulStats, MarketData, ShipState
from edap.control_room.protocol import (
    ACCESS_TOKEN_QUERY_PARAMETER,
    ActivityLogAppendedEvent,
    AUTHENTICATION_SCHEME_BEARER_TOKEN,
    DataUpdatedEvent,
    REQUIRED_AUTHENTICATION_TRANSPORTS,
    RemoteObserverWebSocketConnectInfo,
    SnapshotUpdatedEvent,
    build_remote_observer_capabilities_payload,
    build_remote_observer_websocket_connect_info,
    event_from_message,
    hydrate_message,
)
from edap.inara.trade_routes import TradeRoute, TradeRouteSearchResult
from edap.control_room.protocol.snapshot import (
    ActivityLogEntry,
    ActiveOperatorSnapshot,
    CommandHistoryEntrySnapshot,
    CommandHistorySnapshot,
    ControlRoomSnapshot,
    HaulSessionSnapshot,
    MarketSnapshot,
    PromptStateSnapshot,
    ReplayBrowserSnapshot,
    ServerStatusSnapshot,
    SessionSnapshot,
    ShipSnapshot,
    TradeRouteSnapshot,
    TradeRoutesSnapshot,
    UiStateSnapshot,
)
from edap.runtime import ResolvedPath, RuntimeContext
from edap.timing import TimingChannelConfig, TimingConfig, TimingSampler


def _make_timing_config() -> TimingConfig:
    channel = TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.0)
    return TimingConfig(enabled=False, distribution="log_normal", delay=channel, hold=channel, typing=channel)


class _WidgetStyles:
    def __init__(self) -> None:
        self.display = "block"


class _FakeInputWidget:
    def __init__(self) -> None:
        self.disabled = False
        self.placeholder = ""
        self.value = ""
        self.cursor_position = 0


class _FakeStaticWidget:
    def __init__(self) -> None:
        self.updated = None
        self.styles = _WidgetStyles()

    def update(self, value) -> None:
        self.updated = value


class _FakeOptionListWidget:
    def __init__(self) -> None:
        self.highlighted = 0
        self.options: list[object] = []

    def clear_options(self) -> None:
        self.options = []

    def add_options(self, options: list[object]) -> None:
        self.options.extend(options)


class _FakeActivityWidget:
    def __init__(self) -> None:
        self.styles = _WidgetStyles()
        self.border_title = "ACTIVITY"
        self.auto_scroll = True
        self.writes: list[object] = []

    @property
    def auto_follow_paused(self) -> bool:
        return not self.auto_scroll

    def write(self, value, *_args, **_kwargs) -> None:
        self.writes.append(value)

    def clear(self) -> None:
        self.writes = []


class _FakeContainerWidget:
    def __init__(self) -> None:
        self.styles = _WidgetStyles()
        self.border_title = ""


class _KeyEvent:
    def __init__(self, key: str, *, character: str | None = None) -> None:
        self.key = key
        self.character = character
        self.prevented = False

    def prevent_default(self) -> None:
        self.prevented = True


def _bind_observer_widgets(app: ObserverControlRoomApp, command_input: _FakeInputWidget) -> None:
    activity = _FakeActivityWidget()
    trade_route_list = _FakeOptionListWidget()
    trade_route_help = _FakeStaticWidget()
    trade_route_detail = _FakeStaticWidget()
    trade_route_picker = _FakeContainerWidget()
    market_content = _FakeStaticWidget()
    main = _FakeContainerWidget()
    resume_detail = _FakeStaticWidget()
    resume_list = _FakeOptionListWidget()
    resume_browser = _FakeContainerWidget()
    resume_help = _FakeStaticWidget()

    def _query_one(selector, _type=None):
        widgets = {
            "#cmd": command_input,
            "#activity": activity,
            "#trade-route-list": trade_route_list,
            "#trade-route-help": trade_route_help,
            "#trade-route-detail": trade_route_detail,
            "#trade-route-picker": trade_route_picker,
            "#market-content": market_content,
            "#main": main,
            "#resume-detail": resume_detail,
            "#resume-list": resume_list,
            "#resume-browser": resume_browser,
            "#resume-help": resume_help,
        }
        return widgets[selector]

    app.query_one = _query_one  # type: ignore[method-assign]


def _make_observer_context() -> RuntimeContext:
    journal = ResolvedPath(
        configured={"path": None, "status": "not_configured", "reason": "test observer has no local journal"},
        auto_detected={"path": None, "status": "unsupported", "reason": "test observer has no local journal"},
        effective={"path": None, "status": "unsupported", "source": "auto_detected", "reason": "no path available"},
    )
    bindings = ResolvedPath(
        configured={"path": None, "status": "not_configured", "reason": "test observer has no local bindings"},
        auto_detected={"path": None, "status": "unsupported", "reason": "test observer has no local bindings"},
        effective={"path": None, "status": "unsupported", "source": "auto_detected", "reason": "no path available"},
    )
    return RuntimeContext(
        config=AppConfig(
            paths=PathsConfig(journal_dir=None, bindings_file=None),
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
                state_file=Path("/tmp/control-room-state.json"),
                history_limit=20,
                activity_log_max_lines=2000,
                command_delay_seconds=0.0,
            ),
            tts=TTSConfig(enabled=False),
        ),
        game_paths=None,
        journal=journal,
        bindings=bindings,
        input_controller=None,
        screen_capture=None,
        timing_sampler=TimingSampler(_make_timing_config()),
        binding_lookup=None,
        config_path=Path("/tmp/config.toml"),
        used_example_config_fallback=False,
    )


def _snapshot() -> ControlRoomSnapshot:
    return ControlRoomSnapshot(
        session=SessionSnapshot(session_id="observer-1", client_role="observer"),
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
            market_timestamp="2026-06-18T13:00:00Z",
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
                entry_id="activity-1",
                timestamp="2026-06-18T13:00:00Z",
                message_text="Observer ready",
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


def _data_read_model(*, system_name: str = "Sol") -> ControlRoomDataReadModel:
    return ControlRoomDataReadModel(
        ship=ShipState(system=system_name),
        market=MarketData(station="Galileo", system=system_name),
        haul_session=HaulStats(),
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
            session_id="observer-1",
            client_role="active_operator",
            client_name="observer-ipad",
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


def _websocket_connect_info(
    *,
    client_name: str = "observer-ipad",
    capabilities: dict[str, object] | None = None,
    prefer_authorization_header: bool = True,
) -> RemoteObserverWebSocketConnectInfo:
    return build_remote_observer_websocket_connect_info(
        websocket_url="ws://bridge.local:8765/session",
        access_token="secret-token",
        client_name=client_name,
        capabilities=capabilities or _current_remote_capabilities(),
        prefer_authorization_header=prefer_authorization_header,
    )


class ControlRoomClientTests(unittest.TestCase):
    @staticmethod
    def _target() -> ObserverServerTarget:
        return ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )

    @staticmethod
    def _backend(*, initial_snapshot: ControlRoomSnapshot | None = None) -> RemoteObserverBackend:
        return RemoteObserverBackend(
            server_target=ControlRoomClientTests._target(),
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=initial_snapshot or _snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )

    def _app(
        self,
        *,
        backend: RemoteObserverBackend | None = None,
        data_source: RemoteObserverDataSource | None = None,
    ) -> ObserverControlRoomApp:
        return ObserverControlRoomApp(
            _make_observer_context(),
            backend=backend or self._backend(),
            data_source=data_source,
            server_target=self._target(),
            client_name="observer-ipad",
        )

    def test_observer_app_initializes_without_local_journal_dir(self) -> None:
        app = self._app()

        self.assertIsNone(app._journal_dir)
        self.assertIsNone(app._market_path)

    def test_observer_app_refresh_remote_command_input_disables_observer_mode(self) -> None:
        backend = self._backend()
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        app._apply_view_snapshot_state()
        app._refresh_remote_command_input()

        self.assertTrue(command_input.disabled)
        self.assertEqual(command_input.placeholder, "observer mode - read only")

    def test_observer_app_starts_with_clean_command_input_from_remote_snapshot(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        command_input.disabled = True
        _bind_observer_widgets(app, command_input)

        app._apply_view_snapshot_state()
        app._refresh_remote_command_input()

        self.assertFalse(command_input.disabled)
        self.assertEqual(command_input.placeholder, app._default_command_placeholder)
        self.assertEqual(command_input.value, "")
        self.assertEqual(command_input.cursor_position, 0)

    def test_observer_app_preserves_freeform_command_draft_across_snapshot_refresh(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        app._apply_view_snapshot_state()
        command_input.value = "haul gold"
        command_input.cursor_position = 4
        app._local_command_input_value = command_input.value
        app._local_command_input_cursor_position = command_input.cursor_position

        refreshed_snapshot = replace(
            updated_snapshot,
            ship=replace(updated_snapshot.ship, system_name="Achenar"),
        )
        backend.publish_snapshot(refreshed_snapshot)
        app._view_snapshot = refreshed_snapshot
        app._apply_view_snapshot_state()
        app._refresh_remote_command_input()

        self.assertEqual(command_input.value, "haul gold")
        self.assertEqual(command_input.cursor_position, 4)
        self.assertEqual(command_input.placeholder, app._default_command_placeholder)

    def test_observer_app_ignores_legacy_snapshot_backend_events(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        app._apply_view_snapshot_state()
        command_input.value = "haul gold"
        app._local_command_input_value = command_input.value
        refreshed_snapshot = replace(
            updated_snapshot,
            ship=replace(updated_snapshot.ship, system_name="Achenar"),
        )

        app._apply_backend_event(SnapshotUpdatedEvent(snapshot=refreshed_snapshot))

        self.assertEqual(app._view_snapshot.ship.system_name, "Sol")
        self.assertEqual(command_input.value, "haul gold")

    def test_observer_app_preserves_prompt_draft_across_snapshot_refresh(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        app._apply_view_snapshot_state()
        app._prompt_state.command_input_prefill_active = True
        app._prompt_state.command_input_placeholder = "station 1 buying..."
        app._prompt_state.command_input_value = "Gold"
        app._sync_local_prompt_state()
        app._refresh_remote_command_input()

        command_input.value = "Gol"
        command_input.cursor_position = 1
        app._local_command_input_value = command_input.value
        app._local_command_input_cursor_position = command_input.cursor_position

        refreshed_snapshot = replace(
            updated_snapshot,
            market=replace(updated_snapshot.market, station_name="Galileo"),
        )
        backend.publish_snapshot(refreshed_snapshot)
        app._view_snapshot = refreshed_snapshot
        app._apply_view_snapshot_state()
        app._refresh_remote_command_input()

        self.assertEqual(command_input.placeholder, "station 1 buying...")
        self.assertEqual(command_input.value, "Gol")
        self.assertEqual(command_input.cursor_position, 1)

    def test_observer_app_tracks_latest_cursor_position_without_text_change(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        app._apply_view_snapshot_state()
        app._prompt_state.command_input_prefill_active = True
        app._prompt_state.command_input_placeholder = "edit Inara search params then press Enter..."
        app._prompt_state.haul_prompt_step = "search_edit"
        app._prompt_state.haul_prompt_mode = "search"
        app._prompt_state.command_input_value = "near_system='Sol'"
        app._sync_local_prompt_state()
        app._refresh_remote_command_input()

        command_input.value = "near_system='Sol'"
        command_input.cursor_position = 5
        app._local_command_input_value = command_input.value
        app._local_command_input_cursor_position = 14

        app.on_key(_KeyEvent("left"))

        self.assertEqual(app._local_command_input_cursor_position, 5)

        refreshed_snapshot = replace(
            updated_snapshot,
            market=replace(updated_snapshot.market, station_name="Galileo"),
        )
        app._view_snapshot = refreshed_snapshot
        app._apply_view_snapshot_state()
        app._refresh_remote_command_input()

        self.assertEqual(command_input.value, "near_system='Sol'")
        self.assertEqual(command_input.cursor_position, 5)

    def test_observer_app_syncs_live_prompt_text_into_local_prompt_state(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        app._apply_view_snapshot_state()
        app._prompt_state.command_input_prefill_active = True
        app._prompt_state.command_input_placeholder = "station 1 buying..."
        app._prompt_state.command_input_value = "Gold"
        app._prompt_state.haul_prompt_step = "station_1_buying"
        command_input.value = "Gold ore"
        command_input.cursor_position = 4
        app._local_prompt_prefill_signature = app._prompt_prefill_signature()

        app._sync_local_prompt_state()

        self.assertIsNotNone(app._local_prompt_state)
        self.assertEqual(app._local_prompt_state.command_input_value, "Gold ore")
        self.assertEqual(app._prompt_state.command_input_value, "Gold ore")

    def test_observer_app_keeps_new_prompt_prefill_when_widget_is_still_blank(self) -> None:
        backend = self._backend(
            initial_snapshot=replace(
                _snapshot(),
                session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            )
        )
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        app._prompt_state.command_input_prefill_active = True
        app._prompt_state.command_input_placeholder = "edit Inara search params then press Enter..."
        app._prompt_state.haul_prompt_step = "search_edit"
        app._prompt_state.haul_prompt_mode = "search"
        app._prompt_state.command_input_value = "near_system='Sol'"
        command_input.value = ""
        app._local_prompt_prefill_signature = (False, "", "")

        app._sync_local_prompt_state()

        self.assertIsNotNone(app._local_prompt_state)
        self.assertEqual(app._local_prompt_state.command_input_value, "near_system='Sol'")
        self.assertEqual(app._prompt_state.command_input_value, "near_system='Sol'")

    def test_observer_app_preserves_local_activity_entries_across_snapshot_refresh(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            activity_log=[
                ActivityLogEntry(
                    entry_id="remote-1",
                    timestamp="2026-06-30T13:54:34Z",
                    message_text="[dim]Unknown command: dest sol[/]",
                )
            ],
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        activity = app.query_one("#activity")

        app._apply_view_snapshot_state()
        app._replace_activity_log(updated_snapshot.activity_log)
        app._log("[bold]dest[/] - dest <system>")
        self.assertEqual(len(activity.writes), 2)

        refreshed_snapshot = replace(
            updated_snapshot,
            ship=replace(updated_snapshot.ship, system_name="Achenar"),
        )
        backend.publish_snapshot(refreshed_snapshot)
        app._view_snapshot = refreshed_snapshot
        app._apply_view_snapshot_state()
        app._replace_activity_log(refreshed_snapshot.activity_log)

        rendered_messages = [segment.plain for segment in activity.writes]
        self.assertTrue(
            any("Unknown command: dest sol" in message for message in rendered_messages)
        )
        self.assertTrue(any("dest - dest <system>" in message for message in rendered_messages))
        self.assertIn("13:54:34  Unknown command: dest sol", rendered_messages[0])
        self.assertIn("dest - dest <system>", rendered_messages[-1])

    def test_observer_app_sorts_local_and_remote_activity_by_timestamp_on_refresh(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            activity_log=[
                ActivityLogEntry(
                    entry_id="remote-1",
                    timestamp="2026-06-30T15:57:35Z",
                    message_text="[dim]Executing dest sol in 5.0s...[/]",
                ),
                ActivityLogEntry(
                    entry_id="remote-2",
                    timestamp="2026-06-30T15:57:38Z",
                    message_text="[yellow]Remote Ctrl-C received — cancelling active routine.[/]",
                ),
                ActivityLogEntry(
                    entry_id="remote-3",
                    timestamp="2026-06-30T15:57:38Z",
                    message_text="[yellow]Cancelled pending dest sol before execution.[/]",
                ),
            ],
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        activity = app.query_one("#activity")

        app._local_activity_log = [
            ActivityLogEntry(
                entry_id="local-1",
                timestamp="2026-06-30T15:57:34Z",
                message_text="[dim]Command: dest sol[/]",
            ),
            ActivityLogEntry(
                entry_id="local-2",
                timestamp="2026-06-30T15:57:34Z",
                message_text="Destination: [bold]sol[/]",
            ),
            ActivityLogEntry(
                entry_id="local-3",
                timestamp="2026-06-30T15:57:34Z",
                message_text="[dim]Galaxy-map settle seconds? (Enter = 2.0)[/]",
            ),
        ]

        app._replace_activity_log(updated_snapshot.activity_log)

        rendered_messages = [segment.plain for segment in activity.writes]
        self.assertEqual(
            rendered_messages,
            [
                "15:57:34  Command: dest sol",
                "15:57:34  Destination: sol",
                "15:57:34  Galaxy-map settle seconds? (Enter = 2.0)",
                "15:57:35  Executing dest sol in 5.0s...",
                "15:57:38  Remote Ctrl-C received — cancelling active routine.",
                "15:57:38  Cancelled pending dest sol before execution.",
            ],
        )

    def test_observer_app_uses_event_timestamp_for_incremental_activity_append(self) -> None:
        backend = self._backend(initial_snapshot=_snapshot())
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        activity = app.query_one("#activity")

        app._apply_backend_event(
            ActivityLogAppendedEvent(
                entry=ActivityLogEntry(
                    entry_id="remote-2",
                    timestamp="2026-06-30T16:44:02Z",
                    message_text="[dim]Executing dest sol in 5.0s...[/]",
                )
            )
        )

        self.assertEqual(
            activity.writes[-1].plain,
            "16:44:02  Executing dest sol in 5.0s...",
        )

    def test_observer_app_replay_browser_runs_locally_from_remote_history(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            command_history=CommandHistorySnapshot(
                history_entries=[
                    CommandHistoryEntrySnapshot(
                        raw_command="haul Silver",
                        command_name="haul",
                        arguments={
                            "station_1_buying": "Silver",
                            "station_1": "Savitskaya Orbital",
                            "station_1_system": "TSONGORIS",
                            "station_2": "Nyberg Vision",
                            "station_2_system": "NJOKUJINUN",
                        },
                        timestamp="2026-06-30T12:00:00Z",
                    )
                ],
                history_limit=20,
            ),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        app.set_focus = lambda _widget: None  # type: ignore[method-assign]

        app._apply_view_snapshot_state()
        app._show_resume_picker()

        self.assertTrue(app._resume_open)
        self.assertEqual(len(app._resume_entries), 1)
        self.assertTrue(backend._outgoing_messages.empty())

        app._resume_edit_selected()

        self.assertEqual(app._haul_prompt_step, "station_1_buying")
        self.assertEqual(command_input.value, "Silver")
        self.assertEqual(
            app._prompt_state.haul_prompt_defaults["station_2"],
            "Nyberg Vision",
        )
        self.assertTrue(backend._outgoing_messages.empty())

    def test_observer_app_replay_filter_runs_locally(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            command_history=CommandHistorySnapshot(
                history_entries=[
                    CommandHistoryEntrySnapshot(
                        raw_command="haul Silver",
                        command_name="haul",
                        arguments={"station_1_buying": "Silver"},
                        timestamp="2026-06-30T12:00:00Z",
                    ),
                    CommandHistoryEntrySnapshot(
                        raw_command="dest Achenar",
                        command_name="dest",
                        arguments={"destination": "Achenar", "galaxy_map_settle": 2.0},
                        timestamp="2026-06-30T12:01:00Z",
                    ),
                ],
                history_limit=20,
            ),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        app.set_focus = lambda _widget: None  # type: ignore[method-assign]

        app._apply_view_snapshot_state()
        app._show_resume_picker()
        app._resume_filter = "dest"
        app._refresh_resume_picker()

        self.assertEqual(len(app._resume_entries), 1)
        self.assertEqual(app._resume_entries[0].entry.raw, "dest Achenar")
        self.assertTrue(backend._outgoing_messages.empty())

    def test_observer_app_replay_command_runs_locally(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            command_history=CommandHistorySnapshot(
                history_entries=[
                    CommandHistoryEntrySnapshot(
                        raw_command="haul Silver",
                        command_name="haul",
                        arguments={"station_1_buying": "Silver"},
                        timestamp="2026-06-30T12:00:00Z",
                    )
                ],
                history_limit=20,
            ),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        app.set_focus = lambda _widget: None  # type: ignore[method-assign]

        class _Submitted:
            def __init__(self, value: str) -> None:
                self.value = value
                self.input = type("_Input", (), {"value": value})()

        app._apply_view_snapshot_state()
        app.on_input_submitted(_Submitted("replay"))

        self.assertTrue(app._resume_open)
        self.assertTrue(any(entry.entry.raw == "haul Silver" for entry in app._resume_entries))
        self.assertTrue(backend._outgoing_messages.empty())

    def test_observer_app_market_lock_unlock_are_local_display_controls(self) -> None:
        initial_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            market=MarketSnapshot(
                station_name="Jameson Memorial",
                system_name="Sol",
                market_timestamp="2026-06-30T12:00:00Z",
                items=[{"Name": "gold", "Stock": 42}],
            ),
        )
        backend = self._backend(initial_snapshot=initial_snapshot)
        data_source = RemoteObserverDataSource(
            replace(
                _data_read_model(system_name="Sol"),
                market=MarketData(
                    station="Jameson Memorial",
                    system="Sol",
                    timestamp="2026-06-30T12:00:00Z",
                    items=[{"Name": "gold", "Stock": 42}],
                ),
            )
        )
        app = self._app(backend=backend, data_source=data_source)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        class _Submitted:
            def __init__(self, value: str) -> None:
                self.value = value
                self.input = type("_Input", (), {"value": value})()

        app._apply_view_snapshot_state()
        app._sync_presented_market_from_snapshot(force=True)
        self.assertEqual(app._view_market_data().station, "Jameson Memorial")

        app.on_input_submitted(_Submitted("market lock"))
        self.assertTrue(app._market.locked)
        self.assertTrue(backend._outgoing_messages.empty())

        updated_snapshot = replace(
            initial_snapshot,
            market=MarketSnapshot(
                station_name="Galileo",
                system_name="Sol",
                market_timestamp="2026-06-30T12:01:00Z",
                items=[{"Name": "silver", "Stock": 99}],
            ),
        )
        data_source.hydrate(
            replace(
                data_source.current(),
                market=MarketData(
                    station="Galileo",
                    system="Sol",
                    timestamp="2026-06-30T12:01:00Z",
                    items=[{"Name": "silver", "Stock": 99}],
                ),
            )
        )
        backend.publish_snapshot(updated_snapshot)
        app._view_snapshot = updated_snapshot
        app._apply_view_snapshot_state()
        self.assertEqual(app._view_market_data().station, "Jameson Memorial")
        self.assertEqual(app._view_market_data().items[0]["Name"], "gold")

        app.on_input_submitted(_Submitted("market unlock"))
        self.assertFalse(app._market.locked)
        self.assertEqual(app._view_market_data().station, "Galileo")
        self.assertEqual(app._view_market_data().items[0]["Name"], "silver")
        self.assertTrue(backend._outgoing_messages.empty())

    def test_observer_app_ignores_remote_trade_routes_snapshot(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            trade_routes=TradeRoutesSnapshot(
                system_name="Praea Euq AK-A d25",
                query_url="https://inara.cz/elite/market-traderoutes/?ps1=Praea+Euq+AK-A+d25",
                searched_at="2026-06-22T11:00:00Z",
                routes=[
                    TradeRouteSnapshot(
                        index=1,
                        from_station="Savitskaya Orbital",
                        from_system="TSONGORIS",
                        to_station="Scully-Power Station",
                        to_system="IX",
                        source_buy_commodity="Silver",
                        from_station_distance="82 Ls",
                        to_station_distance="5 Ls",
                        distance_from_system="~167 Ly",
                        route_distance="33.08 Ly",
                        profit_per_unit="45,510 Cr",
                        profit_per_hour="88,323,553 Cr",
                        updated="3 hours ago",
                    )
                ],
            ),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)

        app._apply_view_snapshot_state()

        self.assertEqual(app._trade_routes.system_name, "")
        self.assertEqual(app._trade_routes.routes, [])
        self.assertFalse(app._trade_route_picker_open)
        self.assertIsNone(app._selected_trade_route_index)

    def test_observer_app_keeps_local_trade_routes_across_remote_snapshot_updates(self) -> None:
        backend = self._backend()
        app = self._app(backend=backend)
        app._local_trade_routes = TradeRoutesData(
            system_name="Praea Euq AK-A d25",
            query_url="https://inara.cz/elite/market-traderoutes/?ps1=Praea+Euq+AK-A+d25",
            searched_at="2026-06-28T21:00:00Z",
            routes=[
                TradeRoute(
                    index=1,
                    from_station="Savitskaya Orbital",
                    from_system="TSONGORIS",
                    to_station="Scully-Power Station",
                    to_system="IX",
                    source_buy_commodity="Silver",
                )
            ],
        )
        app._local_trade_route_picker = TradeRoutePickerState(
            open=True,
            selected_route_index=1,
            presented_query_url=app._local_trade_routes.query_url,
            presented_searched_at=app._local_trade_routes.searched_at,
        )

        app._apply_view_snapshot_state()
        self.assertEqual(app._trade_routes.system_name, "Praea Euq AK-A d25")

        app._view_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
        )
        app._apply_view_snapshot_state()

        self.assertEqual(app._trade_routes.system_name, "Praea Euq AK-A d25")
        self.assertEqual(len(app._trade_routes.routes), 1)
        self.assertTrue(app._trade_route_picker_open)
        self.assertEqual(app._selected_trade_route_index, 1)

    def test_observer_app_handles_haul_search_locally(self) -> None:
        backend = self._backend(
            initial_snapshot=replace(
                _snapshot(),
                session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
                ship=replace(_snapshot().ship, cargo_capacity=460),
            )
        )
        app = self._app(backend=backend)
        app._ship.system = "Praea Euq AK-A d25"
        app._controls = object()
        app._run_in_thread = lambda fn: fn()
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)  # type: ignore[method-assign]

        result = TradeRouteSearchResult(
            system_name="Praea Euq AK-A d25",
            query_url="https://inara.cz/elite/market-traderoutes/?ps1=Praea+Euq+AK-A+d25",
            searched_at="2026-06-28T22:00:00Z",
            routes=(
                TradeRoute(
                    index=1,
                    from_station="Savitskaya Orbital",
                    from_system="TSONGORIS",
                    to_station="Scully-Power Station",
                    to_system="IX",
                    source_buy_commodity="Silver",
                ),
            ),
        )

        class _Submitted:
            def __init__(self, value: str) -> None:
                self.value = value
                self.input = type("_Input", (), {"value": value})()

        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        with patch("edap.control_room.client.connect.search_trade_routes", return_value=result):
            app.on_input_submitted(_Submitted("haul search Praea Euq AK-A d25"))
            self.assertEqual(app._prompt_state.haul_prompt_mode, "search")
            self.assertEqual(app._haul_prompt_step, "search_edit")
            self.assertIn("cargo_capacity=460", command_input.value)
            app.on_input_submitted(_Submitted(command_input.value))

        self.assertEqual(app._trade_routes.system_name, "Praea Euq AK-A d25")
        self.assertEqual(len(app._trade_routes.routes), 1)
        self.assertTrue(app._trade_route_picker_open)
        self.assertEqual(app._selected_trade_route_index, 1)
        self.assertEqual(app._prompt_state.haul_prompt_mode, "")
        self.assertEqual(app._haul_prompt_step, "")
        self.assertEqual(command_input.value, "")
        self.assertEqual(command_input.placeholder, app._default_command_placeholder)

    def test_observer_app_keeps_haul_search_prefill_when_local_command_submits(self) -> None:
        backend = self._backend(
            initial_snapshot=replace(
                _snapshot(),
                session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
                ship=replace(_snapshot().ship, cargo_capacity=460),
            )
        )
        app = self._app(backend=backend)
        app._ship.system = "Praea Euq AK-A d25"
        app._controls = object()
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        class _Submitted:
            def __init__(self, value: str, widget: _FakeInputWidget) -> None:
                self.value = value
                self.input = widget

        app.on_input_submitted(_Submitted("haul search Praea Euq AK-A d25", command_input))

        self.assertEqual(app._prompt_state.haul_prompt_mode, "search")
        self.assertEqual(app._haul_prompt_step, "search_edit")
        self.assertTrue(command_input.value)
        self.assertIn("near_system='Praea Euq AK-A d25'", command_input.value)
        self.assertIn("cargo_capacity=460", command_input.value)

    def test_observer_app_uses_remote_snapshot_context_for_bare_haul_search(self) -> None:
        backend = self._backend(
            initial_snapshot=replace(
                _snapshot(),
                session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
                ship=replace(_snapshot().ship, system_name="Zeta Trianguli Australis", cargo_capacity=461),
            )
        )
        app = self._app(backend=backend)
        app._controls = object()
        app._run_in_thread = lambda fn: fn()
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)  # type: ignore[method-assign]

        result = TradeRouteSearchResult(
            system_name="Zeta Trianguli Australis",
            query_url="https://inara.cz/elite/market-traderoutes/?ps1=Zeta+Trianguli+Australis",
            searched_at="2026-06-29T07:00:00Z",
            routes=(
                TradeRoute(
                    index=1,
                    from_station="Savitskaya Orbital",
                    from_system="TSONGORIS",
                    to_station="Scully-Power Station",
                    to_system="IX",
                    source_buy_commodity="Silver",
                ),
            ),
        )

        class _Submitted:
            def __init__(self, value: str) -> None:
                self.value = value
                self.input = type("_Input", (), {"value": value})()

        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        with patch("edap.control_room.client.connect.search_trade_routes", return_value=result):
            app.on_input_submitted(_Submitted("haul search"))
            self.assertEqual(app._prompt_state.haul_prompt_mode, "search")
            self.assertEqual(app._haul_prompt_step, "search_edit")
            self.assertIn("near_system='Zeta Trianguli Australis'", command_input.value)
            self.assertIn("cargo_capacity=461", command_input.value)
            app.on_input_submitted(_Submitted(command_input.value))

        self.assertEqual(app._trade_routes.system_name, "Zeta Trianguli Australis")
        self.assertEqual(len(app._trade_routes.routes), 1)
        self.assertTrue(app._trade_route_picker_open)
        self.assertEqual(app._selected_trade_route_index, 1)
        self.assertEqual(app._prompt_state.haul_prompt_mode, "")
        self.assertEqual(app._haul_prompt_step, "")
        self.assertEqual(command_input.value, "")
        self.assertEqual(command_input.placeholder, app._default_command_placeholder)

    def test_observer_app_loads_selected_local_trade_route_into_local_prompt(self) -> None:
        backend = self._backend(
            initial_snapshot=replace(
                _snapshot(),
                session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            )
        )
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        app._local_trade_routes = TradeRoutesData(
            system_name="Praea Euq AK-A d25",
            routes=[
                TradeRoute(
                    index=2,
                    from_station="Savitskaya Orbital",
                    from_system="TSONGORIS",
                    to_station="Nyberg Vision",
                    to_system="NJOKUJINUN",
                    source_buy_commodity="Beryllium",
                )
            ],
        )
        app._local_trade_route_picker = TradeRoutePickerState(open=True, selected_route_index=2)
        app._apply_view_snapshot_state()

        app._load_selected_trade_route()

        self.assertTrue(app._prompt_state.haul_prompt_step)
        self.assertEqual(app._haul_prompt_step, "station_1_buying")
        self.assertEqual(command_input.value, "Beryllium")
        self.assertEqual(app._prompt_state.haul_prompt_defaults["station_1"], "Savitskaya Orbital")
        self.assertEqual(app._prompt_state.haul_prompt_defaults["station_2"], "Nyberg Vision")
        self.assertEqual(app._prompt_state.haul_prompt_defaults["station_1_buying"], "Beryllium")
        self.assertFalse(app._local_trade_route_picker.open)
        self.assertFalse(app._trade_route_picker_open)

    def test_observer_app_handles_dest_command_locally_then_dispatches_remote(self) -> None:
        backend = self._backend(
            initial_snapshot=replace(
                _snapshot(),
                session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            )
        )
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        class _Submitted:
            def __init__(self, value: str) -> None:
                self.value = value
                self.input = type("_Input", (), {"value": value})()

        app.on_input_submitted(_Submitted("dest Achenar"))
        self.assertEqual(app._dest_prompt_destination, "Achenar")
        self.assertTrue(backend._outgoing_messages.empty())

        app.on_input_submitted(_Submitted("3.5"))
        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.dispatch_destination")
        self.assertEqual(message["payload"]["destination"], "Achenar")
        self.assertEqual(message["payload"]["galaxy_map_settle"], 3.5)
        self.assertEqual(message["payload"]["raw_command"], "dest Achenar")

    def test_observer_app_enter_on_dest_prompt_uses_default_locally(self) -> None:
        backend = self._backend(
            initial_snapshot=replace(
                _snapshot(),
                session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            )
        )
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        class _Submitted:
            def __init__(self, value: str) -> None:
                self.value = value
                self.input = type("_Input", (), {"value": value, "id": "cmd"})()

        app.on_input_submitted(_Submitted("dest Sol"))
        command_input.value = ""

        event = _KeyEvent("enter")
        app.on_key(event)

        self.assertTrue(event.prevented)
        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.dispatch_destination")
        self.assertEqual(message["payload"]["destination"], "Sol")
        self.assertEqual(message["payload"]["galaxy_map_settle"], 2.0)
        self.assertEqual(message["payload"]["raw_command"], "dest Sol")
        self.assertTrue(backend._outgoing_messages.empty())

    def test_observer_app_handles_haul_prompt_locally_then_dispatches_remote(self) -> None:
        backend = self._backend(
            initial_snapshot=replace(
                _snapshot(),
                session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
                ship=replace(
                    _snapshot().ship,
                    system_name="TSONGORIS",
                    station_name="Savitskaya Orbital",
                ),
            )
        )
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)

        class _Submitted:
            def __init__(self, value: str) -> None:
                self.value = value
                self.input = type("_Input", (), {"value": value})()

        app.on_input_submitted(_Submitted("haul Silver"))
        self.assertTrue(app._haul_prompt_step)
        self.assertTrue(backend._outgoing_messages.empty())

        app.on_input_submitted(_Submitted("Savitskaya Orbital"))
        app.on_input_submitted(_Submitted("TSONGORIS"))
        app.on_input_submitted(_Submitted(""))
        app.on_input_submitted(_Submitted(""))
        app.on_input_submitted(_Submitted("Nyberg Vision"))
        app.on_input_submitted(_Submitted("NJOKUJINUN"))
        app.on_input_submitted(_Submitted(""))
        app.on_input_submitted(_Submitted(""))
        app.on_input_submitted(_Submitted(""))
        app.on_input_submitted(_Submitted(""))

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.dispatch_haul_loop")
        self.assertEqual(message["payload"]["params"]["station_1_buying"], "Silver")
        self.assertEqual(message["payload"]["params"]["station_1"], "Savitskaya Orbital")
        self.assertEqual(message["payload"]["params"]["station_2"], "Nyberg Vision")
        self.assertEqual(message["payload"]["raw_command"], "haul Silver")

    def test_parse_target_defaults_to_http_and_default_port(self) -> None:
        target = parse_observer_server_target("192.168.1.44")

        self.assertEqual(target.host, "192.168.1.44")
        self.assertEqual(target.port, 8765)
        self.assertEqual(target.http_base_url, "http://192.168.1.44:8765")
        self.assertEqual(target.websocket_url, "ws://192.168.1.44:8765/session")

    def test_parse_target_keeps_explicit_https_port(self) -> None:
        target = parse_observer_server_target("https://bridge.local:9443")

        self.assertEqual(target.host, "bridge.local")
        self.assertEqual(target.port, 9443)
        self.assertEqual(target.http_base_url, "https://bridge.local:9443")
        self.assertEqual(target.websocket_url, "wss://bridge.local:9443/session")

    def test_remote_backend_updates_cached_snapshot(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        snapshot = _snapshot()
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=snapshot,
            websocket_connect_info=_websocket_connect_info(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)

        updated_snapshot = ControlRoomSnapshot(
            session=snapshot.session,
            connected_clients=snapshot.connected_clients,
            active_operator=snapshot.active_operator,
            ship=ShipSnapshot(**{**asdict(snapshot.ship), "system_name": "Achenar"}),
            market=snapshot.market,
            haul_session=snapshot.haul_session,
            ui_state=snapshot.ui_state,
            command_history=snapshot.command_history,
            activity_log=snapshot.activity_log,
            server_status=snapshot.server_status,
        )

        backend.publish_snapshot(updated_snapshot)

        self.assertEqual(backend.current_snapshot().ship.system_name, "Achenar")
        self.assertIsInstance(received[0], SnapshotUpdatedEvent)

    def test_remote_backend_surfaces_response_error_messages(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)

        backend._handle_response_message(
            {
                "message_type": "response.error",
                "payload": {"error_message": "Observer clients cannot issue operator commands."},
            }
        )

        self.assertIsInstance(received[0], ActivityLogAppendedEvent)
        self.assertEqual(
            received[0].entry.message_text,
            "Observer clients cannot issue operator commands.",
        )

    def test_remote_backend_enqueues_submit_input(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )

        backend.dispatch_command("dock")

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.submit_input")
        self.assertEqual(message["payload"]["raw_input"], "dock")

    def test_remote_backend_does_not_enqueue_client_local_submit_input(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )

        backend.submit_input("dest sol")
        backend.dispatch_command("home")
        backend.submit_input("market lock")

        self.assertTrue(backend._outgoing_messages.empty())

    def test_remote_backend_load_trade_route_stays_client_local(self) -> None:
        backend = self._backend()
        received: list[object] = []
        backend.subscribe_events(received.append)

        backend.load_trade_route(
            TradeRoute(
                index=2,
                from_station="Savitskaya Orbital",
                from_system="TSONGORIS",
                to_station="Nyberg Vision",
                to_system="NJOKUJINUN",
                source_buy_commodity="Beryllium",
            ),
            raw_command="haul route Savitskaya Orbital -> Nyberg Vision",
        )

        self.assertTrue(backend._outgoing_messages.empty())
        self.assertIsInstance(received[0], ActivityLogAppendedEvent)
        self.assertEqual(received[0].entry.message_text, "Observer route loading is client-local.")

    def test_remote_backend_enqueues_dispatch_destination_and_haul_loop(self) -> None:
        backend = self._backend()

        backend.dispatch_destination(
            "Achenar",
            3.5,
            skip_delay=True,
            raw_command="!dest Achenar",
        )
        backend.dispatch_haul_loop(
            params={"station_1_buying": "Silver", "station_1": "Savitskaya Orbital"},
            raw_command="haul Silver",
        )

        destination_message = backend._outgoing_messages.get_nowait()
        haul_message = backend._outgoing_messages.get_nowait()
        self.assertEqual(destination_message["message_type"], "command.dispatch_destination")
        self.assertEqual(destination_message["payload"]["destination"], "Achenar")
        self.assertEqual(destination_message["payload"]["galaxy_map_settle"], 3.5)
        self.assertTrue(destination_message["payload"]["skip_delay"])
        self.assertEqual(haul_message["message_type"], "command.dispatch_haul_loop")
        self.assertEqual(haul_message["payload"]["params"]["station_1_buying"], "Silver")
        self.assertEqual(haul_message["payload"]["raw_command"], "haul Silver")

    def test_remote_execution_delegates_to_remote_backend(self) -> None:
        backend = self._backend()
        execution = RemoteObserverExecution(backend)

        execution.submit_command("jump", skip_delay=True)
        execution.dispatch_destination("Achenar", 3.5, raw_command="dest Achenar")
        execution.dispatch_haul_loop(params={"station_1_buying": "Silver"}, raw_command="haul")

        command_message = backend._outgoing_messages.get_nowait()
        destination_message = backend._outgoing_messages.get_nowait()
        haul_message = backend._outgoing_messages.get_nowait()

        self.assertEqual(command_message["message_type"], "command.submit_input")
        self.assertEqual(command_message["payload"]["raw_input"], "jump")
        self.assertEqual(command_message["payload"]["skip_delay"], True)
        self.assertEqual(destination_message["message_type"], "command.dispatch_destination")
        self.assertEqual(destination_message["payload"]["destination"], "Achenar")
        self.assertEqual(haul_message["message_type"], "command.dispatch_haul_loop")
        self.assertEqual(haul_message["payload"]["params"]["station_1_buying"], "Silver")

    def test_remote_data_source_hydrates_current_read_model(self) -> None:
        data_source = RemoteObserverDataSource(_data_read_model(system_name="Sol"))

        data_source.hydrate(_data_read_model(system_name="Achenar"))

        self.assertEqual(data_source.current().ship.system, "Achenar")

    def test_initial_remote_snapshot_is_derived_from_hydrate_data(self) -> None:
        data = _data_read_model(system_name="Achenar")

        snapshot = initial_remote_snapshot_from_data(data, client_name="observer-ipad")

        self.assertEqual(snapshot.ship.system_name, "Achenar")
        self.assertEqual(snapshot.session.session_id, data.session.session_id)
        self.assertEqual(
            snapshot.command_history.history_limit,
            data.command_history.history_limit,
        )
        self.assertEqual(snapshot.server_status.operator_mode, data.server_status.operator_mode)

    def test_remote_backend_hydrates_data_source_from_data_message(self) -> None:
        data_source = RemoteObserverDataSource(_data_read_model(system_name="Sol"))
        backend = self._backend()
        backend._data_source = data_source
        events: list[object] = []
        backend.subscribe_events(events.append)

        handled = backend._handle_data_message(
            hydrate_message(_data_read_model(system_name="Achenar"))
        )

        self.assertTrue(handled)
        self.assertEqual(data_source.current().ship.system, "Achenar")
        self.assertIsInstance(events[0], DataUpdatedEvent)
        self.assertEqual(events[0].data.ship.system, "Achenar")

    def test_observer_app_installs_remote_data_source_dependency(self) -> None:
        backend = self._backend()
        data_source = RemoteObserverDataSource(_data_read_model(system_name="Achenar"))

        app = self._app(backend=backend)
        self.assertNotEqual(app.dependencies.data_source.current().ship.system, "Achenar")

        app = ObserverControlRoomApp(
            _make_observer_context(),
            backend=backend,
            data_source=data_source,
            server_target=self._target(),
            client_name="observer-ipad",
        )

        self.assertIs(app.dependencies.data_source, data_source)
        self.assertEqual(app.dependencies.data_source.current().ship.system, "Achenar")

    def test_remote_backend_replay_commands_stay_client_local(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)

        backend.open_replay_browser()
        backend.set_replay_filter("haul")
        backend.move_replay_selection(1)
        backend.replay_history_entry(
            entry=type("Entry", (), {
                "raw": "haul gold",
                "command": "haul",
                "params": {"station_1_buying": "gold"},
                "timestamp": "2026-06-18T13:00:00Z",
            })(),
            edit=True,
            skip_delay=True,
        )
        backend.toggle_replay_default_haul(
            type("Entry", (), {
                "raw": "haul gold",
                "command": "haul",
                "params": {"station_1_buying": "gold"},
                "timestamp": "2026-06-18T13:00:00Z",
            })()
        )
        backend.close_replay_browser()

        self.assertTrue(backend._outgoing_messages.empty())
        messages = [
            event.entry.message_text
            for event in received
            if isinstance(event, ActivityLogAppendedEvent)
        ]
        self.assertEqual(
            messages,
            [
                "Observer replay browser is client-local.",
                "Observer replay browser is client-local.",
                "Observer replay browser is client-local.",
                "Observer replay browser is client-local.",
                "Observer replay browser is client-local.",
                "Observer replay browser is client-local.",
            ],
        )

    def test_remote_backend_preserves_cached_snapshot_on_connection_loss(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        snapshot = ControlRoomSnapshot(
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            connected_clients=[],
            active_operator=ActiveOperatorSnapshot(
                session_id="observer-1",
                client_name="observer-ipad",
            ),
            ship=_snapshot().ship,
            market=_snapshot().market,
            haul_session=_snapshot().haul_session,
            ui_state=UiStateSnapshot(
                routine_active=True,
                active_routine_name="dock",
                haul_stop_requested=False,
                verbose_controls=False,
                instant_mode=False,
                activity_auto_follow_paused=False,
                shutdown_requested=False,
                shutdown_finalized=False,
            ),
            command_history=_snapshot().command_history,
            activity_log=_snapshot().activity_log,
            server_status=_snapshot().server_status,
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=snapshot,
            websocket_connect_info=_websocket_connect_info(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)
        backend._has_connected_once = True

        backend._handle_connection_lost("Observer connection lost: ping timeout")

        current = backend.current_snapshot()
        self.assertEqual(current.connected_clients, [])
        self.assertEqual(current.active_operator, snapshot.active_operator)
        self.assertTrue(current.ui_state.routine_active)
        self.assertEqual(current.ui_state.active_routine_name, "dock")
        self.assertIsInstance(received[0], ActivityLogAppendedEvent)
        self.assertEqual(received[0].entry.message_text, "Observer connection lost: ping timeout")

    def test_remote_backend_rejects_commands_when_disconnected(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)
        backend._has_connected_once = True

        backend.dispatch_command("dock")

        self.assertTrue(backend._outgoing_messages.empty())
        self.assertIsInstance(received[0], ActivityLogAppendedEvent)
        self.assertEqual(received[0].entry.message_text, "Observer connection unavailable.")

    def test_remote_backend_reconnect_delay_doubles_and_caps(self) -> None:
        backend = RemoteObserverBackend(
            server_target=ObserverServerTarget(
                host="bridge.local",
                port=8765,
                http_base_url="http://bridge.local:8765",
                websocket_url="ws://bridge.local:8765/session",
            ),
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )

        self.assertEqual(backend._next_reconnect_delay(1.0), 2.0)
        self.assertEqual(backend._next_reconnect_delay(2.0), 4.0)
        self.assertEqual(backend._next_reconnect_delay(16.0), 30.0)
        self.assertEqual(backend._next_reconnect_delay(30.0), 30.0)

    def test_remote_backend_logs_reconnect_backoff_and_restore(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)
        backend._has_connected_once = True

        backend._handle_connection_lost("Observer connection lost: ping timeout")
        backend._emit_local_message("Reconnecting in 1.0s...")
        backend._connected = True
        backend._emit_local_message("Observer connection restored.")

        messages = [
            event.entry.message_text
            for event in received
            if isinstance(event, ActivityLogAppendedEvent)
        ]
        self.assertIn("Observer connection lost: ping timeout", messages)
        self.assertIn("Reconnecting in 1.0s...", messages)
        self.assertIn("Observer connection restored.", messages)
        self.assertTrue(backend._outgoing_messages.empty())

    def test_remote_backend_enqueues_active_operator_claim(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )

        backend.request_active_operator()

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.request_active_operator")

    def test_remote_backend_enqueues_cancel_active_routine(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
            websocket_connect_info=_websocket_connect_info(),
        )

        backend.interrupt_active_routine()

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.cancel_active_routine")

    def test_validate_remote_capabilities_accepts_current_server_surface(self) -> None:
        capabilities = _current_remote_capabilities()

        _validate_remote_observer_capabilities(
            capabilities,
            ObserverServerTarget(
                host="bridge.local",
                port=8765,
                http_base_url="http://bridge.local:8765",
                websocket_url="ws://bridge.local:8765/session",
            ),
        )

    def test_validate_remote_capabilities_rejects_missing_message_types(self) -> None:
        capabilities = _current_remote_capabilities()
        capabilities["supported_message_types"] = ["state.snapshot", "response.success", "response.error"]

        with self.assertRaises(SystemExit) as ctx:
            _validate_remote_observer_capabilities(
                capabilities,
                ObserverServerTarget(
                    host="bridge.local",
                    port=8765,
                    http_base_url="http://bridge.local:8765",
                    websocket_url="ws://bridge.local:8765/session",
                ),
            )

        self.assertIn("does not support required message types", str(ctx.exception))

    def test_websocket_connect_info_prefers_authorization_header_for_native_clients(self) -> None:
        connect_info = _websocket_connect_info()

        self.assertEqual(
            connect_info.session_url,
            "ws://bridge.local:8765/session?client_name=observer-ipad",
        )
        self.assertEqual(
            connect_info.additional_headers,
            (("Authorization", "Bearer secret-token"),),
        )

    def test_websocket_connect_info_can_use_query_parameter_when_requested(self) -> None:
        connect_info = _websocket_connect_info(prefer_authorization_header=False)

        self.assertEqual(
            connect_info.session_url,
            "ws://bridge.local:8765/session?client_name=observer-ipad&access_token=secret-token",
        )
        self.assertEqual(connect_info.additional_headers, ())

    def test_validate_remote_capabilities_rejects_missing_command_breakdown(self) -> None:
        capabilities = _current_remote_capabilities()
        capabilities["supported_command_message_types"] = ["command.request_snapshot"]

        with self.assertRaises(SystemExit) as ctx:
            _validate_remote_observer_capabilities(
                capabilities,
                ObserverServerTarget(
                    host="bridge.local",
                    port=8765,
                    http_base_url="http://bridge.local:8765",
                    websocket_url="ws://bridge.local:8765/session",
                ),
            )

        self.assertIn("does not support required command message types", str(ctx.exception))

    def test_validate_remote_capabilities_rejects_unsupported_client_version(self) -> None:
        capabilities = _current_remote_capabilities()
        capabilities["minimum_client_version"] = "2"

        with self.assertRaises(SystemExit) as ctx:
            _validate_remote_observer_capabilities(
                capabilities,
                ObserverServerTarget(
                    host="bridge.local",
                    port=8765,
                    http_base_url="http://bridge.local:8765",
                    websocket_url="ws://bridge.local:8765/session",
                ),
            )

        self.assertIn("requires unsupported client version", str(ctx.exception))

    def test_validate_remote_capabilities_rejects_missing_auth_transports(self) -> None:
        capabilities = _current_remote_capabilities()
        capabilities["authentication_supported_transports"] = ["authorization_header"]

        with self.assertRaises(SystemExit) as ctx:
            _validate_remote_observer_capabilities(
                capabilities,
                ObserverServerTarget(
                    host="bridge.local",
                    port=8765,
                    http_base_url="http://bridge.local:8765",
                    websocket_url="ws://bridge.local:8765/session",
                ),
            )

        self.assertIn("does not support required authentication transports", str(ctx.exception))

    def test_validate_remote_capabilities_rejects_missing_browser_probe_url(self) -> None:
        capabilities = _current_remote_capabilities()
        capabilities["browser_probe_url"] = ""

        with self.assertRaises(SystemExit) as ctx:
            _validate_remote_observer_capabilities(
                capabilities,
                ObserverServerTarget(
                    host="bridge.local",
                    port=8765,
                    http_base_url="http://bridge.local:8765",
                    websocket_url="ws://bridge.local:8765/session",
                ),
            )

        self.assertIn("browser_probe_url must be a non-empty string", str(ctx.exception))


def _current_remote_capabilities() -> dict[str, object]:
    return build_remote_observer_capabilities_payload(
        capability_names=["local_embedded", "remote_observer"],
        server_version="1.2.3",
        authentication_required=True,
        authentication_scheme=AUTHENTICATION_SCHEME_BEARER_TOKEN,
        authentication_supported_transports=REQUIRED_AUTHENTICATION_TRANSPORTS,
        authentication_query_parameter_name=ACCESS_TOKEN_QUERY_PARAMETER,
        message_schema_url="/schema/control_room_message.json",
        browser_probe_url="/browser-probe",
    )


if __name__ == "__main__":
    unittest.main()
