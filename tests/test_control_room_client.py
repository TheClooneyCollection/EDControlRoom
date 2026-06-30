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
    _validate_remote_observer_capabilities,
)
from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.models import TradeRoutePickerState, TradeRoutesData
from edap.control_room.protocol import (
    ACCESS_TOKEN_QUERY_PARAMETER,
    ActivityLogAppendedEvent,
    AUTHENTICATION_SCHEME_BEARER_TOKEN,
    REQUIRED_AUTHENTICATION_TRANSPORTS,
    RemoteObserverWebSocketConnectInfo,
    SnapshotUpdatedEvent,
    build_remote_observer_capabilities_payload,
    build_remote_observer_websocket_connect_info,
    event_from_message,
)
from edap.inara.trade_routes import TradeRoute, TradeRouteSearchResult
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

    @property
    def auto_follow_paused(self) -> bool:
        return not self.auto_scroll

    def write(self, *_args, **_kwargs) -> None:
        return None


class _FakeContainerWidget:
    def __init__(self) -> None:
        self.styles = _WidgetStyles()
        self.border_title = ""


def _bind_observer_widgets(app: ObserverControlRoomApp, command_input: _FakeInputWidget) -> None:
    activity = _FakeActivityWidget()
    trade_route_list = _FakeOptionListWidget()
    trade_route_help = _FakeStaticWidget()
    trade_route_detail = _FakeStaticWidget()
    trade_route_picker = _FakeContainerWidget()
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
            market_filter_text=None,
            locked=False,
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
            replay_browser_open=False,
            shutdown_requested=False,
            shutdown_finalized=False,
        ),
        command_history=CommandHistorySnapshot(history_limit=20),
        prompt_state=PromptStateSnapshot(),
        replay_browser=ReplayBrowserSnapshot(open=False, filter_text=""),
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

    def _app(self, *, backend: RemoteObserverBackend | None = None) -> ObserverControlRoomApp:
        return ObserverControlRoomApp(
            _make_observer_context(),
            backend=backend or self._backend(),
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

    def test_observer_app_applies_remote_replay_edit_prefill(self) -> None:
        updated_snapshot = replace(
            _snapshot(),
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            prompt_state=PromptStateSnapshot(
                command_input_prefill_active=True,
                command_input_placeholder="commands | help dock | ...",
                command_input_value="jump",
            ),
        )
        backend = self._backend(initial_snapshot=updated_snapshot)
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        command_input.disabled = True
        _bind_observer_widgets(app, command_input)

        app._apply_view_snapshot_state()
        app._refresh_remote_command_input()

        self.assertFalse(command_input.disabled)
        self.assertEqual(command_input.placeholder, "commands | help dock | ...")
        self.assertEqual(command_input.value, "jump")
        self.assertEqual(command_input.cursor_position, 4)

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
        app._controls = object()
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
        app._controls = object()
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

    def test_event_from_message_parses_snapshot_message(self) -> None:
        snapshot = _snapshot()
        event = event_from_message(
            {
                "message_type": "state.snapshot",
                "payload": asdict(snapshot),
            }
        )

        self.assertIsInstance(event, SnapshotUpdatedEvent)
        self.assertEqual(event.snapshot.ship.system_name, "Sol")

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
            prompt_state=snapshot.prompt_state,
            replay_browser=snapshot.replay_browser,
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

    def test_remote_backend_enqueues_snapshot_request_and_submit_input(self) -> None:
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

        backend.request_snapshot()
        backend.dispatch_command("dock")

        first = backend._outgoing_messages.get_nowait()
        second = backend._outgoing_messages.get_nowait()
        self.assertEqual(first["message_type"], "command.request_snapshot")
        self.assertEqual(second["message_type"], "command.submit_input")
        self.assertEqual(second["payload"]["raw_input"], "dock")

    def test_remote_backend_enqueues_trade_route_load(self) -> None:
        backend = self._backend()

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

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.load_trade_route")
        self.assertEqual(message["payload"]["route"]["index"], 2)
        self.assertEqual(message["payload"]["route"]["to_system"], "NJOKUJINUN")
        self.assertEqual(
            message["payload"]["raw_command"],
            "haul route Savitskaya Orbital -> Nyberg Vision",
        )

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

    def test_remote_backend_enqueues_replay_commands(self) -> None:
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

        self.assertEqual(backend._outgoing_messages.get_nowait()["message_type"], "command.open_replay_browser")
        self.assertEqual(backend._outgoing_messages.get_nowait()["payload"]["filter_text"], "haul")
        move_message = backend._outgoing_messages.get_nowait()
        self.assertEqual(move_message["message_type"], "command.move_replay_selection")
        self.assertEqual(move_message["payload"]["offset"], 1)
        replay_message = backend._outgoing_messages.get_nowait()
        self.assertEqual(replay_message["message_type"], "command.replay_history_entry")
        self.assertTrue(replay_message["payload"]["edit"])
        self.assertTrue(replay_message["payload"]["skip_delay"])
        toggle_message = backend._outgoing_messages.get_nowait()
        self.assertEqual(toggle_message["message_type"], "command.toggle_replay_default_haul")
        self.assertEqual(backend._outgoing_messages.get_nowait()["message_type"], "command.close_replay_browser")

    def test_remote_backend_marks_snapshot_disconnected_on_connection_loss(self) -> None:
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
                replay_browser_open=True,
                shutdown_requested=False,
                shutdown_finalized=False,
            ),
            command_history=_snapshot().command_history,
            prompt_state=_snapshot().prompt_state,
            replay_browser=_snapshot().replay_browser,
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
        self.assertIsNone(current.active_operator)
        self.assertFalse(current.ui_state.routine_active)
        self.assertIsNone(current.ui_state.active_routine_name)
        self.assertFalse(current.ui_state.replay_browser_open)
        self.assertIsInstance(received[0], SnapshotUpdatedEvent)
        self.assertIsInstance(received[1], ActivityLogAppendedEvent)
        self.assertEqual(received[1].entry.message_text, "Observer connection lost: ping timeout")

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
        backend.request_snapshot()
        backend._emit_local_message("Observer connection restored.")

        messages = [
            event.entry.message_text
            for event in received
            if isinstance(event, ActivityLogAppendedEvent)
        ]
        self.assertIn("Observer connection lost: ping timeout", messages)
        self.assertIn("Reconnecting in 1.0s...", messages)
        self.assertIn("Observer connection restored.", messages)
        reconnect_request = backend._outgoing_messages.get_nowait()
        self.assertEqual(reconnect_request["message_type"], "command.request_snapshot")

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
