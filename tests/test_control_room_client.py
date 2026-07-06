from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
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
from edap.control_room.app import ControlRoomApp
from edap.control_room.client.backend import (
    RemoteObserverBackend,
    RemoteObserverDataSource,
    RemoteObserverExecution,
    _validate_remote_observer_capabilities,
)
from edap.control_room.client.connect import connect_observer_mode
from edap.control_room.dependencies import (
    ActivityLogReadModel,
    CommandHistoryReadModel,
    ControlRoomDataReadModel,
    RoutineReadModel,
    ServerStatusReadModel,
    SessionReadModel,
    ControlRoomDependencies,
)
from edap.control_room_state import CommandHistoryEntry
from edap.control_room import commands as control_room_commands
from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.models import HaulStats, MarketData, ShipState
from edap.control_room.protocol import (
    ACCESS_TOKEN_QUERY_PARAMETER,
    ActivityLogEntry,
    ActivityLogAppendedEvent,
    AUTHENTICATION_SCHEME_BEARER_TOKEN,
    DataUpdatedEvent,
    REQUIRED_AUTHENTICATION_TRANSPORTS,
    RemoteObserverWebSocketConnectInfo,
    build_remote_observer_capabilities_payload,
    build_remote_observer_websocket_connect_info,
    event_from_message,
    hydrate_message,
)
from edap.inara.trade_routes import TradeRoute, TradeRouteSearchResult
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


def _bind_observer_widgets(app: ControlRoomApp, command_input: _FakeInputWidget) -> None:
    activity = _FakeActivityWidget()
    trade_route_list = _FakeOptionListWidget()
    trade_route_help = _FakeStaticWidget()
    trade_route_detail = _FakeStaticWidget()
    trade_route_picker = _FakeContainerWidget()
    status = _FakeStaticWidget()
    haul = _FakeStaticWidget()
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
            "#status": status,
            "#haul": haul,
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


def _data_read_model(
    *,
    system_name: str = "Sol",
    cargo_capacity: int | None = None,
) -> ControlRoomDataReadModel:
    return ControlRoomDataReadModel(
        ship=ShipState(system=system_name, cargo_capacity=cargo_capacity),
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
            haul_pause_requested=False,
            haul_paused=False,
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
    def _backend() -> RemoteObserverBackend:
        return RemoteObserverBackend(
            server_target=ControlRoomClientTests._target(),
            access_token="secret-token",
            client_name="observer-ipad",
            websocket_connect_info=_websocket_connect_info(),
        )

    def _app(
        self,
        *,
        backend: RemoteObserverBackend | None = None,
        data_source: RemoteObserverDataSource | None = None,
    ) -> ControlRoomApp:
        backend = backend or self._backend()
        data_source = data_source or RemoteObserverDataSource(_data_read_model())
        execution = RemoteObserverExecution(backend)
        app = ControlRoomApp(
            _make_observer_context(),
            backend=backend or self._backend(),
            dependencies=ControlRoomDependencies(
                data_source=data_source,
                execution=execution,
            ),
            title_override="ED Control Room Observer - bridge.local:8765",
        )
        execution.bind_app(app)
        return app

    def test_observer_app_initializes_without_local_journal_dir(self) -> None:
        app = self._app()

        self.assertIsNone(app._journal_dir)
        self.assertIsNone(app._market_path)

    def test_observer_app_preserves_local_activity_entries_across_activity_refresh(self) -> None:
        remote_activity = [
            ActivityLogEntry(
                entry_id="remote-1",
                timestamp="2026-06-30T13:54:34Z",
                message_text="[dim]Unknown command: dest sol[/]",
            )
        ]
        backend = self._backend()
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        activity = app.query_one("#activity")

        app._replace_activity_log(remote_activity)
        app._log("[bold]dest[/] - dest <system>")
        self.assertEqual(len(activity.writes), 2)

        app._replace_activity_log(remote_activity)

        rendered_messages = [segment.plain for segment in activity.writes]
        self.assertTrue(
            any("Unknown command: dest sol" in message for message in rendered_messages)
        )
        self.assertTrue(any("dest - dest <system>" in message for message in rendered_messages))
        self.assertIn("13:54:34  Unknown command: dest sol", rendered_messages[0])
        self.assertIn("dest - dest <system>", rendered_messages[-1])

    def test_observer_app_keeps_shutdown_state_client_local_on_data_refresh(self) -> None:
        data = _data_read_model()
        server_shutdown_data = replace(
            data,
            routine=replace(
                data.routine,
                shutdown_requested=True,
                shutdown_finalized=True,
            ),
        )
        app = self._app()
        _bind_observer_widgets(app, _FakeInputWidget())

        app._apply_data_state(server_shutdown_data, replace_activity=True)

        self.assertFalse(app._shutdown_requested)
        self.assertFalse(app._shutdown_finalized)

        app._shutdown_requested = True
        app._shutdown_finalized = True
        server_running_data = replace(
            data,
            routine=replace(
                data.routine,
                shutdown_requested=False,
                shutdown_finalized=False,
            ),
        )

        app._apply_data_state(server_running_data, replace_activity=True)

        self.assertTrue(app._shutdown_requested)
        self.assertTrue(app._shutdown_finalized)

    def test_observer_app_preserves_observed_activity_order_on_refresh(self) -> None:
        remote_activity = [
            ActivityLogEntry(
                entry_id="remote-1",
                timestamp="2026-06-30T15:57:30Z",
                message_text="[dim]Executing dest sol in 5.0s...[/]",
            ),
            ActivityLogEntry(
                entry_id="remote-2",
                timestamp="2026-06-30T15:57:31Z",
                message_text="[yellow]Remote Ctrl-C received — cancelling active routine.[/]",
            ),
            ActivityLogEntry(
                entry_id="remote-3",
                timestamp="2026-06-30T15:57:31Z",
                message_text="[yellow]Cancelled pending dest sol before execution.[/]",
            ),
        ]
        backend = self._backend()
        app = self._app(backend=backend)
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        activity = app.query_one("#activity")

        local_activity = [
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
        for entry in local_activity:
            app._remember_activity_display_order(entry)
        app._local_activity_log = local_activity

        app._replace_activity_log(remote_activity)

        rendered_messages = [segment.plain for segment in activity.writes]
        self.assertEqual(
            rendered_messages,
            [
                "15:57:34  Command: dest sol",
                "15:57:34  Destination: sol",
                "15:57:34  Galaxy-map settle seconds? (Enter = 2.0)",
                "15:57:30  Executing dest sol in 5.0s...",
                "15:57:31  Remote Ctrl-C received — cancelling active routine.",
                "15:57:31  Cancelled pending dest sol before execution.",
            ],
        )

    def test_observer_app_uses_event_timestamp_for_incremental_activity_append(self) -> None:
        backend = self._backend()
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
        backend = self._backend()
        app = self._app(backend=backend)
        app._saved_state.history = [
            CommandHistoryEntry(
                raw="haul Silver",
                command="haul",
                params={
                    "station_1_buying": "Silver",
                    "station_1": "Savitskaya Orbital",
                    "station_1_system": "TSONGORIS",
                    "station_2": "Nyberg Vision",
                    "station_2_system": "NJOKUJINUN",
                },
                timestamp="2026-06-30T12:00:00Z",
            )
        ]
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        app.set_focus = lambda _widget: None  # type: ignore[method-assign]

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
        backend = self._backend()
        app = self._app(backend=backend)
        app._saved_state.history = [
            CommandHistoryEntry(
                raw="haul Silver",
                command="haul",
                params={"station_1_buying": "Silver"},
                timestamp="2026-06-30T12:00:00Z",
            ),
            CommandHistoryEntry(
                raw="dest Achenar",
                command="dest",
                params={"destination": "Achenar", "galaxy_map_settle": "2.0"},
                timestamp="2026-06-30T12:01:00Z",
            ),
        ]
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        app.set_focus = lambda _widget: None  # type: ignore[method-assign]

        app._show_resume_picker()
        app._resume_filter = "dest"
        app._refresh_resume_picker()

        self.assertEqual(len(app._resume_entries), 1)
        self.assertEqual(app._resume_entries[0].entry.raw, "dest Achenar")
        self.assertTrue(backend._outgoing_messages.empty())

    def test_observer_app_replay_command_runs_locally(self) -> None:
        backend = self._backend()
        app = self._app(backend=backend)
        app._saved_state.history = [
            CommandHistoryEntry(
                raw="haul Silver",
                command="haul",
                params={"station_1_buying": "Silver"},
                timestamp="2026-06-30T12:00:00Z",
            )
        ]
        command_input = _FakeInputWidget()
        _bind_observer_widgets(app, command_input)
        app.set_focus = lambda _widget: None  # type: ignore[method-assign]

        class _Submitted:
            def __init__(self, value: str) -> None:
                self.value = value
                self.input = type("_Input", (), {"value": value})()

        app.on_input_submitted(_Submitted("replay"))

        self.assertTrue(app._resume_open)
        self.assertTrue(any(entry.entry.raw == "haul Silver" for entry in app._resume_entries))
        self.assertTrue(backend._outgoing_messages.empty())

    def test_observer_app_market_lock_pins_locally_and_keeps_matching_updates(self) -> None:
        backend = self._backend()
        data_source = RemoteObserverDataSource(
            replace(
                _data_read_model(system_name="Sol"),
                market=MarketData(
                    station="Jameson Memorial",
                    system="Sol",
                    timestamp="2026-06-30T12:00:00Z",
                    market_id=128666762,
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

        app._apply_data_state(data_source.current(), replace_activity=False)
        app._sync_presented_market_from_current_data(force=True)
        self.assertEqual(app._view_market_data().station, "Jameson Memorial")

        app.on_input_submitted(_Submitted("market lock"))
        self.assertTrue(app._market.locked)
        self.assertTrue(backend._outgoing_messages.empty())

        data_source.hydrate(
            replace(
                data_source.current(),
                market=MarketData(
                    station="Jameson Memorial",
                    system="Sol",
                    timestamp="2026-06-30T12:01:00Z",
                    market_id=128666762,
                    items=[{"Name": "gold", "Stock": 84}],
                ),
            )
        )
        app._apply_data_state(data_source.current(), replace_activity=False)
        self.assertEqual(app._view_market_data().station, "Jameson Memorial")
        self.assertEqual(app._view_market_data().items[0]["Stock"], 84)

        data_source.hydrate(
            replace(
                data_source.current(),
                market=MarketData(
                    station="Galileo",
                    system="Sol",
                    timestamp="2026-06-30T12:02:00Z",
                    market_id=3229359104,
                    items=[{"Name": "silver", "Stock": 99}],
                ),
            )
        )
        app._apply_data_state(data_source.current(), replace_activity=False)
        self.assertEqual(app._view_market_data().station, "Jameson Memorial")
        self.assertEqual(app._view_market_data().items[0]["Name"], "gold")
        self.assertEqual(app._view_market_data().items[0]["Stock"], 84)

        app.on_input_submitted(_Submitted("market unlock"))
        self.assertFalse(app._market.locked)
        self.assertEqual(app._view_market_data().station, "Galileo")
        self.assertEqual(app._view_market_data().items[0]["Name"], "silver")
        self.assertTrue(backend._outgoing_messages.empty())

    def test_observer_app_handles_haul_search_locally(self) -> None:
        backend = self._backend()
        data_source = RemoteObserverDataSource(
            _data_read_model(system_name="Praea Euq AK-A d25", cargo_capacity=460)
        )
        app = self._app(backend=backend, data_source=data_source)
        app._ship.system = "Praea Euq AK-A d25"
        app._ship.cargo_capacity = 460
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
        with patch("edap.control_room.routines_haul.search_trade_routes", return_value=result):
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
        backend = self._backend()
        data_source = RemoteObserverDataSource(
            _data_read_model(system_name="Praea Euq AK-A d25", cargo_capacity=460)
        )
        app = self._app(backend=backend, data_source=data_source)
        app._ship.system = "Praea Euq AK-A d25"
        app._ship.cargo_capacity = 460
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

    def test_observer_app_uses_remote_data_context_for_bare_haul_search(self) -> None:
        backend = self._backend()
        data_source = RemoteObserverDataSource(
            _data_read_model(system_name="Zeta Trianguli Australis", cargo_capacity=461)
        )
        app = self._app(backend=backend, data_source=data_source)
        app._ship.system = "Zeta Trianguli Australis"
        app._ship.cargo_capacity = 461
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
        with patch("edap.control_room.routines_haul.search_trade_routes", return_value=result):
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

    def test_observer_app_handles_dest_command_locally_then_dispatches_remote(self) -> None:
        backend = self._backend()
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
        backend = self._backend()
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
        backend = self._backend()
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

    def test_connect_observer_mode_uses_parsed_websocket_url(self) -> None:
        loaded = SimpleNamespace(
            config=_make_observer_context().config,
            config_path="config.toml",
            used_example_config_fallback=False,
        )
        captured_apps: list[object] = []
        captured_backends: list[RemoteObserverBackend] = []

        class _FakeApp:
            def __init__(self, *_args, **kwargs) -> None:
                captured_backends.append(kwargs["backend"])

            def run(self) -> None:
                captured_apps.append(self)

        with (
            patch("edap.control_room.client.connect.load_config_with_fallback", return_value=loaded),
            patch(
                "edap.control_room.client.connect.build_runtime_context",
                return_value=_make_observer_context(),
            ),
            patch(
                "edap.control_room.client.connect.fetch_remote_control_room_data",
                return_value=(_current_remote_capabilities(), _data_read_model()),
            ),
            patch("edap.control_room.client.connect.ControlRoomApp", new=_FakeApp),
        ):
            connect_observer_mode(
                config_path="config.toml",
                target="http://192.168.50.201:8765",
                access_token="1001",
                client_name="observer-test",
                claim_operator=True,
            )

        self.assertEqual(
            captured_backends[0]._websocket_connect_info.session_url,
            "ws://192.168.50.201:8765/session?client_name=observer-test",
        )
        self.assertEqual(
            captured_backends[0]._websocket_connect_info.additional_headers,
            (("Authorization", "Bearer 1001"),),
        )
        claim_message = captured_backends[0]._outgoing_messages.get_nowait()
        self.assertEqual(claim_message["message_type"], "command.request_active_operator")
        self.assertEqual(len(captured_apps), 1)

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

    def test_remote_backend_enqueues_dispatch_destination_haul_loop_and_travel(self) -> None:
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
        backend.dispatch_travel(
            system="Sol",
            station="Abraham Lincoln",
            raw_command="travel Sol / Abraham Lincoln",
        )

        destination_message = backend._outgoing_messages.get_nowait()
        haul_message = backend._outgoing_messages.get_nowait()
        travel_message = backend._outgoing_messages.get_nowait()
        self.assertEqual(destination_message["message_type"], "command.dispatch_destination")
        self.assertEqual(destination_message["payload"]["destination"], "Achenar")
        self.assertEqual(destination_message["payload"]["galaxy_map_settle"], 3.5)
        self.assertTrue(destination_message["payload"]["skip_delay"])
        self.assertEqual(haul_message["message_type"], "command.dispatch_haul_loop")
        self.assertEqual(haul_message["payload"]["params"]["station_1_buying"], "Silver")
        self.assertEqual(haul_message["payload"]["raw_command"], "haul Silver")
        self.assertEqual(travel_message["message_type"], "command.dispatch_travel")
        self.assertEqual(travel_message["payload"]["system"], "Sol")
        self.assertEqual(travel_message["payload"]["station"], "Abraham Lincoln")
        self.assertEqual(travel_message["payload"]["raw_command"], "travel Sol / Abraham Lincoln")

    def test_remote_execution_delegates_to_remote_backend(self) -> None:
        backend = self._backend()
        execution = RemoteObserverExecution(backend)

        execution.submit_command("jump", skip_delay=True)
        execution.dispatch_destination("Achenar", 3.5, raw_command="dest Achenar")
        execution.dispatch_haul_loop(params={"station_1_buying": "Silver"}, raw_command="haul")
        execution.dispatch_travel(system="Sol", station="Abraham Lincoln", raw_command="travel Sol / Abraham Lincoln")

        command_message = backend._outgoing_messages.get_nowait()
        destination_message = backend._outgoing_messages.get_nowait()
        haul_message = backend._outgoing_messages.get_nowait()
        travel_message = backend._outgoing_messages.get_nowait()

        self.assertEqual(command_message["message_type"], "command.submit_input")
        self.assertEqual(command_message["payload"]["raw_input"], "jump")
        self.assertEqual(command_message["payload"]["skip_delay"], True)
        self.assertEqual(destination_message["message_type"], "command.dispatch_destination")
        self.assertEqual(destination_message["payload"]["destination"], "Achenar")
        self.assertEqual(haul_message["message_type"], "command.dispatch_haul_loop")
        self.assertEqual(haul_message["payload"]["params"]["station_1_buying"], "Silver")
        self.assertEqual(travel_message["message_type"], "command.dispatch_travel")
        self.assertEqual(travel_message["payload"]["station"], "Abraham Lincoln")

    def test_remote_data_source_hydrates_current_read_model(self) -> None:
        data_source = RemoteObserverDataSource(_data_read_model(system_name="Sol"))

        data_source.hydrate(_data_read_model(system_name="Achenar"))

        self.assertEqual(data_source.current().ship.system, "Achenar")

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

    def test_remote_backend_reports_connection_loss(self) -> None:
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
            websocket_connect_info=_websocket_connect_info(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)
        backend._has_connected_once = True

        backend._handle_connection_lost("Observer connection lost: ping timeout")

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
            websocket_connect_info=_websocket_connect_info(),
        )

        backend.interrupt_active_routine()

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.cancel_active_routine")
        self.assertEqual(message["payload"], {})

    def test_remote_backend_enqueues_explicit_stop_mode(self) -> None:
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
            websocket_connect_info=_websocket_connect_info(),
        )

        backend.interrupt_active_routine(stop_mode="now")

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.cancel_active_routine")
        self.assertEqual(message["payload"], {"mode": "now"})

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
