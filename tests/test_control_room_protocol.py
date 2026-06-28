from __future__ import annotations

import tempfile
import unittest
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
from edap.control_room.history import resume_detail, resume_label
from edap.control_room.models import ReplaySelection
from edap.control_room.protocol import (
    ActivityLogEntry,
    build_activity_log_entry,
    snapshot_from_app,
)
from edap.control_room.protocol.events import ActivityLogAppendedEvent, AnnouncementEvent
from edap.control_room.protocol.snapshot import (
    CommandHistoryEntrySnapshot,
    ControlRoomSnapshot,
    ReplayBrowserSnapshot,
    ReplayEntrySnapshot,
)
from edap.control_room.protocol.sink import ControlRoomEventSink
from edap.control_room_state import CommandHistoryEntry, ControlRoomState
from edap.inara.trade_routes import TradeRoute
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


class _SnapshotBackend(ControlRoomBackend):
    def __init__(self, snapshot: ControlRoomSnapshot) -> None:
        self.snapshot = snapshot

    def current_snapshot(self) -> ControlRoomSnapshot:
        return self.snapshot

    def subscribe_events(self, handler):
        return lambda: None

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        return None

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        return None

    def publish_snapshot(self, snapshot: ControlRoomSnapshot) -> None:
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
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        return None

    def handle_haul_prompt(self, value: str) -> None:
        return None

    def handle_haul_confirm_prompt(self, value: str) -> None:
        return None

    def open_replay_browser(self) -> None:
        return None

    def close_replay_browser(self) -> None:
        return None

    def refresh_replay_browser(self) -> None:
        return None

    def set_replay_filter(self, filter_text: str) -> None:
        return None

    def move_replay_selection(self, offset: int) -> None:
        return None

    def replay_history_entry(
        self,
        entry: CommandHistoryEntry,
        *,
        edit: bool,
        skip_delay: bool = False,
    ) -> None:
        return None

    def toggle_replay_default_haul(self, entry: CommandHistoryEntry) -> None:
        return None


class _IntentRecorderBackend(_SnapshotBackend):
    def __init__(self, snapshot: ControlRoomSnapshot) -> None:
        super().__init__(snapshot)
        self.dispatched_commands: list[tuple[str, bool | None]] = []
        self.submitted_inputs: list[str] = []
        self.opened_replay_browser = 0
        self.closed_replay_browser = 0
        self.replay_selection_offsets: list[int] = []
        self.replayed_entries: list[tuple[str, bool, bool]] = []

    def submit_input(self, raw: str) -> None:
        self.submitted_inputs.append(raw)

    def dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        self.dispatched_commands.append((raw, skip_delay))

    def open_replay_browser(self) -> None:
        self.opened_replay_browser += 1

    def close_replay_browser(self) -> None:
        self.closed_replay_browser += 1

    def move_replay_selection(self, offset: int) -> None:
        self.replay_selection_offsets.append(offset)

    def replay_history_entry(
        self,
        entry: CommandHistoryEntry,
        *,
        edit: bool,
        skip_delay: bool = False,
    ) -> None:
        self.replayed_entries.append((entry.raw, edit, skip_delay))


class _SinkRecorder(ControlRoomEventSink):
    def __init__(self) -> None:
        self.activity_messages: list[str] = []
        self.announcement_ids: list[str] = []
        self.snapshot_count = 0

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        self.activity_messages.append(entry.message_text)

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        self.announcement_ids.append(event.announcement_id)

    def publish_snapshot(self, snapshot: ControlRoomSnapshot) -> None:
        self.snapshot_count += 1


class ControlRoomProtocolSnapshotTests(unittest.TestCase):
    def test_build_activity_log_entry_preserves_markup_for_remote_rendering(self) -> None:
        entry = build_activity_log_entry("[green]Connected.[/]")

        self.assertEqual(entry.message_text, "[green]Connected.[/]")

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.app = _ProtocolHarnessApp(_make_context(Path(self.tmpdir.name)))

    def test_snapshot_from_app_maps_current_state(self) -> None:
        history_entry = CommandHistoryEntry(
            raw="haul gold",
            command="haul",
            params={"commodity": "gold"},
            timestamp="2026-06-15T15:00:00Z",
        )
        self.app._ship.commander = "CMDR TEST"
        self.app._ship.ship_type = "Type-9"
        self.app._ship.system = "Sol"
        self.app._ship.station = "Jameson Memorial"
        self.app._ship.status = "in_station"
        self.app._ship.credits = 123456
        self.app._ship.cargo_count = 32
        self.app._ship.cargo_capacity = 128
        self.app._ship.cargo_inventory = [{"Name": "gold", "Count": 32}]
        self.app._ship.destination_system = "Achenar"
        self.app._market.station = "Jameson Memorial"
        self.app._market.system = "Sol"
        self.app._market.timestamp = "2026-06-15T15:01:00Z"
        self.app._market.items = [{"Name": "gold", "Stock": 42}]
        self.app._market.locked = True
        self.app._market_filter = "gold"
        self.app._haul_stats.station_1_buying = "gold"
        self.app._haul_stats.station_2_buying = "silver"
        self.app._haul_stats.station_1 = "Jameson Memorial"
        self.app._haul_stats.station_2 = "Galileo"
        self.app._haul_stats.active = True
        self.app._haul_stats.current_run_profit = 5000
        self.app._haul_stats.completed_runs = 2
        self.app._haul_stats.accumulated_profit = 9000
        self.app._runtime_state.routine_active = True
        self.app._runtime_state.active_routine_name = "haul"
        self.app._runtime_state.instant_mode = True
        self.app._prompt_state.haul_params = {"commodity": "gold"}
        self.app._prompt_state.dest_prompt_destination = "Achenar"
        self.app._saved_state = ControlRoomState(
            default_haul={"commodity": "gold"},
            history=[history_entry],
            instant_mode=True,
        )
        self.app._history_draft = "sell gold"
        self.app._resume_filter = "ha"
        self.app._replay_state.open = True
        self.app._replay_state.filter_text = "ha"
        self.app._resume_entries = [
            ReplaySelection(
                entry=history_entry,
                label=resume_label(history_entry, self.app._saved_state.default_haul),
                detail=resume_detail(history_entry),
            )
        ]

        snapshot = snapshot_from_app(
            self.app,
            session_id="session-1",
            client_name="observer-1",
            activity_log=[
                ActivityLogEntry(
                    entry_id="log-1",
                    timestamp="2026-06-15T15:02:00Z",
                    message_text="Docked at Jameson Memorial",
                    severity="info",
                )
            ],
            capability_names=["snapshot", "announcement_stream"],
        )

        self.assertEqual(snapshot.session.session_id, "session-1")
        self.assertEqual(snapshot.ship.commander_name, "CMDR TEST")
        self.assertEqual(snapshot.ship.station_name, "Jameson Memorial")
        self.assertEqual(snapshot.market.market_filter_text, "gold")
        self.assertTrue(snapshot.market.locked)
        self.assertTrue(snapshot.haul_session.active)
        self.assertEqual(snapshot.haul_session.current_run_profit, 5000)
        self.assertTrue(snapshot.ui_state.routine_active)
        self.assertTrue(snapshot.ui_state.instant_mode)
        self.assertTrue(snapshot.ui_state.activity_auto_follow_paused)
        self.assertEqual(snapshot.command_history.default_haul, {"commodity": "gold"})
        self.assertEqual(snapshot.command_history.history_entries[0].raw_command, "haul gold")
        self.assertEqual(snapshot.command_history.draft_command, "sell gold")
        self.assertEqual(snapshot.prompt_state.destination_prompt_destination, "Achenar")
        self.assertTrue(snapshot.replay_browser.open)
        self.assertEqual(snapshot.replay_browser.visible_entries[0].history_entry.command_name, "haul")
        self.assertEqual(snapshot.activity_log[0].message_text, "Docked at Jameson Memorial")

    def test_snapshot_from_app_includes_selected_replay_history_entry(self) -> None:
        entry = CommandHistoryEntry(
            raw="haul gold",
            command="haul",
            params={"station_1_buying": "gold"},
            timestamp="2026-06-15T15:00:00Z",
        )
        app = _RenderHarnessApp(_make_context(Path(self.tmpdir.name)))
        app._replay_state.open = True
        app._resume_entries = [
            ReplaySelection(
                entry=entry,
                label="haul gold",
                detail="haul detail",
            )
        ]
        app._selected_resume_history_entry = entry

        snapshot = snapshot_from_app(app)

        self.assertIsNotNone(snapshot.replay_browser.selected_history_entry)
        self.assertEqual(
            snapshot.replay_browser.selected_history_entry.raw_command,
            "haul gold",
        )

    def test_snapshot_from_app_prefers_live_command_input_during_prefill_prompt(self) -> None:
        app = _RenderHarnessApp(_make_context(Path(self.tmpdir.name)))
        app._prompt_state.command_input_prefill_active = True
        app._prompt_state.command_input_placeholder = "stale placeholder"
        app._prompt_state.command_input_value = "stale=value"
        app._command_input_widget.placeholder = "edit Inara search params then press Enter..."
        app._command_input_widget.value = "near_system=Sol cargo_capacity=512"

        snapshot = snapshot_from_app(app)

        self.assertTrue(snapshot.prompt_state.command_input_prefill_active)
        self.assertEqual(
            snapshot.prompt_state.command_input_placeholder,
            "edit Inara search params then press Enter...",
        )
        self.assertEqual(
            snapshot.prompt_state.command_input_value,
            "near_system=Sol cargo_capacity=512",
        )

    def test_sync_view_snapshot_does_not_reset_cursor_for_unchanged_prefill(self) -> None:
        app = _RenderHarnessApp(_make_context(Path(self.tmpdir.name)))
        app._prompt_state.command_input_prefill_active = True
        app._command_input_widget.placeholder = "edit Inara search params then press Enter..."
        app._command_input_widget.value = "near_system=Sol cargo_capacity=512"
        app._command_input_widget.cursor_position = 8
        snapshot = snapshot_from_app(app)
        app._backend = _SnapshotBackend(snapshot)

        app._sync_view_snapshot()

        self.assertEqual(app._command_input_widget.value, "near_system=Sol cargo_capacity=512")
        self.assertEqual(app._command_input_widget.cursor_position, 8)

    def test_remote_snapshot_apply_syncs_resume_widget_from_selected_history_entry(self) -> None:
        entry = CommandHistoryEntry(
            raw="haul gold",
            command="haul",
            params={"station_1_buying": "gold"},
            timestamp="2026-06-15T15:00:00Z",
        )
        base_app = _ProtocolHarnessApp(_make_context(Path(self.tmpdir.name)))
        base_snapshot = snapshot_from_app(base_app)
        history_entry_snapshot = CommandHistoryEntrySnapshot(
            raw_command=entry.raw,
            command_name=entry.command,
            arguments=entry.params,
            timestamp=entry.timestamp,
        )
        snapshot = ControlRoomSnapshot(
            session=base_snapshot.session,
            connected_clients=base_snapshot.connected_clients,
            active_operator=base_snapshot.active_operator,
            ship=base_snapshot.ship,
            market=base_snapshot.market,
            haul_session=base_snapshot.haul_session,
            ui_state=base_snapshot.ui_state,
            command_history=base_snapshot.command_history,
            prompt_state=base_snapshot.prompt_state,
            replay_browser=ReplayBrowserSnapshot(
                open=True,
                filter_text="haul",
                visible_entries=[
                    ReplayEntrySnapshot(
                        label="haul gold",
                        detail="haul detail",
                        history_entry=history_entry_snapshot,
                    )
                ],
                selected_history_entry=history_entry_snapshot,
            ),
            activity_log=base_snapshot.activity_log,
            server_status=base_snapshot.server_status,
        )
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=_SnapshotBackend(snapshot),
        )

        app._sync_view_snapshot()

        self.assertEqual(app._selected_resume_history_entry, entry)
        self.assertEqual(app._resume_list_widget.highlighted, 0)
        self.assertEqual(app._resume_list_widget.options, ["haul gold"])
        self.assertEqual(app._activity_widget.styles.display, "none")
        self.assertEqual(app._resume_browser_widget.styles.display, "block")
        self.assertEqual(app._resume_help_widget.updated.splitlines()[-1], "Filter: haul")

    def test_log_records_protocol_activity_entry_and_snapshot_uses_it_by_default(self) -> None:
        self.app._log("[yellow]Docked at Jameson Memorial[/]")

        self.assertEqual(len(self.app._protocol_activity_log), 1)
        entry = self.app._protocol_activity_log[0]
        self.assertEqual(entry.message_text, "[yellow]Docked at Jameson Memorial[/]")

        snapshot = snapshot_from_app(self.app)
        self.assertEqual(len(snapshot.activity_log), 1)
        self.assertEqual(
            snapshot.activity_log[0].message_text,
            "[yellow]Docked at Jameson Memorial[/]",
        )

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

    def test_handle_event_publishes_snapshot_to_external_sink(self) -> None:
        app = _RenderHarnessApp(_make_context(Path(self.tmpdir.name)))
        recorder = _SinkRecorder()
        app._protocol_event_sink = recorder

        app._handle_event({"event": "FSDTarget", "Name": "Achenar"})
        app._finalize_shutdown()

        self.assertEqual(recorder.snapshot_count, 1)

    def test_status_panel_can_render_from_backend_snapshot(self) -> None:
        remote_app = _ProtocolHarnessApp(_make_context(Path(self.tmpdir.name)))
        remote_app._ship.commander = "CMDR REMOTE"
        remote_app._ship.system = "Achenar"
        remote_app._ship.status = "in_station"
        snapshot = snapshot_from_app(remote_app)

        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=_SnapshotBackend(snapshot),
        )
        app._ship.commander = "CMDR LOCAL"
        app._refresh_status()

        rendered = app._status_widget.updated.plain
        self.assertIn("CMDR REMOTE", rendered)
        self.assertNotIn("CMDR LOCAL", rendered)

    def test_dispatch_command_routes_through_backend(self) -> None:
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )

        app._dispatch_command("commands", skip_delay=True)

        self.assertEqual(backend.dispatched_commands, [("commands", True)])

    def test_action_open_history_routes_through_backend(self) -> None:
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )

        app.action_open_history()

        self.assertEqual(backend.opened_replay_browser, 1)

    def test_resume_execute_selected_routes_through_backend(self) -> None:
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._resume_entries = [
            ReplaySelection(
                entry=CommandHistoryEntry(raw="jump", command="jump", timestamp="1"),
                label="jump",
                detail="jump",
            )
        ]

        app._resume_execute_selected()

        self.assertEqual(backend.closed_replay_browser, 1)
        self.assertEqual(backend.replayed_entries, [("jump", False, False)])

    def test_trade_route_picker_enter_dispatches_haul_route_command(self) -> None:
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
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
        self.assertEqual(backend.dispatched_commands, [("haul route 2", None)])

    def test_trade_route_picker_escape_closes_without_dispatch(self) -> None:
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
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
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
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
        self.assertEqual(backend.dispatched_commands, [("dest TSONGORIS", None)])

    def test_replay_open_arrow_keys_route_selection_through_backend(self) -> None:
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        app._resume_open = True

        up_event = _KeyEventStub("up")
        down_event = _KeyEventStub("down")

        app.on_key(up_event)
        app.on_key(down_event)

        self.assertTrue(up_event.prevented)
        self.assertTrue(down_event.prevented)
        self.assertEqual(backend.replay_selection_offsets, [-1, 1])

    def test_blank_input_submission_reaches_backend_during_destination_prompt(self) -> None:
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        input_stub = _InputStub()
        app.query_one = lambda selector, widget_type=None: input_stub if selector == "#cmd" else _RenderHarnessApp.query_one(app, selector, widget_type)  # type: ignore[method-assign]
        app._dest_prompt_destination = "Sol"

        class _SubmittedEvent:
            def __init__(self, input_widget) -> None:
                self.value = ""
                self.input = input_widget

        app.on_input_submitted(_SubmittedEvent(input_stub))

        self.assertEqual(backend.submitted_inputs, [""])
        self.assertEqual(input_stub.value, "")

    def test_blank_enter_key_submits_prompt_default_value_path(self) -> None:
        snapshot = snapshot_from_app(self.app)
        backend = _IntentRecorderBackend(snapshot)
        app = _RenderHarnessApp(
            _make_context(Path(self.tmpdir.name)),
            backend=backend,
        )
        input_stub = _InputStub()
        app.query_one = lambda selector, widget_type=None: input_stub if selector == "#cmd" else _RenderHarnessApp.query_one(app, selector, widget_type)  # type: ignore[method-assign]
        app._dest_prompt_destination = "Sol"
        event = _KeyEventStub("enter")

        app.on_key(event)

        self.assertTrue(event.prevented)
        self.assertEqual(backend.submitted_inputs, [""])
        self.assertEqual(input_stub.value, "")


if __name__ == "__main__":
    unittest.main()
