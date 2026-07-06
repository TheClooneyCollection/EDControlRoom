from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

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
from edap.control_room.backend import ControlRoomBackend, LocalControlRoomBackend
from edap.control_room.app import ControlRoomApp
from edap.control_room.dependencies import LocalControlRoomDataSource
from edap.control_room.models import ReplaySelection
from edap.control_room.protocol import (
    ActivityLogEntry,
    build_activity_log_entry,
)
from edap.control_room.protocol.events import ActivityLogAppendedEvent, AnnouncementEvent
from edap.control_room.protocol.sink import ControlRoomEventSink
from edap.control_room_state import CommandHistoryEntry
from edap.inara.trade_routes import TradeRoute
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
        tts=TTSConfig(
            enabled=False,
            title="captain",
            disabled_messages=(),
            phrases={"arrival": "Arrived in {system_name}"},
        ),
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


class _ProtocolHarnessApp(ControlRoomApp):
    def __init__(self, ctx: RuntimeContext) -> None:
        super().__init__(ctx)
        self._current_version = "1.2.3"
        self._activity_widget = _ActivityLogStub()

    def _activity_auto_follow_paused(self) -> bool:  # type: ignore[override]
        return True

    def _refresh_activity_title(self) -> None:  # type: ignore[override]
        return None

    def query_one(self, selector: str, widget_type=None):  # type: ignore[override]
        if selector == "#activity":
            return self._activity_widget
        raise AssertionError(f"Unexpected selector: {selector}")


class _ActivityLogStub:
    def __init__(self) -> None:
        self.writes: list[object] = []
        self.styles = type("Styles", (), {"display": "block"})()

    def write(self, content, **kwargs) -> None:
        self.writes.append((content, kwargs))


class _StaticWidgetStub:
    def __init__(self) -> None:
        self.updated = None
        self.border_title = ""
        self.styles = type("Styles", (), {"display": "block"})()

    def update(self, content) -> None:
        self.updated = content


class _InputStub:
    def __init__(self) -> None:
        self.placeholder = ""
        self.value = ""
        self.cursor_position = 0


class _OptionListStub:
    def __init__(self) -> None:
        self.highlighted = 0
        self.options: list[object] = []

    def clear_options(self) -> None:
        self.options = []

    def add_options(self, options: list[object]) -> None:
        self.options.extend(options)


class _ContainerStub:
    def __init__(self) -> None:
        self.border_title = ""
        self.styles = type("Styles", (), {"display": "none"})()


class _KeyEventStub:
    def __init__(self, key: str, *, character: str | None = None) -> None:
        self.key = key
        self.character = character
        self.prevented = False

    def prevent_default(self) -> None:
        self.prevented = True


class _RenderHarnessApp(_ProtocolHarnessApp):
    def __init__(self, ctx: RuntimeContext, *, backend: ControlRoomBackend | None = None) -> None:
        self._status_widget = _StaticWidgetStub()
        self._haul_widget = _StaticWidgetStub()
        self._market_widget = _StaticWidgetStub()
        self._resume_help_widget = _StaticWidgetStub()
        self._resume_detail_widget = _StaticWidgetStub()
        self._resume_list_widget = _OptionListStub()
        self._resume_browser_widget = _ContainerStub()
        self._trade_route_help_widget = _StaticWidgetStub()
        self._trade_route_detail_widget = _StaticWidgetStub()
        self._trade_route_list_widget = _OptionListStub()
        self._trade_route_picker_widget = _ContainerStub()
        self._main_widget = _ContainerStub()
        self._command_input_widget = _InputStub()
        super().__init__(ctx) if backend is None else ControlRoomApp.__init__(self, ctx, backend=backend)
        self._activity_widget = _ActivityLogStub()

    def query_one(self, selector: str, widget_type=None):  # type: ignore[override]
        if selector == "#activity":
            return self._activity_widget
        if selector == "#cmd":
            return self._command_input_widget
        if selector == "#status":
            return self._status_widget
        if selector == "#haul":
            return self._haul_widget
        if selector == "#market":
            return self._market_widget
        if selector == "#resume-help":
            return self._resume_help_widget
        if selector == "#resume-detail":
            return self._resume_detail_widget
        if selector == "#resume-list":
            return self._resume_list_widget
        if selector == "#resume-browser":
            return self._resume_browser_widget
        if selector == "#trade-route-help":
            return self._trade_route_help_widget
        if selector == "#trade-route-detail":
            return self._trade_route_detail_widget
        if selector == "#trade-route-list":
            return self._trade_route_list_widget
        if selector == "#trade-route-picker":
            return self._trade_route_picker_widget
        if selector == "#main":
            return self._main_widget
        raise AssertionError(f"Unexpected selector: {selector}")


class _BackendStub(ControlRoomBackend):
    def subscribe_events(self, handler):
        return lambda: None

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        return None

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        return None

    def publish_data_refresh(self) -> None:
        return None

    def submit_input(self, raw: str) -> None:
        return None

    def dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        return None

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        return None

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        return None

    def dispatch_travel(
        self,
        *,
        system: str,
        station: str,
        on_land: bool = False,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        return None

    def handle_haul_prompt(self, value: str) -> None:
        return None

    def handle_haul_confirm_prompt(self, value: str) -> None:
        return None

    def load_trade_route(self, route: TradeRoute, *, raw_command: str | None = None) -> None:
        return None


class _IntentRecorderBackend(_BackendStub):
    def __init__(self) -> None:
        self.dispatched_commands: list[tuple[str, bool | None]] = []
        self.dispatched_hauls: list[tuple[dict[str, str] | None, bool, str | None]] = []
        self.submitted_inputs: list[str] = []
        self.loaded_trade_routes: list[tuple[TradeRoute, str | None]] = []

    def submit_input(self, raw: str) -> None:
        self.submitted_inputs.append(raw)

    def dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        self.dispatched_commands.append((raw, skip_delay))

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self.dispatched_hauls.append((params, skip_delay, raw_command))

    def load_trade_route(self, route: TradeRoute, *, raw_command: str | None = None) -> None:
        self.loaded_trade_routes.append((route, raw_command))


class _ExecutionRecorder:
    def __init__(self) -> None:
        self.dispatched_commands: list[tuple[str, bool | None]] = []
        self.dispatched_destinations: list[tuple[str, float, bool, str | None]] = []
        self.dispatched_hauls: list[tuple[dict[str, str] | None, bool, str | None]] = []
        self.dispatched_travels: list[tuple[str, str, bool, bool, str | None]] = []

    def submit_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        self.dispatched_commands.append((raw, skip_delay))

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
        on_land: bool = False,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self.dispatched_travels.append((system, station, on_land, skip_delay, raw_command))

    def load_trade_route(self, route: TradeRoute, *, raw_command: str | None = None) -> None:
        return None

    def handle_haul_prompt(self, value: str) -> None:
        return None

    def handle_haul_confirm_prompt(self, value: str) -> None:
        return None

    def cancel_active_routine(self, *, stop_mode="toggle") -> None:
        return None


class _SinkRecorder(ControlRoomEventSink):
    def __init__(self) -> None:
        self.activity_messages: list[str] = []
        self.announcement_ids: list[str] = []
        self.data_refresh_count = 0

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        self.activity_messages.append(entry.message_text)

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        self.announcement_ids.append(event.announcement_id)

    def publish_data_refresh(self) -> None:
        self.data_refresh_count += 1


class ControlRoomProtocolSnapshotTests(unittest.TestCase):
    def test_build_activity_log_entry_preserves_markup_for_remote_rendering(self) -> None:
        entry = build_activity_log_entry("[green]Connected.[/]")

        self.assertEqual(entry.message_text, "[green]Connected.[/]")

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.app = _ProtocolHarnessApp(_make_context(Path(self.tmpdir.name)))

    def test_log_records_protocol_activity_entry(self) -> None:
        self.app._log("[yellow]Docked at Jameson Memorial[/]")

        self.assertEqual(len(self.app._protocol_activity_log), 1)
        entry = self.app._protocol_activity_log[0]
        self.assertEqual(entry.message_text, "[yellow]Docked at Jameson Memorial[/]")

    def test_announce_tts_records_protocol_announcement_event_even_when_local_tts_disabled(self) -> None:
        self.app._announce_tts(AnnouncementId.ARRIVAL, system_name="Sol")

        self.assertEqual(len(self.app._protocol_announcements), 1)
        event = self.app._protocol_announcements[0]
        self.assertEqual(event.announcement_id, "arrival")
        self.assertEqual(event.message_text, "Arrived in Sol")
        self.assertEqual(event.message_values, {"system_name": "Sol"})

    def test_announcement_event_is_client_local_intent_only(self) -> None:
        event = AnnouncementEvent(
            announcement_id="arrival",
            message_text="Arrived in Sol",
            message_values={"system_name": "Sol"},
        )

        self.assertEqual(event.announcement_id, "arrival")
        self.assertEqual(event.message_text, "Arrived in Sol")
        self.assertEqual(event.message_values["system_name"], "Sol")

    def test_local_backend_is_attached_and_streams_activity_events(self) -> None:
        received: list[object] = []
        unsubscribe = self.app.backend.subscribe_events(received.append)

        self.app._log("[green]Observer ready[/]")
        unsubscribe()
        self.app._log("[green]Ignored after unsubscribe[/]")

        self.assertIsInstance(self.app.backend, LocalControlRoomBackend)
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], ActivityLogAppendedEvent)
        self.assertEqual(received[0].entry.message_text, "[green]Observer ready[/]")

    def test_local_backend_forwards_events_to_external_sink(self) -> None:
        recorder = _SinkRecorder()
        self.app._protocol_event_sink = recorder

        self.app._log("[green]Observer ready[/]")
        self.app._announce_tts(AnnouncementId.ARRIVAL, system_name="Sol")

        self.assertEqual(recorder.activity_messages, ["[green]Observer ready[/]"])
        self.assertEqual(recorder.announcement_ids, ["arrival"])

    def test_handle_event_publishes_data_refresh_to_external_sink(self) -> None:
        app = _RenderHarnessApp(_make_context(Path(self.tmpdir.name)))
        recorder = _SinkRecorder()
        app._protocol_event_sink = recorder

        app._handle_event({"event": "FSDTarget", "Name": "Achenar"})
        app._finalize_shutdown()

        self.assertEqual(recorder.data_refresh_count, 1)

    def test_status_panel_renders_from_data_source(self) -> None:
        remote_app = _ProtocolHarnessApp(_make_context(Path(self.tmpdir.name)))
        remote_app._ship.commander = "CMDR DATA"
        remote_app._ship.system = "Achenar"
        remote_app._ship.status = "in_station"
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=_BackendStub(),
        )
        app._ship.commander = "CMDR LOCAL"
        app._dependencies = replace(
            app._dependencies,
            data_source=LocalControlRoomDataSource(remote_app),
        )
        app._refresh_status()

        rendered = app._status_widget.updated.plain
        self.assertIn("CMDR DATA", rendered)
        self.assertNotIn("CMDR LOCAL", rendered)

    def test_dispatch_command_routes_through_execution_dependency(self) -> None:
        backend = _IntentRecorderBackend()
        execution = _ExecutionRecorder()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._dependencies = replace(app._dependencies, execution=execution)

        app._dispatch_command("commands", skip_delay=True)

        self.assertEqual(execution.dispatched_commands, [("commands", True)])

    def test_action_open_history_opens_local_replay_browser(self) -> None:
        backend = _IntentRecorderBackend()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app.set_focus = lambda _widget: None  # type: ignore[method-assign]
        app._saved_state.history = [
            CommandHistoryEntry(raw="jump", command="jump", timestamp="1")
        ]

        app.action_open_history()

        self.assertTrue(app._resume_open)

    def test_resume_execute_selected_dispatches_through_execution(self) -> None:
        backend = _IntentRecorderBackend()
        execution = _ExecutionRecorder()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._dependencies = replace(app._dependencies, execution=execution)
        app.set_focus = lambda _widget: None  # type: ignore[method-assign]
        app._resume_entries = [
            ReplaySelection(
                entry=CommandHistoryEntry(raw="jump", command="jump", timestamp="1"),
                label="jump",
                detail="jump",
            )
        ]

        app._resume_execute_selected()

        self.assertFalse(app._resume_open)
        self.assertEqual(execution.dispatched_commands, [("jump", None)])

    def test_trade_route_picker_enter_dispatches_haul_route_command(self) -> None:
        backend = _IntentRecorderBackend()
        execution = _ExecutionRecorder()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._dependencies = replace(app._dependencies, execution=execution)
        app._trade_routes.routes = [
            TradeRoute(
                index=2,
                from_station="Savitskaya Orbital",
                from_system="TSONGORIS",
                to_station="Nyberg Vision",
                to_system="NJOKUJINUN",
                source_buy_commodity="Beryllium",
            )
        ]
        app._selected_trade_route_index = 2
        app._trade_route_picker_open = True

        event = _KeyEventStub("enter")
        app.on_key(event)

        self.assertTrue(event.prevented)
        self.assertFalse(app._trade_route_picker_open)
        self.assertEqual(execution.dispatched_commands, [("haul route 2", None)])
        self.assertEqual(app._saved_state.selected_trade_route.from_station, "Savitskaya Orbital")

    def test_trade_route_picker_escape_closes_without_dispatch(self) -> None:
        backend = _IntentRecorderBackend()
        execution = _ExecutionRecorder()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._dependencies = replace(app._dependencies, execution=execution)
        app._trade_routes.routes = [
            TradeRoute(index=1, from_station="A", from_system="B", to_station="C", to_system="D")
        ]
        app._selected_trade_route_index = 1
        app._trade_route_picker_open = True

        event = _KeyEventStub("escape")
        app.on_key(event)

        self.assertTrue(event.prevented)
        self.assertFalse(app._trade_route_picker_open)
        self.assertEqual(backend.dispatched_commands, [])

    def test_trade_route_picker_d_sets_destination_to_first_station_system(self) -> None:
        backend = _IntentRecorderBackend()
        execution = _ExecutionRecorder()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._dependencies = replace(app._dependencies, execution=execution)
        app._trade_routes.routes = [
            TradeRoute(
                index=2,
                from_station="Savitskaya Orbital",
                from_system="TSONGORIS",
                to_station="Nyberg Vision",
                to_system="NJOKUJINUN",
                source_buy_commodity="Beryllium",
            )
        ]
        app._selected_trade_route_index = 2
        app._trade_route_picker_open = True

        event = _KeyEventStub("d")
        app.on_key(event)

        self.assertTrue(event.prevented)
        self.assertFalse(app._trade_route_picker_open)
        self.assertEqual(execution.dispatched_commands, [("dest TSONGORIS", None)])
        self.assertEqual(app._saved_state.selected_trade_route.from_station, "Savitskaya Orbital")

    def test_trade_route_picker_t_starts_travel_to_first_station(self) -> None:
        backend = _IntentRecorderBackend()
        execution = _ExecutionRecorder()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._dependencies = replace(app._dependencies, execution=execution)
        app._trade_routes.routes = [
            TradeRoute(
                index=2,
                from_station="Savitskaya Orbital",
                from_system="TSONGORIS",
                to_station="Nyberg Vision",
                to_system="NJOKUJINUN",
                source_buy_commodity="Beryllium",
            )
        ]
        app._selected_trade_route_index = 2
        app._trade_route_picker_open = True

        event = _KeyEventStub("t")
        app.on_key(event)

        self.assertTrue(event.prevented)
        self.assertFalse(app._trade_route_picker_open)
        self.assertEqual(
            execution.dispatched_travels,
            [("TSONGORIS", "Savitskaya Orbital", False, False, "travel TSONGORIS / Savitskaya Orbital")],
        )
        self.assertEqual(app._saved_state.selected_trade_route.from_station, "Savitskaya Orbital")

    def test_replay_open_arrow_keys_move_local_selection(self) -> None:
        backend = _IntentRecorderBackend()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._resume_open = True
        first = CommandHistoryEntry(raw="jump", command="jump", timestamp="1")
        second = CommandHistoryEntry(raw="dock", command="dock", timestamp="2")
        app._resume_entries = [
            ReplaySelection(entry=first, label="jump", detail="jump"),
            ReplaySelection(entry=second, label="dock", detail="dock"),
        ]
        app._selected_resume_history_entry = second

        up_event = _KeyEventStub("up")
        down_event = _KeyEventStub("down")

        app.on_key(up_event)
        app.on_key(down_event)

        self.assertTrue(up_event.prevented)
        self.assertTrue(down_event.prevented)
        self.assertEqual(app._selected_resume_history_entry, second)

    def test_blank_input_submission_dispatches_destination_prompt_default(self) -> None:
        backend = _IntentRecorderBackend()
        execution = _ExecutionRecorder()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._dependencies = replace(app._dependencies, execution=execution)
        input_stub = _InputStub()
        app.query_one = lambda selector, widget_type=None: input_stub if selector == "#cmd" else _RenderHarnessApp.query_one(app, selector, widget_type)  # type: ignore[method-assign]
        app._dest_prompt_destination = "Sol"

        class _SubmittedEvent:
            def __init__(self, input_widget) -> None:
                self.value = ""
                self.input = input_widget

        app.on_input_submitted(_SubmittedEvent(input_stub))

        self.assertEqual(execution.dispatched_destinations, [("Sol", 0.0, False, "")])
        self.assertEqual(input_stub.value, "")

    def test_blank_enter_key_dispatches_destination_prompt_default(self) -> None:
        backend = _IntentRecorderBackend()
        execution = _ExecutionRecorder()
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._dependencies = replace(app._dependencies, execution=execution)
        input_stub = _InputStub()
        app.query_one = lambda selector, widget_type=None: input_stub if selector == "#cmd" else _RenderHarnessApp.query_one(app, selector, widget_type)  # type: ignore[method-assign]
        app._dest_prompt_destination = "Sol"
        event = _KeyEventStub("enter")

        app.on_key(event)

        self.assertTrue(event.prevented)
        self.assertEqual(execution.dispatched_destinations, [("Sol", 0.0, False, "")])
        self.assertEqual(input_stub.value, "")


if __name__ == "__main__":
    unittest.main()
