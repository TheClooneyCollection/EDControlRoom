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
    PathsConfig,
    RuntimeConfig,
    ScreenConfig,
    TTSConfig,
)
from edap.control_room.backend import ControlRoomBackend, LocalControlRoomBackend
from edap.control_room.app import ControlRoomApp
from edap.control_room.history import resume_detail, resume_label
from edap.control_room.models import ReplaySelection
from edap.control_room.protocol import ActivityLogEntry, snapshot_from_app
from edap.control_room.protocol.events import ActivityLogAppendedEvent, AnnouncementEvent
from edap.control_room.protocol.snapshot import ControlRoomSnapshot
from edap.control_room.protocol.sink import ControlRoomEventSink
from edap.control_room_state import CommandHistoryEntry, ControlRoomState
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
            market_buy_hold_seconds_per_ton=0.01,
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

    def write(self, content, **kwargs) -> None:
        self.writes.append((content, kwargs))


class _StaticWidgetStub:
    def __init__(self) -> None:
        self.updated = None
        self.border_title = ""

    def update(self, content) -> None:
        self.updated = content


class _OptionListStub:
    def __init__(self) -> None:
        self.highlighted = 0


class _RenderHarnessApp(_ProtocolHarnessApp):
    def __init__(self, ctx: RuntimeContext, *, backend: ControlRoomBackend | None = None) -> None:
        self._status_widget = _StaticWidgetStub()
        self._haul_widget = _StaticWidgetStub()
        self._market_widget = _StaticWidgetStub()
        self._resume_list_widget = _OptionListStub()
        super().__init__(ctx) if backend is None else ControlRoomApp.__init__(self, ctx, backend=backend)
        self._activity_widget = _ActivityLogStub()

    def query_one(self, selector: str, widget_type=None):  # type: ignore[override]
        if selector == "#activity":
            return self._activity_widget
        if selector == "#status":
            return self._status_widget
        if selector == "#haul":
            return self._haul_widget
        if selector == "#market":
            return self._market_widget
        if selector == "#resume-list":
            return self._resume_list_widget
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
        self.opened_replay_browser = 0
        self.closed_replay_browser = 0
        self.replayed_entries: list[tuple[str, bool, bool]] = []

    def dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        self.dispatched_commands.append((raw, skip_delay))

    def open_replay_browser(self) -> None:
        self.opened_replay_browser += 1

    def close_replay_browser(self) -> None:
        self.closed_replay_browser += 1

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

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        self.activity_messages.append(entry.message_text)

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        self.announcement_ids.append(event.announcement_id)


class ControlRoomProtocolSnapshotTests(unittest.TestCase):
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
        self.assertEqual(snapshot.server_status.server_version, "1.2.3")
        self.assertEqual(snapshot.server_status.runtime_platform, "macos")
        self.assertFalse(snapshot.server_status.bindings_loaded)
        self.assertEqual(snapshot.server_status.capability_names, ["snapshot", "announcement_stream"])
        self.assertEqual(snapshot.active_operator.client_name if snapshot.active_operator else None, "observer-1")

    def test_log_records_protocol_activity_entry_and_snapshot_uses_it_by_default(self) -> None:
        self.app._log("[yellow]Docked at Jameson Memorial[/]")

        self.assertEqual(len(self.app._protocol_activity_log), 1)
        entry = self.app._protocol_activity_log[0]
        self.assertEqual(entry.message_text, "Docked at Jameson Memorial")

        snapshot = snapshot_from_app(self.app)
        self.assertEqual(len(snapshot.activity_log), 1)
        self.assertEqual(snapshot.activity_log[0].message_text, "Docked at Jameson Memorial")

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
        self.assertEqual(received[0].entry.message_text, "Observer ready")

    def test_local_backend_forwards_events_to_external_sink(self) -> None:
        recorder = _SinkRecorder()
        self.app._protocol_event_sink = recorder

        self.app._log("[green]Observer ready[/]")
        self.app._announce_tts(AnnouncementId.ARRIVAL, system_name="Sol")

        self.assertEqual(recorder.activity_messages, ["Observer ready"])
        self.assertEqual(recorder.announcement_ids, ["arrival"])

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


if __name__ == "__main__":
    unittest.main()
