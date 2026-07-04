from __future__ import annotations

import asyncio
from dataclasses import replace
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room import (
    ControlRoomApp,
    _ALL_ROUTINE_ACTIONS,
    _build_log_text,
    _cargo_summary_lines,
    main,
)
from edap.actions import ActionDispatchResult
from edap.binding_lookup import build_binding_lookup
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
from edap.control_room import error_text
from edap.control_room import commands as control_room_commands
from edap.control_room import prompts as control_room_prompts
from edap.control_room.app import ActivityLog, _JOURNAL_ARTIFACT_LOG_FLUSH_EVERY, _detect_lan_host
from edap.control_room.backend import ControlRoomBackendEventHandler
from edap.control_room.failure_messages import describe_routine_failure
from edap.control_room.events import apply_ship_event
from edap.control_room import rendering as control_room_rendering
from edap.control_room.models import HaulStats, MarketData, PromptState, ShipState, TradeRoutesData
from edap.control_room.protocol import ActivityLogEntry
from edap.control_room_state import CommandHistoryEntry
from edap.routines import RoutineResult
from edap.runtime import ResolvedPath, RuntimeContext
from edap.timing import TimingChannelConfig, TimingConfig, TimingSampler
from edap.tts import AnnouncementId, NullSpeechBackend, TTSAnnouncer
from edap.control_room.workers import PendingRoutineCancelled, RoutineCancelled, run_routine_thread
from edap.haul_config import DEFAULT_HAUL_CONFIG_PATH
from edap.inara.trade_routes import TradeRoute, TradeRouteSearchResult
from edap.platform.input.base import InputTargetState
from edap.version import GitHubRelease
from rich.text import Text
from textual.widgets import Static


def _make_timing_config() -> TimingConfig:
    channel = TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.0)
    return TimingConfig(enabled=False, distribution="log_normal", delay=channel, hold=channel, typing=channel)


def _make_config(journal_dir: Path, *, activity_log_max_lines: int = 2000) -> AppConfig:
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
            activity_log_max_lines=activity_log_max_lines,
            command_delay_seconds=0.0,
            status_refresh_seconds=2.0,
        ),
        tts=TTSConfig(enabled=False, title="captain", disabled_messages=(), phrases={}),
    )


def _make_context(
    journal_dir: Path,
    *,
    activity_log_max_lines: int = 2000,
    config_path: Path | None = None,
    used_example_config_fallback: bool = False,
    input_controller=None,
) -> RuntimeContext:
    resolved = ResolvedPath(
        configured={"path": str(journal_dir), "status": "ok", "reason": "test journal dir"},
        auto_detected={"path": str(journal_dir), "status": "ok", "reason": "test journal dir"},
        effective={"path": str(journal_dir), "status": "ok", "source": "configured", "reason": "test journal dir"},
    )
    return RuntimeContext(
        config=_make_config(
            journal_dir,
            activity_log_max_lines=activity_log_max_lines,
        ),
        game_paths=None,
        journal=resolved,
        bindings=resolved,
        input_controller=input_controller,
        screen_capture=None,
        timing_sampler=TimingSampler(_make_timing_config()),
        binding_lookup=None,
        config_path=config_path or journal_dir / "config.toml",
        used_example_config_fallback=used_example_config_fallback,
    )


class _FakeWorker:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class _InputControllerStub:
    def __init__(self) -> None:
        self._target = InputTargetState(platform="macos", mode="foreground")

    def current_target(self) -> InputTargetState:
        return self._target

    def set_foreground_target(self) -> InputTargetState:
        self._target = InputTargetState(platform="macos", mode="foreground")
        return self._target

    def set_pid_target(self, pid: int) -> InputTargetState:
        self._target = InputTargetState(platform="macos", mode="pid", pid=pid)
        return self._target

    def set_hwnd_target(self, hwnd: int) -> InputTargetState:
        raise RuntimeError("macOS does not support hwnd-targeted input.")

    def auto_target(self, process_name: str = "EliteDangerous64.exe", *, prefer: str = "pid") -> InputTargetState:
        if prefer == "hwnd":
            raise RuntimeError("macOS does not support hwnd-targeted input.")
        self._target = InputTargetState(platform="macos", mode="pid", pid=4242, process_name=process_name)
        return self._target


class _FakeVersionSource:
    def __init__(
        self,
        *,
        current_version: str = "9.9.9",
        latest_release: GitHubRelease | None = None,
    ) -> None:
        self.current_version = current_version
        self.latest_release = latest_release

    def get_current_version(self) -> str:
        return self.current_version

    def fetch_latest_github_release(self) -> GitHubRelease | None:
        return self.latest_release


class _HarnessApp(ControlRoomApp):
    def __init__(self, ctx: RuntimeContext, *, activity_log_max_lines: int | None = None) -> None:
        self.version_source = _FakeVersionSource()
        super().__init__(
            ctx,
            activity_log_max_lines=activity_log_max_lines,
            version_source=self.version_source,
        )
        self._journal_artifact_log_path = ctx.config.control_room.state_file.parent / "control-room-artifact.log"
        self.logged: list[str] = []
        self.exit_calls = 0
        self._command_input = _InputStub()

    def _log(self, msg: str) -> None:
        self.logged.append(msg)

    def call_from_thread(self, callback, *args, **kwargs):  # type: ignore[override]
        return callback(*args, **kwargs)

    def exit(self, result=None, return_code: int = 0, message=None) -> None:
        self.exit_calls += 1

    def _finalize_shutdown(self) -> None:
        if self._shutdown_finalized:
            return
        self._shutdown_finalized = True
        self.exit()

    def _refresh_market(self) -> None:  # type: ignore[override]
        return None

    def _refresh_trade_routes(self) -> None:  # type: ignore[override]
        return None

    def _refresh_haul_stats(self) -> None:  # type: ignore[override]
        return None

    def _refresh_status(self) -> None:  # type: ignore[override]
        return None

    def _show_resume_picker(self) -> None:  # type: ignore[override]
        if not self._saved_state.history:
            self._log("[dim]No saved command history yet.[/]")
            return
        self._resume_open = True
        self._resume_entries = self._filtered_resume_entries()

    def query_one(self, selector: str, widget_type=None):  # type: ignore[override]
        if selector == "#cmd":
            return self._command_input
        return super().query_one(selector, widget_type)


class _WorkerGroupStub:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str]] = []

    def cancel_group(self, app, group: str) -> None:
        self.calls.append((app, group))


class _ShutdownHarnessApp(ControlRoomApp):
    def __init__(self, ctx: RuntimeContext) -> None:
        self.version_source = _FakeVersionSource()
        super().__init__(ctx, version_source=self.version_source)
        self._journal_artifact_log_path = ctx.config.control_room.state_file.parent / "control-room-artifact.log"
        self.exit_calls = 0

    def exit(self, result=None, return_code: int = 0, message=None) -> None:
        self.exit_calls += 1

    def _finalize_shutdown(self) -> None:
        if self._shutdown_finalized:
            return
        self._shutdown_finalized = True
        if self._journal_artifact_log_handle is not None:
            self._flush_journal_artifact_log()
            self._journal_artifact_log_handle.close()
            self._journal_artifact_log_handle = None
            self._journal_artifact_log_pending_writes = 0
        self._tts.close()
        self.exit()


class _InputStub:
    def __init__(self) -> None:
        self.id = "cmd"
        self.placeholder = ""
        self.value = ""
        self.cursor_position = 0


class _KeyEventStub:
    def __init__(self, key: str, *, character: str | None = None) -> None:
        self.key = key
        self.character = character
        self.prevented = False

    def prevent_default(self) -> None:
        self.prevented = True


class _ActivityLogStub:
    def __init__(self, *, scroll_y: float = 0.0, max_scroll_y: float = 0.0) -> None:
        self.border_title = ""
        self.scroll_y = scroll_y
        self.max_scroll_y = max_scroll_y
        self.auto_scroll = True
        self.writes: list[dict[str, object]] = []

    @property
    def auto_follow_paused(self) -> bool:
        return not self.auto_scroll

    def write(self, content, **kwargs) -> None:
        self.writes.append({"content": content, **kwargs})


class _TimerStub:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _HarnessActivityLog(ActivityLog):
    def __init__(self, *, max_scroll_y: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self._test_max_scroll_y = max_scroll_y

    @property
    def max_scroll_y(self) -> float:
        return self._test_max_scroll_y


class _FakeTTS:
    def __init__(self) -> None:
        self.calls: list[tuple[AnnouncementId, dict[str, object]]] = []
        self.commander_name: str | None = None

    def announce(self, message_id: AnnouncementId, **values: object) -> None:
        self.calls.append((message_id, values))

    def set_commander_name(self, name: str | None) -> None:
        self.commander_name = name

    def render_announcement(self, message_id: AnnouncementId, **values: object) -> str | None:
        return None

    def close(self) -> None:
        return None


class _RemoteBackendStub:
    def __init__(self) -> None:
        self.interrupt_calls = 0

    def subscribe_events(self, handler: ControlRoomBackendEventHandler):
        def unsubscribe() -> None:
            return None

        return unsubscribe

    def publish_activity_log(self, entry) -> None:
        return None

    def publish_announcement(self, event) -> None:
        return None

    def publish_data_refresh(self) -> None:
        return None

    def submit_input(self, raw: str) -> None:
        return None

    def interrupt_active_routine(self) -> None:
        self.interrupt_calls += 1

    def exit_detaches_remote_session(self) -> bool:
        return True

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

    def handle_haul_prompt(self, value: str) -> None:
        return None

    def handle_haul_confirm_prompt(self, value: str) -> None:
        return None

    def load_trade_route(self, route, *, raw_command: str | None = None) -> None:
        return None


class _ArtifactLogHandleStub:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.flush_calls = 0
        self.close_calls = 0
        self.closed = False

    def write(self, value: str) -> int:
        self.parts.append(value)
        return len(value)

    def flush(self) -> None:
        self.flush_calls += 1

    def close(self) -> None:
        self.close_calls += 1
        self.closed = True

    def getvalue(self) -> str:
        return "".join(self.parts)


class _EventSinkStub:
    def __init__(self) -> None:
        self.data_refresh_count = 0

    def publish_activity_log(self, entry) -> None:
        return None

    def publish_announcement(self, event) -> None:
        return None

    def publish_data_refresh(self) -> None:
        self.data_refresh_count += 1


class ControlRoomCliTests(unittest.TestCase):
    def test_detect_lan_host_uses_udp_route_address(self) -> None:
        class FakeSocket:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                pass

            def connect(self, address) -> None:
                self.address = address

            def getsockname(self):
                return ("192.168.1.42", 53621)

        fake_socket = FakeSocket()
        with patch("edap.control_room.app.socket.socket", return_value=fake_socket), patch(
            "edap.control_room.app.socket.getaddrinfo",
            return_value=[],
        ):
            self.assertEqual(_detect_lan_host(), "192.168.1.42")
        self.assertEqual(fake_socket.address, ("8.8.8.8", 80))

    def test_detect_lan_host_falls_back_to_hostname_address(self) -> None:
        with patch("edap.control_room.app.socket.socket") as socket_factory, patch(
            "edap.control_room.app.socket.getaddrinfo",
            return_value=[
                (None, None, None, None, ("127.0.0.1", 0)),
                (None, None, None, None, ("10.0.0.12", 0)),
            ],
        ):
            socket_factory.return_value.__enter__.return_value.connect.side_effect = OSError("no route")
            self.assertEqual(_detect_lan_host(), "10.0.0.12")

    def test_serve_lan_passes_detected_host(self) -> None:
        with patch("sys.argv", ["control_room.py", "serve", "--lan", "--token", "1001"]), patch(
            "edap.control_room.app._detect_lan_host",
            return_value="192.168.1.42",
        ), patch("edap.control_room.server.serve.serve_observer_mode") as serve:
            main()

        serve.assert_called_once_with(
            config_path="config.toml",
            host="192.168.1.42",
            port=8765,
            access_token="1001",
        )

    def test_serve_lan_rejects_explicit_host(self) -> None:
        argv = ["control_room.py", "serve", "--lan", "--host", "0.0.0.0", "--token", "1001"]
        with patch("sys.argv", argv), patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit) as raised:
            main()

        self.assertEqual(raised.exception.code, 2)


class ControlRoomCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.app = _HarnessApp(_make_context(Path(self.tmpdir.name)))
        self.addCleanup(self._close_artifact_log)

    def _close_artifact_log(self) -> None:
        if self.app._journal_artifact_log_handle is not None:
            self.app._journal_artifact_log_handle.close()
            self.app._journal_artifact_log_handle = None

    def test_commands_lists_supported_commands(self) -> None:
        self.app._dispatch_command("commands")

        output = "\n".join(self.app.logged)
        self.assertIn("Command: commands", output)
        self.assertIn("Supported commands:", output)
        self.assertIn("dock", output)
        self.assertIn("help", output)
        self.assertIn("q | quit | exit", output)

    def test_help_for_alias_resolves_to_canonical_command(self) -> None:
        self.app._dispatch_command("help set_dest")

        output = "\n".join(self.app.logged)
        self.assertIn("dest", output)
        self.assertIn("dest <system>", output)
        self.assertIn("NavRoute.json", output)

    def test_help_unknown_topic_reports_error(self) -> None:
        self.app._dispatch_command("help mystery")

        output = "\n".join(self.app.logged)
        self.assertIn("Command: help mystery", output)
        self.assertIn("Unknown help topic: mystery", output)

    def test_help_haul_mentions_load_profile(self) -> None:
        self.app._dispatch_command("help haul")

        output = "\n".join(self.app.logged)
        self.assertIn("haul load", output)
        self.assertIn("haul.toml", output)

    def test_help_home_mentions_config_update_flow(self) -> None:
        self.app._dispatch_command("help home")

        output = "\n".join(self.app.logged)
        self.assertIn("home set <system>", output)
        self.assertIn("config.toml", output)

    def test_quit_command_exits_immediately_without_active_routine(self) -> None:
        self.app._dispatch_command("quit")

        self.assertTrue(self.app._shutdown_requested)
        self.assertEqual(self.app.exit_calls, 1)

    def test_request_interrupt_cancels_active_routine_without_exiting(self) -> None:
        worker = _FakeWorker()
        self.app._routine_active = True
        self.app._routine_worker = worker

        self.app.action_request_interrupt()

        self.assertFalse(self.app._shutdown_requested)
        self.assertTrue(worker.cancelled)
        self.assertEqual(self.app.exit_calls, 0)

    def test_request_interrupt_on_haul_schedules_stop_after_run(self) -> None:
        worker = _FakeWorker()
        self.app._routine_active = True
        self.app._routine_worker = worker
        self.app._active_routine_name = "haul"
        self.app._tts = _FakeTTS()

        self.app.action_request_interrupt()

        self.assertFalse(self.app._shutdown_requested)
        self.assertFalse(worker.cancelled)
        self.assertTrue(self.app._haul_stop_requested)
        self.assertIn(
            (AnnouncementId.HAUL_STOP_AFTER_RUN, {}),
            self.app._tts.calls,
        )
        self.assertIn("stop after this run", "\n".join(self.app.logged))

    def test_request_interrupt_on_haul_cancels_immediately_when_stop_already_pending(self) -> None:
        worker = _FakeWorker()
        self.app._routine_active = True
        self.app._routine_worker = worker
        self.app._active_routine_name = "haul"
        self.app._haul_stop_requested = True
        self.app._tts = _FakeTTS()

        self.app.action_request_interrupt()

        self.assertFalse(self.app._shutdown_requested)
        self.assertTrue(worker.cancelled)
        self.assertFalse(self.app._haul_stop_requested)
        self.assertIn((AnnouncementId.HAUL_CANCELLED, {}), self.app._tts.calls)
        self.assertIn("cancelling haul immediately", "\n".join(self.app.logged))

    def test_request_interrupt_without_worker_clears_stale_routine_state(self) -> None:
        self.app._routine_active = True
        self.app._active_routine_name = "dock"

        self.app.action_request_interrupt()

        self.assertFalse(self.app._routine_active)
        self.assertIsNone(self.app._active_routine_name)
        self.assertIn("no active routine to cancel", "\n".join(self.app.logged))

    def test_request_interrupt_cancels_active_haul_prompt(self) -> None:
        self.app._haul_params = {"station_1": "Jameson Memorial"}
        self.app._haul_prompt_defaults = {"station_1": "Jameson Memorial"}
        self.app._haul_prompt_step = "station_1_system"
        self.app._haul_prompt_raw_command = "haul gold"
        self.app._haul_prompt_skip_delay = True
        self.app._command_input.placeholder = "station 1 system..."
        self.app._command_input.value = "Sol"

        self.app.action_request_interrupt()

        self.assertEqual(self.app._haul_params, {})
        self.assertEqual(self.app._haul_prompt_defaults, {})
        self.assertEqual(self.app._haul_prompt_step, "")
        self.assertEqual(self.app._haul_prompt_raw_command, "")
        self.assertFalse(self.app._haul_prompt_skip_delay)
        self.assertEqual(self.app._command_input.placeholder, self.app._default_command_placeholder)
        self.assertEqual(self.app._command_input.value, "")
        self.assertIn("cancelling haul prompt", "\n".join(self.app.logged))

    def test_pending_sigint_cancels_active_routine_without_exiting(self) -> None:
        worker = _FakeWorker()
        self.app._routine_active = True
        self.app._routine_worker = worker

        self.app.request_sigint()
        self.app._drain_pending_sigint()

        self.assertFalse(self.app._sigint_pending)
        self.assertFalse(self.app._shutdown_requested)
        self.assertTrue(worker.cancelled)
        self.assertEqual(self.app.exit_calls, 0)

    def test_pending_sigint_does_not_exit_when_idle(self) -> None:
        self.app.request_sigint()

        self.app._drain_pending_sigint()

        self.assertFalse(self.app._sigint_pending)
        self.assertFalse(self.app._shutdown_requested)
        self.assertEqual(self.app.exit_calls, 0)
        self.assertIn("no active routine to cancel", "\n".join(self.app.logged))

    def test_clear_routine_publishes_protocol_data_refresh(self) -> None:
        sink = _EventSinkStub()
        self.app._protocol_external_event_sink = sink
        self.app._routine_active = True
        self.app._active_routine_name = "dock"

        self.app._clear_routine()

        self.assertFalse(self.app._routine_active)
        self.assertEqual(sink.data_refresh_count, 1)

    def test_request_exit_requires_second_press_before_shutdown(self) -> None:
        self.app.action_request_exit()

        self.assertFalse(self.app._shutdown_requested)
        self.assertEqual(self.app.exit_calls, 0)
        self.assertTrue(self.app._exit_requested_once)

        self.app.action_request_exit()

        self.assertTrue(self.app._shutdown_requested)
        self.assertEqual(self.app.exit_calls, 1)

    def test_remote_exit_prompt_defaults_to_detach_without_cancelling(self) -> None:
        backend = _RemoteBackendStub()
        app = _HarnessApp(_make_context(Path(self.tmpdir.name)))
        app._backend = backend
        app._routine_active = True

        app.action_request_exit()
        app.action_request_exit()

        self.assertTrue(app._exit_prompt_active)
        self.assertEqual(
            app._command_input.placeholder,
            "Enter = leave routine running | cancel = stop routine and exit | no = stay",
        )

        app._handle_exit_prompt_input("")

        self.assertEqual(backend.interrupt_calls, 0)
        self.assertTrue(app._shutdown_requested)
        self.assertEqual(app.exit_calls, 1)

    def test_remote_exit_prompt_can_cancel_remote_routine_before_exit(self) -> None:
        backend = _RemoteBackendStub()
        app = _HarnessApp(_make_context(Path(self.tmpdir.name)))
        app._backend = backend
        app._routine_active = True

        app.action_request_exit()
        app.action_request_exit()
        app._handle_exit_prompt_input("cancel")

        self.assertEqual(backend.interrupt_calls, 1)
        self.assertTrue(app._shutdown_requested)
        self.assertEqual(app.exit_calls, 1)

    def test_remote_exit_prompt_can_be_aborted(self) -> None:
        backend = _RemoteBackendStub()
        app = _HarnessApp(_make_context(Path(self.tmpdir.name)))
        app._backend = backend
        app._routine_active = True

        app.action_request_exit()
        app.action_request_exit()
        app._handle_exit_prompt_input("no")

        self.assertEqual(backend.interrupt_calls, 0)
        self.assertFalse(app._shutdown_requested)
        self.assertEqual(app.exit_calls, 0)
        self.assertIn("Exit cancelled", "\n".join(app.logged))

    def test_bootstrap_ship_state_reads_balance_and_cargo_from_status_json(self) -> None:
        journal_dir = Path(self.tmpdir.name)
        (journal_dir / "Journal.240101000000.01.log").write_text(
            json.dumps({
                "event": "LoadGame",
                "Commander": "VRYAE",
                "Ship": "type6",
                "FuelLevel": 16.0,
                "FuelCapacity": 32.0,
            }) + "\n" + json.dumps({
                "event": "Loadout",
                "Ship": "type6",
                "CargoCapacity": 460,
            }) + "\n" + json.dumps({
                "event": "Location",
                "Docked": True,
                "StarSystem": "HIP 58412",
                "StationName": "Pawelczyk Dock",
                "FuelLevel": 16.0,
                "FuelCapacity": 32.0,
            }) + "\n",
            encoding="utf-8",
        )
        (journal_dir / "Status.json").write_text(
            json.dumps({
                "Flags": 1,
                "Fuel": {"FuelMain": 16.0, "FuelReservoir": 0.5},
                "Cargo": 24,
                "Balance": 123456789,
                "Destination": {
                    "System": "Achenar",
                    "Body": "Dawes Hub",
                    "Name": "Dawes Hub",
                },
            }),
            encoding="utf-8",
        )
        (journal_dir / "Cargo.json").write_text(
            json.dumps({
                "Inventory": [
                    {"Name": "gold", "Name_Localised": "Gold", "Count": 5},
                    {"Name": "silver", "Name_Localised": "Silver", "Count": 7},
                ]
            }),
            encoding="utf-8",
        )

        self.app._bootstrap_ship_state()

        self.assertEqual(self.app._ship.commander, "VRYAE")
        self.assertEqual(self.app._ship.system, "HIP 58412")
        self.assertEqual(self.app._ship.credits, 123456789)
        self.assertEqual(self.app._ship.cargo_count, 24)
        self.assertEqual(self.app._ship.cargo_capacity, 460)
        self.assertEqual(self.app._ship.destination_system, "Achenar")
        self.assertEqual(self.app._ship.destination_body, "Dawes Hub")
        self.assertEqual(self.app._ship.destination_name, "Dawes Hub")
        self.assertEqual(len(self.app._ship.cargo_inventory), 2)

    def test_bootstrap_ship_state_syncs_commander_name_into_tts(self) -> None:
        journal_dir = Path(self.tmpdir.name)
        (journal_dir / "Journal.240101000000.01.log").write_text(
            json.dumps({"event": "LoadGame", "Commander": "VRYAE"}) + "\n",
            encoding="utf-8",
        )
        self.app._tts = _FakeTTS()

        self.app._bootstrap_ship_state()

        self.assertEqual(self.app._tts.commander_name, "VRYAE")

    def test_bootstrap_ship_state_reads_commander_from_commander_event(self) -> None:
        journal_dir = Path(self.tmpdir.name)
        (journal_dir / "Journal.240101000000.01.log").write_text(
            json.dumps({"event": "Commander", "Name": "VRYAE"}) + "\n",
            encoding="utf-8",
        )

        self.app._bootstrap_ship_state()

        self.assertEqual(self.app._ship.commander, "VRYAE")

    def test_sync_status_state_refreshes_destination_without_journal_event(self) -> None:
        journal_dir = Path(self.tmpdir.name)
        (journal_dir / "Status.json").write_text(
            json.dumps({
                "Flags": 0,
                "Destination": {
                    "System": "Shinrarta Dezhra",
                    "Body": "Jameson Memorial",
                    "Name": "Jameson Memorial",
                },
            }),
            encoding="utf-8",
        )

        self.app._sync_status_state()

        self.assertEqual(self.app._ship.destination_system, "Shinrarta Dezhra")
        self.assertEqual(self.app._ship.destination_body, "Jameson Memorial")
        self.assertEqual(self.app._ship.destination_name, "Jameson Memorial")

    def test_sync_status_state_refreshes_cargo_manifest_without_journal_event(self) -> None:
        journal_dir = Path(self.tmpdir.name)
        self.app._ship.cargo_count = 461
        self.app._ship.cargo_inventory = []
        (journal_dir / "Status.json").write_text(
            json.dumps({"Flags": 0, "Cargo": 461}),
            encoding="utf-8",
        )
        (journal_dir / "Cargo.json").write_text(
            json.dumps(
                {
                    "Inventory": [
                        {"Name": "bertrandite", "Name_Localised": "Bertrandite", "Count": 461},
                    ]
                }
            ),
            encoding="utf-8",
        )

        self.app._sync_status_state()

        self.assertEqual(self.app._ship.cargo_count, 461)
        self.assertEqual(
            self.app._ship.cargo_inventory,
            [{"Name": "bertrandite", "Name_Localised": "Bertrandite", "Count": 461}],
        )

    def test_status_markup_shows_destination_summary(self) -> None:
        ship = ShipState(
            system="Sol",
            status="in_supercruise",
            destination_system="Achenar",
            destination_body="Dawes Hub",
            destination_name="Dawes Hub",
        )

        markup = control_room_rendering.status_markup(ship)

        self.assertIn("Destination", markup)
        self.assertIn("Achenar / Dawes Hub / Dawes Hub", markup)
        self.assertIn("\n[dim]Destination[/]  [yellow]Achenar / Dawes Hub / Dawes Hub[/]", markup)

    def test_market_markup_shows_zero_demand_sell_rows_with_sell_price(self) -> None:
        market = MarketData(
            station="Pawelczyk Dock",
            system="HIP 58412",
            timestamp="2026-06-08T20:09:46Z",
            items=[
                {
                    "Category": "Foods",
                    "Name": "foodcartridges",
                    "Name_Localised": "Food Cartridges",
                    "Demand": 0,
                    "DemandBracket": 0,
                    "SellPrice": 1929,
                }
            ],
        )

        markup = control_room_rendering.market_markup(market, None, side="sell")

        self.assertIn("SELL TO MARKET", markup)
        self.assertIn("Food Cartridges", markup)
        self.assertIn("0", markup)
        self.assertIn("1,929", markup)

    def test_market_markup_keeps_sell_rows_plain_name_sorted(self) -> None:
        market = MarketData(
            station="Pawelczyk Dock",
            system="HIP 58412",
            timestamp="2026-06-08T20:09:46Z",
            items=[
                {
                    "Category": "Foods",
                    "Name": "foodcartridges",
                    "Name_Localised": "Food Cartridges",
                    "Demand": 0,
                    "DemandBracket": 0,
                    "SellPrice": 1929,
                },
                {
                    "Category": "Metals",
                    "Name": "gold",
                    "Name_Localised": "Gold",
                    "Demand": 12,
                    "DemandBracket": 1,
                    "SellPrice": 10000,
                },
            ],
        )

        markup = control_room_rendering.market_markup(market, None, side="sell")

        self.assertLess(markup.index("Food Cartridges"), markup.index("Gold"))

    def test_market_markup_renders_only_selected_side(self) -> None:
        market = MarketData(
            station="Pawelczyk Dock",
            system="HIP 58412",
            timestamp="2026-06-08T20:09:46Z",
            items=[
                {
                    "Category": "Foods",
                    "Name": "foodcartridges",
                    "Name_Localised": "Food Cartridges",
                    "Stock": 15,
                    "BuyPrice": 1500,
                    "Demand": 0,
                    "DemandBracket": 0,
                    "SellPrice": 1929,
                }
            ],
        )

        buy_markup = control_room_rendering.market_markup(market, None, side="buy")
        sell_markup = control_room_rendering.market_markup(market, None, side="sell")

        self.assertIn("BUY FROM MARKET", buy_markup)
        self.assertNotIn("SELL TO MARKET", buy_markup)
        self.assertIn("SELL TO MARKET", sell_markup)
        self.assertNotIn("BUY FROM MARKET", sell_markup)

    def test_market_markup_labels_locked_market_as_pinned(self) -> None:
        market = MarketData(
            station="Pawelczyk Dock",
            system="HIP 58412",
            timestamp="2026-06-08T20:09:46Z",
            items=[{"Name": "gold", "Stock": 15, "BuyPrice": 10_000}],
            locked=True,
        )

        markup = control_room_rendering.market_markup(market, None, side="buy")

        self.assertIn("\\[PINNED]", markup)
        self.assertNotIn("\\[LOCKED]", markup)

    def test_fmt_cr_uses_billions_and_remaining_millions(self) -> None:
        self.assertEqual(
            control_room_rendering.fmt_cr(1_234_567_890),
            "1b 234.57M CR",
        )

    def test_haul_stats_markup_shows_session_and_live_profit(self) -> None:
        stats = HaulStats(
            station_1_buying="Aluminium",
            station_2_buying="Bertrandite",
            station_1="Pawelczyk Dock",
            station_2="Hutton Orbital",
            session_started_at=100.0,
            active=True,
            clean_run_active=True,
            current_run_started_at=160.0,
            current_run_profit=12_500_000,
            completed_runs=2,
            accumulated_profit=987_654_321,
            last_run_profit=300_000,
            last_run_elapsed_s=240.0,
            total_run_elapsed_s=600.0,
        )

        markup = control_room_rendering.haul_stats_markup(
            stats,
            current_balance=1_234_567_890,
            now_fn=lambda: 400.0,
        )

        rendered = Text.from_markup(markup).plain

        self.assertIn("Session", rendered)
        self.assertIn("05:00", rendered)
        self.assertIn("Profit", rendered)
        self.assertIn("1b 000.15M CR", rendered)
        self.assertIn("Balance", rendered)
        self.assertIn("1b 234.57M CR", rendered)

    def test_trade_route_detail_markup_surfaces_trip_and_hour_profit(self) -> None:
        markup = control_room_rendering.trade_route_detail_markup(
            TradeRoute(
                index=1,
                from_station="Fontana City",
                from_system="HIP 17597",
                to_station="Stronghold Carrier",
                to_system="HIP 17597",
                source_buy_commodity="Silver",
                target_buy_commodity="Robotics",
                from_station_distance="148 Ls",
                to_station_distance="215 Ls",
                distance_from_system="~167 Ly",
                route_distance="12.4 Ly",
                profit_per_unit="37,903 Cr",
                profit_per_trip="17,435,380 Cr",
                profit_per_hour="88,323,553 Cr",
                updated="4 minutes ago",
            ),
            system_name="HIP 17597",
            searched_at="2026-06-27T13:35:53Z",
            route_count=50,
        )

        rendered = Text.from_markup(markup)

        self.assertIn("Per trip", rendered.plain)
        self.assertIn("17,435,380 Cr", rendered.plain)
        self.assertIn("Per hour", rendered.plain)
        self.assertIn("88,323,553 Cr", rendered.plain)
        self.assertIn("From Fontana City (148 Ls) (HIP 17597)    To Stronghold Carrier (215 Ls) (HIP 17597)", rendered.plain)
        self.assertIn("Buy Silver    Return Robotics", rendered.plain)
        self.assertIn("Distance ~167 Ly    Route 12.4 Ly", rendered.plain)
        self.assertIn("Per unit 37,903 Cr", rendered.plain)
        self.assertIn("Per trip 17,435,380 Cr    Per hour 88,323,553 Cr", rendered.plain)

    def test_trade_route_option_label_prefixes_compact_per_hour_profit(self) -> None:
        label = control_room_rendering.trade_route_option_label(
            TradeRoute(
                index=1,
                from_station="Fontana City",
                from_system="HIP 17597",
                to_station="Stronghold Carrier",
                to_system="HIP 17597",
                source_buy_commodity="Silver",
                target_buy_commodity="Robotics",
                from_station_distance="148 Ls",
                to_station_distance="215 Ls",
                distance_from_system="~167 Ly",
                profit_per_unit="37,903 Cr",
                profit_per_hour="88,323,553 Cr",
            )
        )

        self.assertEqual(
            label,
            "[88.3m/h] 1. Fontana City -> Stronghold Carrier [stn 148 Ls/215 Ls | dist ~167 Ly | buy Silver | return Robotics | ppu 37,903 Cr]",
        )

    def test_load_market_json_seeds_ship_station_when_in_station(self) -> None:
        journal_dir = Path(self.tmpdir.name)
        (journal_dir / "Journal.240101000000.01.log").write_text(
            "\n".join(
                [
                    json.dumps({"event": "FSDJump", "StarSystem": "Col 285 Sector HD-F b13-1"}),
                    json.dumps({"event": "Docked", "StationName": "Pawelczyk Dock"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (journal_dir / "Market.json").write_text(
            json.dumps({
                "StationName": "Pawelczyk Dock",
                "StarSystem": "HIP 58412",
                "timestamp": "2026-06-07T21:10:39Z",
                "Items": [],
            }),
            encoding="utf-8",
        )

        self.app._bootstrap_ship_state()
        self.assertEqual(self.app._ship.status, "in_station")
        self.assertEqual(self.app._ship.station, "Pawelczyk Dock")
        self.assertEqual(self.app._ship.system, "Col 285 Sector HD-F b13-1")

        self.app._load_market_json()

        self.assertEqual(self.app._ship.station, "Pawelczyk Dock")
        self.assertEqual(self.app._ship.system, "Col 285 Sector HD-F b13-1")
        self.assertEqual(self.app._market.station, "Pawelczyk Dock")
        self.assertEqual(self.app._market.system, "Col 285 Sector HD-F b13-1")

    def test_load_market_json_does_not_seed_when_not_in_station(self) -> None:
        journal_dir = Path(self.tmpdir.name)
        (journal_dir / "Journal.240101000000.01.log").write_text(
            json.dumps({"event": "SupercruiseEntry"}) + "\n",
            encoding="utf-8",
        )
        (journal_dir / "Market.json").write_text(
            json.dumps({
                "StationName": "Pawelczyk Dock",
                "StarSystem": "HIP 58412",
                "timestamp": "2026-06-07T21:10:39Z",
                "Items": [],
            }),
            encoding="utf-8",
        )

        self.app._bootstrap_ship_state()
        self.app._load_market_json()

        self.assertFalse(self.app._ship.station)

    def test_handle_event_syncs_commander_name_into_tts(self) -> None:
        self.app._tts = _FakeTTS()

        self.app._handle_event({"event": "Commander", "Name": "VRYAE"})

        self.assertEqual(self.app._ship.commander, "VRYAE")
        self.assertEqual(self.app._tts.commander_name, "VRYAE")


class ControlRoomBindingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.app = _HarnessApp(_make_context(Path(self.tmpdir.name)))
        self.addCleanup(self._close_artifact_log)

    def _close_artifact_log(self) -> None:
        if self.app._journal_artifact_log_handle is not None:
            self.app._journal_artifact_log_handle.close()
            self.app._journal_artifact_log_handle = None

    def test_preloaded_actions_cover_mass_lock_escape(self) -> None:
        self.assertIn("SetSpeed100", _ALL_ROUTINE_ACTIONS)
        self.assertIn("UseBoostJuice", _ALL_ROUTINE_ACTIONS)

    def test_undock_command_uses_configured_timeouts(self) -> None:
        captured: dict[str, object] = {}

        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_undock(controls, watcher, **kwargs):
            captured["controls"] = controls
            captured["watcher"] = watcher
            captured["kwargs"] = kwargs
            return None

        with patch("edap.control_room.routines_station.undock", new=fake_undock):
            self.app._cmd_undock()

        self.assertEqual(captured["kwargs"]["undock_timeout_s"], 30.0)
        self.assertEqual(captured["kwargs"]["step_delay_s"], 0.3)

    def test_dock_command_passes_configured_supercruise_exit_settle(self) -> None:
        captured: dict[str, object] = {}

        self.app._controls = object()
        self.app._ship.status = "supercruise"
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_dock(controls, watcher, **kwargs):
            captured["controls"] = controls
            captured["watcher"] = watcher
            captured["kwargs"] = kwargs
            return None

        with patch("edap.control_room.routines_station.dock", new=fake_dock):
            self.app._cmd_dock()

        self.assertEqual(captured["kwargs"]["supercruise_exit_settle_s"], 3.0)
        self.assertEqual(captured["kwargs"]["step_delay_s"], 0.3)

    def test_buy_command_passes_tts_announcer_to_market_routine(self) -> None:
        captured: dict[str, object] = {}

        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_market_buy(controls, watcher, **kwargs):
            captured["controls"] = controls
            captured["watcher"] = watcher
            captured["kwargs"] = kwargs
            return None

        with patch("edap.control_room.routines_trade.market_buy", new=fake_market_buy):
            self.app._cmd_buy("aluminium 10")

        announce_fn = captured["kwargs"]["announce_fn"]
        self.assertIs(announce_fn.__self__, self.app)
        self.assertIs(announce_fn.__func__, self.app._announce_tts.__func__)
        self.assertEqual(captured["kwargs"]["buy_hold_segments"][0].function, "flat")
        self.assertEqual(captured["kwargs"]["buy_hold_segments"][1].function, "linear")
        self.assertEqual(captured["kwargs"]["critical_level_multiplier"], 10.0)

    def test_buy_command_defaults_multi_word_item_to_max(self) -> None:
        captured: dict[str, object] = {}

        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_market_buy(controls, watcher, **kwargs):
            captured["kwargs"] = kwargs
            return None

        with patch("edap.control_room.routines_trade.market_buy", new=fake_market_buy):
            self.app._cmd_buy("food cartridges")

        self.assertEqual(captured["kwargs"]["target"], "food cartridges")
        self.assertEqual(captured["kwargs"]["amount"], "MAX")

    def test_escape_command_calls_mass_lock_routine(self) -> None:
        captured: dict[str, object] = {}

        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._run_in_thread = lambda fn: fn()

        def fake_escape_mass_lock(controls, **kwargs):
            captured["controls"] = controls
            captured["kwargs"] = kwargs
            return None

        with patch("edap.control_room.routines_movement.escape_mass_lock", new=fake_escape_mass_lock):
            self.app._cmd_escape()

        self.assertEqual(captured["kwargs"]["boost_delay_s"], 5.0)
        self.assertEqual(captured["kwargs"]["step_delay_s"], 0.3)

    def test_boost_command_dispatches_three_boosts(self) -> None:
        controls = object()
        dispatch = ActionDispatchResult(action="UseBoostJuice", status="ok")
        captured: dict[str, object] = {}

        class _BoostControls:
            def boost(self, repeat: int = 1, hold_s: float | None = None) -> ActionDispatchResult:
                captured["repeat"] = repeat
                captured["hold_s"] = hold_s
                return dispatch

        self.app._controls = controls
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: _BoostControls()
        self.app._run_in_thread = lambda fn: fn()

        result = self.app._cmd_boost()

        self.assertIsNone(result)
        self.assertEqual(captured["repeat"], 3)
        self.assertIsNone(captured["hold_s"])
        self.assertIn("Boosting 3x...", self.app.logged)

    def test_boost_command_history_is_distinct_from_escape(self) -> None:
        called: list[str] = []
        self.app._cmd_boost = lambda **kwargs: called.append("boost")
        self.app._cmd_escape = lambda **kwargs: called.append("escape")

        self.app._dispatch_command("boost")
        self.app._dispatch_command("escape")

        self.assertEqual(called, ["boost", "escape"])
        self.assertEqual(self.app._saved_state.history[-2].command, "boost")
        self.assertEqual(self.app._saved_state.history[-1].command, "escape")

    def test_sell_all_falls_back_to_cargo_json_when_live_manifest_is_empty(self) -> None:
        cargo_path = Path(self.tmpdir.name) / "Cargo.json"
        cargo_path.write_text(json.dumps({
            "Inventory": [
                {"Name": "aluminium", "Name_Localised": "Aluminium", "Count": 12, "Stolen": 0},
            ]
        }))

        captured_targets: list[str] = []
        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()
        self.app._raise_if_worker_cancelled = lambda: None
        self.app.call_from_thread = lambda fn, *args, **kwargs: fn(*args, **kwargs)

        def fake_market_sell(controls, watcher, **kwargs):
            captured_targets.append(kwargs["target"])
            return RoutineResult(
                action="market_sell",
                dispatch=ActionDispatchResult(action="market_sell", status="ok"),
            )

        with patch("edap.control_room.routines_trade.market_sell", new=fake_market_sell):
            self.app._sell_all()

        output = "\n".join(self.app.logged)
        self.assertEqual(captured_targets, ["Aluminium"])
        self.assertIn("sell-all is using Cargo.json as a fallback", output)
        self.assertIn("Sell-all complete", output)
        self.assertNotIn("Nothing sellable in cargo", output)

    def test_sell_all_skips_stale_manifest_after_full_sell_event(self) -> None:
        captured_targets: list[str] = []
        self.app._ship.cargo_count = 4
        self.app._ship.cargo_inventory = [
            {"Name": "gold", "Name_Localised": "Gold", "Count": 4, "Stolen": 0},
        ]
        (Path(self.tmpdir.name) / "Cargo.json").write_text(
            json.dumps({"Inventory": []}),
            encoding="utf-8",
        )
        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()
        self.app._raise_if_worker_cancelled = lambda: None
        self.app.call_from_thread = lambda fn, *args, **kwargs: fn(*args, **kwargs)

        self.app._handle_event(
            {
                "event": "MarketSell",
                "Type": "gold",
                "Type_Localised": "Gold",
                "Count": 4,
                "TotalSale": 250_000,
            }
        )

        def fake_market_sell(controls, watcher, **kwargs):
            captured_targets.append(kwargs["target"])
            return RoutineResult(
                action="market_sell",
                dispatch=ActionDispatchResult(action="market_sell", status="ok"),
            )

        with patch("edap.control_room.routines_trade.market_sell", new=fake_market_sell):
            self.app._sell_all()

        output = "\n".join(self.app.logged)
        self.assertEqual(captured_targets, [])
        self.assertIn("Nothing sellable is in cargo right now", output)

    def test_haul_dispatch_does_not_require_starting_at_sell_station(self) -> None:
        captured: dict[str, object] = {}

        self.app._ship.status = "in_supercruise"
        self.app._ship.station = ""
        self.app._ship.system = "Sol"
        self.app._haul_params = {
            "station_1_buying": "Aluminium",
            "station_1": "Pawelczyk Dock",
            "station_1_system": "Sol",
            "station_2_buying": "Bertrandite",
            "station_2": "Trevithick Dock",
            "station_2_system": "Achenar",
            "galaxy_map_settle": "",
            "dock_timeout": "",
        }
        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_haul_loop(runtime, *, route, stop_requested_fn=None, **kwargs):
            captured["runtime"] = runtime
            captured["route"] = route
            captured["stop_requested_fn"] = stop_requested_fn
            captured["kwargs"] = kwargs
            return RoutineResult(
                action="haul_loop",
                dispatch=ActionDispatchResult(action="haul_loop", status="ok"),
            )

        with patch("edap.control_room.routines_haul.haul_loop_two_way", new=fake_haul_loop):
            self.app._dispatch_haul_loop()

        self.assertIn("runtime", captured)
        runtime = captured["runtime"]
        self.assertEqual(runtime.timing.undock_timeout_s, 30.0)
        self.assertEqual(runtime.timing.undock_no_track_timeout_s, 600.0)
        self.assertEqual(runtime.timing.max_hold_s, 10.0)
        self.assertEqual(len(runtime.market.buy_hold_segments), 3)
        self.assertEqual(runtime.market.buy_hold_segments[0].function, "flat")
        self.assertEqual(runtime.market.sell_quantity_restore_taps, 5)
        self.assertFalse(captured["stop_requested_fn"]())
        self.app._haul_stop_requested = True
        self.assertTrue(captured["stop_requested_fn"]())
        self.assertIn("Starting haul loop:", "\n".join(self.app.logged))
        self.assertEqual(self.app._active_routine_name, "haul")
        self.assertEqual(self.app._haul_stats.station_1_buying, "Aluminium")
        self.assertEqual(self.app._haul_stats.station_2_buying, "Bertrandite")
        self.assertTrue(self.app._haul_stats.resumed_mid_run)

    def test_haul_dispatch_defaults_station_1_to_current_station(self) -> None:
        captured: dict[str, object] = {}

        self.app._ship.status = "in_station"
        self.app._ship.station = "Mystery Base"
        self.app._ship.system = "Sol"
        self.app._haul_params = {
            "station_1_buying": "Aluminium",
            "station_1": "",
            "station_1_system": "",
            "station_2_buying": "Bertrandite",
            "station_2": "Pawelczyk Dock",
            "station_2_system": "Achenar",
            "galaxy_map_settle": "",
            "dock_timeout": "",
        }
        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_haul_loop(runtime, *, route, **kwargs):
            captured["route"] = route
            return RoutineResult(
                action="haul_loop",
                dispatch=ActionDispatchResult(action="haul_loop", status="ok"),
            )

        with patch("edap.control_room.routines_haul.haul_loop_two_way", new=fake_haul_loop):
            self.app._dispatch_haul_loop()

        self.assertEqual(captured["route"].station_1.station, "Mystery Base")
        self.assertEqual(captured["route"].station_1.system, "Sol")
        self.assertFalse(captured["route"].station_1.on_land)
        self.assertIn("Station 1 defaulting to current station", "\n".join(self.app.logged))

    def test_haul_dispatch_allows_empty_station_2_buying(self) -> None:
        captured: dict[str, object] = {}

        self.app._ship.status = "in_station"
        self.app._ship.station = "Pawelczyk Dock"
        self.app._ship.system = "Sol"
        self.app._haul_params = {
            "station_1_buying": "Aluminium",
            "station_1": "Pawelczyk Dock",
            "station_1_system": "Sol",
            "station_2_buying": "",
            "station_2": "Trevithick Dock",
            "station_2_system": "Achenar",
            "galaxy_map_settle": "",
            "dock_timeout": "",
        }
        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_haul_loop(runtime, *, route, **kwargs):
            captured["route"] = route
            return RoutineResult(
                action="haul_loop",
                dispatch=ActionDispatchResult(action="haul_loop", status="ok"),
            )

        with patch("edap.control_room.routines_haul.haul_loop_two_way", new=fake_haul_loop):
            self.app._dispatch_haul_loop()

        self.assertEqual(captured["route"].station_2.buy_commodity, "")
        self.assertIn("station 2 [cyan]Trevithick Dock[/]: [dim]no buy[/]", "\n".join(self.app.logged))

    def test_haul_load_dispatches_from_config_file(self) -> None:
        captured: dict[str, object] = {}
        config_path = Path(self.tmpdir.name) / "haul-profile.toml"
        config_path.write_text(
            """
[haul]
galaxy_map_settle = 4.5
dock_timeout = 900.0

[haul.station_1]
buying = "Aluminium"
name = "Pawelczyk Dock"
system = "Sol"

[haul.station_2]
buying = "Bertrandite"
name = "Trevithick Dock"
system = "Achenar"
on_land = true
""".strip(),
            encoding="utf-8",
        )

        self.app._ship.status = "in_supercruise"
        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_haul_loop(runtime, *, route, **kwargs):
            captured["runtime"] = runtime
            captured["route"] = route
            return RoutineResult(
                action="haul_loop",
                dispatch=ActionDispatchResult(action="haul_loop", status="ok"),
            )

        with patch("edap.control_room.routines_haul.haul_loop_two_way", new=fake_haul_loop):
            self.app._cmd_haul(f"load {config_path}", raw_command=f"haul load {config_path}")

        self.assertEqual(captured["route"].station_1.buy_commodity, "Aluminium")
        self.assertEqual(captured["route"].station_2.buy_commodity, "Bertrandite")
        self.assertEqual(captured["runtime"].timing.galaxy_map_settle_s, 4.5)
        self.assertEqual(captured["runtime"].timing.dock_timeout_s, 900.0)
        self.assertTrue(captured["route"].station_2.on_land)
        self.assertEqual(self.app._saved_state.history[-1].raw, f"haul load {config_path}")
        self.assertIn("Loaded haul config", "\n".join(self.app.logged))

    def test_haul_load_without_path_uses_default_haul_toml(self) -> None:
        captured_paths: list[Path] = []

        def fake_load(path=DEFAULT_HAUL_CONFIG_PATH):
            captured_paths.append(Path(path))
            return {
                "station_1_buying": "Aluminium",
                "station_1": "Pawelczyk Dock",
                "station_1_system": "Sol",
                "station_1_on_land": "false",
                "station_2_buying": "Bertrandite",
                "station_2": "Trevithick Dock",
                "station_2_system": "Achenar",
                "station_2_on_land": "false",
                "galaxy_map_settle": "2.0",
                "dock_timeout": "1200.0",
            }

        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_haul_loop(runtime, *, route, **kwargs):
            return RoutineResult(
                action="haul_loop",
                dispatch=ActionDispatchResult(action="haul_loop", status="ok"),
            )

        with patch("edap.control_room.routines_haul.load_haul_config", new=fake_load), patch(
            "edap.control_room.routines_haul.haul_loop_two_way",
            new=fake_haul_loop,
        ):
            self.app._cmd_haul("load", raw_command="haul load")

        self.assertEqual(captured_paths, [DEFAULT_HAUL_CONFIG_PATH])

    def test_haul_load_reports_missing_file(self) -> None:
        self.app._controls = object()
        self.app._cmd_haul("load missing-haul.toml", raw_command="haul load missing-haul.toml")

        output = "\n".join(self.app.logged)
        self.assertIn("Haul config file not found", output)

    def test_haul_search_uses_all_at_once_prompt_and_ship_cargo_default(self) -> None:
        self.app._ship.system = "Praea Euq AK-A d25"
        self.app._ship.cargo_capacity = 460
        self.app._controls = object()
        self.app._run_in_thread = lambda fn: fn()

        result = TradeRouteSearchResult(
            system_name="Praea Euq AK-A d25",
            query_url="https://inara.cz/elite/market-traderoutes/?ps1=Praea+Euq+AK-A+d25",
            searched_at="2026-06-22T11:00:00Z",
            routes=(
                TradeRoute(
                    index=1,
                    from_station="Savitskaya Orbital",
                    from_system="TSONGORIS",
                    to_station="Scully-Power Station",
                    to_system="IX",
                    route_distance="33.08 Ly",
                    profit_per_unit="45,485 Cr",
                    profit_per_hour="88,275,035 Cr",
                    updated="4 hours ago",
                ),
            ),
        )

        with patch("edap.control_room.routines_haul.search_trade_routes", return_value=result):
            self.app._cmd_haul("search", raw_command="haul search")
            self.assertEqual(self.app._prompt_state.haul_prompt_mode, "search")
            self.assertEqual(self.app._haul_prompt_step, "search_edit")
            self.assertIn("near_system='Praea Euq AK-A d25'", self.app._command_input.value)
            self.assertIn("cargo_capacity=460", self.app._command_input.value)
            self.app._handle_haul_prompt(self.app._command_input.value)

        self.assertEqual(self.app._trade_routes.system_name, "Praea Euq AK-A d25")
        self.assertEqual(len(self.app._trade_routes.routes), 1)
        self.assertFalse(self.app._trade_routes.loading)
        self.assertIsNone(self.app._trade_routes.error)
        self.assertTrue(self.app._trade_route_picker_open)
        self.assertEqual(self.app._selected_trade_route_index, 1)
        self.assertEqual(self.app._saved_state.history[-1].params["mode"], "search")
        self.assertEqual(self.app._saved_state.history[-1].params["near_system"], "Praea Euq AK-A d25")
        self.assertEqual(self.app._saved_state.history[-1].params["cargo_capacity"], "460")
        self.assertIn("Loaded 1 Inara route(s)", "\n".join(self.app.logged))

    def test_haul_search_accepts_any_for_max_station_distance(self) -> None:
        self.app._ship.system = "Ix"
        self.app._ship.cargo_capacity = 460
        self.app._controls = object()
        self.app._run_in_thread = lambda fn: fn()

        result = TradeRouteSearchResult(
            system_name="Ix",
            query_url="https://inara.cz/elite/market-traderoutes/?ps1=Ix&pi9=0",
            searched_at="2026-06-27T14:00:00Z",
            routes=(),
        )

        with patch("edap.control_room.routines_haul.search_trade_routes", return_value=result):
            self.app._cmd_haul("search", raw_command="haul search")
            self.app._handle_haul_prompt(
                "near_system=Ix cargo_capacity=460 max_route_distance_ly=500 "
                "max_price_age_hours=8 min_landing_pad=large max_station_distance_ls=any "
                "use_surface_stations=no min_supply=5000 min_demand=5000 "
                "include_round_trips=true order_by=best_profit_per_hour_estimate"
            )

        self.assertEqual(
            self.app._saved_state.history[-1].params["max_station_distance_ls"],
            "any",
        )
        self.assertIn("Max. station distance (Ls): [cyan]Any[/]", "\n".join(self.app.logged))

    def test_haul_search_reports_missing_system_when_current_unknown(self) -> None:
        self.app._controls = object()

        self.app._cmd_haul("search", raw_command="haul search")

        self.assertIn("haul search needs a system name", "\n".join(self.app.logged))

    def test_haul_search_home_uses_saved_home_system(self) -> None:
        self.app._config = replace(
            self.app._config,
            control_room=replace(
                self.app._config.control_room,
                home_system="Achenar",
            ),
        )

        self.app._cmd_haul("search home", raw_command="haul search home")

        self.assertEqual(self.app._prompt_state.haul_prompt_mode, "search")
        self.assertEqual(self.app._haul_prompt_step, "search_edit")
        self.assertIn("near_system=Achenar", self.app._command_input.value)
        self.assertEqual(self.app._prompt_state.haul_prompt_raw_command, "haul search home")

    def test_haul_search_home_requires_saved_home_system(self) -> None:
        self.app._cmd_haul("search home", raw_command="haul search home")

        self.assertIn("Home system is not set", "\n".join(self.app.logged))
        self.assertNotEqual(self.app._prompt_state.haul_prompt_mode, "search")

    def test_haul_search_url_fetches_directly(self) -> None:
        self.app._controls = object()
        self.app._run_in_thread = lambda fn: fn()

        result = TradeRouteSearchResult(
            system_name="Praea Euq AK-A d25",
            query_url="https://inara.cz/elite/market-traderoutes/?ps1=Praea+Euq+AK-A+d25&pi10=460",
            searched_at="2026-06-22T11:00:00Z",
            routes=(
                TradeRoute(
                    index=1,
                    from_station="Savitskaya Orbital",
                    from_system="TSONGORIS",
                    to_station="Scully-Power Station",
                    to_system="IX",
                ),
            ),
        )
        url = (
            "https://inara.cz/elite/market-traderoutes/?ps1=Praea+Euq+AK-A+d25"
            "&pi10=460&pi2=500&pi5=8&pi3=3&pi9=500&pi4=1&pi7=5000&pi12=5000&pi8=1&pi14=0&pi15=0&pi1=4"
        )

        with patch("edap.control_room.routines_haul.search_trade_routes", return_value=result):
            self.app._cmd_haul(f"search url {url}", raw_command=f"haul search url {url}")

        self.assertEqual(self.app._trade_routes.system_name, "Praea Euq AK-A d25")
        self.assertTrue(self.app._trade_route_picker_open)
        self.assertEqual(self.app._saved_state.history[-1].params["mode"], "search")
        self.assertEqual(self.app._saved_state.history[-1].params["near_system"], "Praea Euq AK-A d25")
        self.assertEqual(self.app._saved_state.history[-1].params["order_by"], "best_profit_per_hour_estimate")

    def test_haul_route_loads_trade_route_into_haul_prompt(self) -> None:
        self.app._trade_routes = TradeRoutesData(
            system_name="Praea Euq AK-A d25",
            routes=[
                TradeRoute(
                    index=2,
                    from_station="Savitskaya Orbital",
                    from_system="TSONGORIS",
                    to_station="Nyberg Vision",
                    to_system="NJOKUJINUN",
                    source_buy_commodity="Beryllium",
                    target_buy_commodity="Bauxite",
                )
            ],
        )

        self.app._cmd_haul("route 2", raw_command="haul route 2")

        self.assertEqual(self.app._haul_prompt_step, "station_1_buying")
        self.assertEqual(self.app._command_input.value, "Beryllium")
        self.assertEqual(self.app._prompt_state.haul_prompt_defaults["station_2_buying"], "Bauxite")
        self.assertEqual(self.app._prompt_state.haul_prompt_defaults["station_1"], "Savitskaya Orbital")
        self.assertEqual(self.app._prompt_state.haul_prompt_defaults["station_2"], "Nyberg Vision")

    def test_haul_dispatch_passes_on_land_flags(self) -> None:
        captured: dict[str, object] = {}

        self.app._ship.status = "in_station"
        self.app._haul_params = {
            "station_1_buying": "Aluminium",
            "station_1": "Pawelczyk Dock",
            "station_1_system": "Sol",
            "station_1_on_land": "false",
            "station_2_buying": "Bertrandite",
            "station_2": "Trevithick Dock",
            "station_2_system": "Achenar",
            "station_2_on_land": "true",
            "galaxy_map_settle": "",
            "dock_timeout": "",
        }
        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_haul_loop(runtime, *, route, **kwargs):
            captured["route"] = route
            return RoutineResult(
                action="haul_loop",
                dispatch=ActionDispatchResult(action="haul_loop", status="ok"),
            )

        with patch("edap.control_room.routines_haul.haul_loop_two_way", new=fake_haul_loop):
            self.app._dispatch_haul_loop()

        self.assertFalse(captured["route"].station_1.on_land)
        self.assertTrue(captured["route"].station_2.on_land)
        self.assertIn("station 2 landing: [cyan]on land[/]", "\n".join(self.app.logged))

    def test_multi_leg_haul_dispatch_loads_route_and_starts_routine(self) -> None:
        captured: dict[str, object] = {}
        definition = type(
            "_Def",
            (),
            {"route_name": "Fixture route", "total_legs": 2, "source_provider": "spansh"},
        )()

        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        def fake_multi_leg_haul(runtime, **kwargs):
            captured["kwargs"] = kwargs
            return RoutineResult(
                action="multi_leg_haul",
                dispatch=ActionDispatchResult(action="multi_leg_haul", status="ok"),
            )

        with patch("edap.control_room.routines_haul.load_multi_leg_haul_definition", return_value=definition), patch(
            "edap.control_room.routines_haul.multi_leg_haul",
            new=fake_multi_leg_haul,
        ):
            self.app._cmd_multi_leg_haul("fixture.json", raw_command="multi_leg_haul fixture.json")

        self.assertEqual(captured["kwargs"]["definition"], definition)
        self.assertEqual(self.app._active_routine_name, "multi_leg_haul")
        self.assertIn("Starting multi-leg haul:", "\n".join(self.app.logged))

    def test_multi_leg_haul_requires_source_argument(self) -> None:
        self.app._controls = object()
        self.app._cmd_multi_leg_haul("", raw_command="multi_leg_haul")

        self.assertIn("Usage: multi_leg_haul", "\n".join(self.app.logged))

    def test_haul_confirm_no_cancels_launch(self) -> None:
        self.app.query_one = lambda *args, **kwargs: _InputStub()  # type: ignore[method-assign]
        self.app._haul_confirm_buy_station = "Mystery Base"

        self.app._handle_haul_confirm_prompt("no")

        self.assertEqual(self.app._haul_confirm_buy_station, "")
        self.assertIn("Haul launch cancelled", "\n".join(self.app.logged))

    def test_record_history_entry_trims_to_configured_limit(self) -> None:
        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=2,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=self.app._config.control_room.command_delay_seconds,
            ),
        )

        self.app._record_history_entry(CommandHistoryEntry(raw="dock", command="dock", timestamp="1"))
        self.app._record_history_entry(CommandHistoryEntry(raw="jump", command="jump", timestamp="2"))
        self.app._record_history_entry(CommandHistoryEntry(raw="undock", command="undock", timestamp="3"))

        self.assertEqual([entry.raw for entry in self.app._saved_state.history], ["jump", "undock"])
        self.assertEqual(self.app._history, ["jump", "undock"])

    def test_saved_haul_defaults_use_explicit_default_haul(self) -> None:
        self.app._saved_state.default_haul = {
            "station_1_buying": "Aluminium",
            "station_2": "Hutton Orbital",
            "galaxy_map_settle": "5.0",
        }
        self.app._ship.station = "Jameson Memorial"
        self.app._ship.system = "Shinrarta Dezhra"

        defaults = self.app._saved_haul_defaults()

        self.assertEqual(defaults["station_1_buying"], "Aluminium")
        self.assertEqual(defaults["station_2"], "Hutton Orbital")
        self.assertEqual(defaults["station_1"], "Jameson Memorial")
        self.assertEqual(defaults["station_1_system"], "Shinrarta Dezhra")
        self.assertEqual(defaults["galaxy_map_settle"], "5.0")

    def test_saved_haul_defaults_seed_can_clear_saved_text(self) -> None:
        self.app._saved_state.default_haul = {
            "station_1_buying": "Aluminium",
            "station_2_buying": "Bertrandite",
        }

        defaults = self.app._saved_haul_defaults({"station_2_buying": ""})

        self.assertEqual(defaults["station_1_buying"], "Aluminium")
        self.assertEqual(defaults["station_2_buying"], "")

    def test_start_haul_prompt_prefills_existing_answers_into_input(self) -> None:
        input_stub = _InputStub()
        self.app.query_one = lambda *args, **kwargs: input_stub  # type: ignore[method-assign]
        self.app._saved_state.default_haul = {
            "station_1_buying": "Aluminium",
            "station_1": "Pawelczyk Dock",
        }

        self.app._start_haul_prompt(
            commodity="",
            prompt_for_commodity=True,
            raw_command="haul",
        )

        self.assertEqual(self.app._haul_prompt_step, "station_1_buying")
        self.assertEqual(input_stub.value, "Aluminium")
        self.assertEqual(input_stub.cursor_position, len("Aluminium"))

    def test_haul_prompt_blank_input_clears_prefilled_station_2_buying(self) -> None:
        input_stub = _InputStub()
        self.app.query_one = lambda *args, **kwargs: input_stub  # type: ignore[method-assign]

        self.app._start_haul_prompt(
            commodity="",
            prompt_for_commodity=True,
            seed={
                "station_1_buying": "Aluminium",
                "station_1": "Pawelczyk Dock",
                "station_1_system": "Sol",
                "station_1_on_land": "false",
                "station_2_buying": "Bertrandite",
                "station_2": "Trevithick Dock",
                "station_2_system": "Achenar",
            },
            raw_command="haul",
        )

        self.assertEqual(input_stub.value, "Aluminium")
        self.app._handle_haul_prompt("Aluminium")
        self.assertEqual(input_stub.value, "Pawelczyk Dock")
        self.app._handle_haul_prompt("Pawelczyk Dock")
        self.assertEqual(input_stub.value, "Sol")
        self.app._handle_haul_prompt("Sol")
        self.assertEqual(self.app._haul_prompt_step, "station_1_on_land")
        self.app._handle_haul_prompt("no")
        self.assertEqual(input_stub.value, "Bertrandite")

        self.app._handle_haul_prompt("")

        self.assertEqual(self.app._haul_params["station_2_buying"], "")
        self.assertEqual(self.app._haul_prompt_step, "station_2")
        self.assertEqual(input_stub.value, "Trevithick Dock")

    def test_filtered_resume_entries_uses_prefix_match(self) -> None:
        self.app._saved_state.history = [
            CommandHistoryEntry(raw="dock", command="dock", timestamp="1"),
            CommandHistoryEntry(raw="dest Sol", command="dest", timestamp="2"),
            CommandHistoryEntry(raw="dest Colonia", command="dest", timestamp="3"),
            CommandHistoryEntry(raw="sell Aluminium", command="sell", timestamp="4"),
        ]

        self.app._resume_filter = "dest "
        labels = [item.label for item in self.app._filtered_resume_entries()]

        self.assertEqual(len(labels), 2)
        self.assertIn("dest Colonia", labels[0])
        self.assertIn("dest Sol", labels[1])

    def test_filtered_resume_entries_empty_filter_returns_full_history(self) -> None:
        self.app._saved_state.history = [
            CommandHistoryEntry(raw="dock", command="dock", timestamp="1"),
            CommandHistoryEntry(raw="jump", command="jump", timestamp="2"),
        ]

        self.app._resume_filter = ""
        raws = [item.entry.raw for item in self.app._filtered_resume_entries()]

        self.assertEqual(raws, ["jump", "dock"])

    def test_log_lines_use_fold_wrap(self) -> None:
        line = _build_log_text("A" * 200, timestamp="2026-06-30T16:44:02Z")

        self.assertFalse(line.no_wrap)
        self.assertEqual(line.overflow, "fold")
        self.assertTrue(line.plain.startswith("16:44:02  "))

    def test_log_lines_require_valid_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "must include a timestamp"):
            _build_log_text("hello", timestamp="")

    def test_activity_log_auto_follows_when_not_paused(self) -> None:
        activity = _ActivityLogStub()
        self.app.query_one = lambda selector, widget_type=None: activity  # type: ignore[method-assign]

        ControlRoomApp._log(self.app, "hello")

        self.assertNotIn("scroll_end", activity.writes[-1])
        self.assertEqual(activity.border_title, "ACTIVITY")

    def test_activity_log_title_reflects_paused_auto_follow(self) -> None:
        activity = _ActivityLogStub()
        self.app.query_one = lambda selector, widget_type=None: activity  # type: ignore[method-assign]
        activity.auto_scroll = False

        self.app._refresh_activity_title()

        self.assertEqual(activity.border_title, "ACTIVITY • AUTO-FOLLOW PAUSED")

    def test_cargo_summary_lines_limits_to_top_three(self) -> None:
        lines = _cargo_summary_lines([
            {"Name": "gold", "Name_Localised": "Gold", "Count": 4},
            {"Name": "silver", "Name_Localised": "Silver", "Count": 10},
            {"Name": "palladium", "Name_Localised": "Palladium", "Count": 6},
            {"Name": "bertrandite", "Name_Localised": "Bertrandite", "Count": 2},
        ])

        self.assertEqual(lines, [
            "10t Silver",
            "6t Palladium",
            "4t Gold",
        ])

    def test_haul_stats_track_clean_cycle_profit_and_time(self) -> None:
        self.app._tts = _FakeTTS()
        self.app._ship.status = "in_station"
        self.app._ship.station = "Pawelczyk Dock"
        self.app._ship.credits = 1_000_000
        self.app._time_fn = lambda: 100.0
        self.app._start_haul_stats(
            station_1_buying="Aluminium",
            station_2_buying="Bertrandite",
            station_1="Pawelczyk Dock",
            station_2="Hutton Orbital",
        )

        self.assertTrue(self.app._haul_stats.waiting_for_station_1_departure)
        self.assertEqual(self.app._haul_stats.current_run_started_at, 100.0)

        self.app._handle_haul_event(
            {"event": "MarketBuy", "TotalCost": 100_000, "Count": 128},
            station_before="Pawelczyk Dock",
        )
        self.assertEqual(self.app._haul_stats.current_run_profit, -100_000)
        self.assertEqual(self.app._haul_stats.cargo_moved_t, 128)
        self.assertIsNone(self.app._haul_stats.current_run_started_at)

        self.app._time_fn = lambda: 110.0
        self.app._handle_haul_event({"event": "Undocked"}, station_before="Pawelczyk Dock")
        self.assertTrue(self.app._haul_stats.clean_run_active)
        self.assertEqual(self.app._haul_stats.current_run_started_at, 110.0)
        self.assertEqual(self.app._haul_stats.current_run_profit, -100_000)

        self.app._time_fn = lambda: 150.0
        self.app._handle_haul_event({"event": "MarketSell", "TotalSale": 250_000}, station_before="Hutton Orbital")
        self.assertEqual(self.app._haul_stats.current_run_profit, 150_000)

        self.app._time_fn = lambda: 200.0
        self.app._handle_haul_event(
            {"event": "MarketBuy", "TotalCost": 250_000, "Count": 64},
            station_before="Hutton Orbital",
        )
        self.assertEqual(self.app._haul_stats.current_run_profit, -100_000)
        self.assertEqual(self.app._haul_stats.cargo_moved_t, 192)

        self.app._time_fn = lambda: 310.0
        self.app._handle_haul_event({"event": "Docked", "StationName": "Pawelczyk Dock"}, station_before=None)
        self.assertTrue(self.app._haul_stats.docked_back_at_station_1)
        self.assertEqual(self.app._haul_stats.current_run_elapsed_s, 200.0)

        self.app._time_fn = lambda: 315.0
        self.app._handle_haul_event({"event": "MarketSell", "TotalSale": 400_000}, station_before="Pawelczyk Dock")
        self.assertEqual(self.app._haul_stats.completed_runs, 1)
        self.assertEqual(self.app._haul_stats.last_run_profit, 300_000)
        self.assertEqual(self.app._haul_stats.accumulated_profit, 300_000)
        self.assertEqual(self.app._haul_stats.last_run_elapsed_s, 200.0)
        self.assertIsNone(self.app._haul_stats.current_run_started_at)
        self.assertTrue(self.app._haul_stats.waiting_for_station_1_departure)
        self.assertIn(
            (AnnouncementId.ROUTE_COMPLETE, {"cycle_count": 1, "total_profit_short": "300 thousand credits"}),
            self.app._tts.calls,
        )

        self.app._time_fn = lambda: 320.0
        self.app._handle_haul_event({"event": "MarketBuy", "TotalCost": 125_000}, station_before="Pawelczyk Dock")
        self.assertEqual(self.app._haul_stats.current_run_profit, -125_000)

        self.app._handle_haul_event({"event": "Undocked"}, station_before="Pawelczyk Dock")
        self.assertTrue(self.app._haul_stats.clean_run_active)
        self.assertEqual(self.app._haul_stats.current_run_started_at, 320.0)
        self.assertEqual(self.app._haul_stats.current_run_profit, -125_000)

    def test_start_haul_stats_preserves_persisted_session_totals(self) -> None:
        self.app._ship.status = "in_station"
        self.app._ship.station = "Pawelczyk Dock"
        self.app._haul_stats.session_started_at = 25.0
        self.app._haul_stats.accumulated_profit = 1_500_000
        self.app._haul_stats.cargo_moved_t = 784
        self.app._haul_stats.completed_runs = 4
        self.app._haul_stats.total_run_elapsed_s = 1200.0
        self.app._haul_stats.last_run_profit = 350_000
        self.app._haul_stats.last_run_elapsed_s = 180.0
        self.app._time_fn = lambda: 100.0

        self.app._start_haul_stats(
            station_1_buying="Aluminium",
            station_2_buying="Bertrandite",
            station_1="Pawelczyk Dock",
            station_2="Hutton Orbital",
        )

        self.assertEqual(self.app._haul_stats.session_started_at, 25.0)
        self.assertEqual(self.app._haul_stats.accumulated_profit, 1_500_000)
        self.assertEqual(self.app._haul_stats.cargo_moved_t, 784)
        self.assertEqual(self.app._haul_stats.completed_runs, 4)
        self.assertEqual(self.app._haul_stats.total_run_elapsed_s, 1200.0)
        self.assertEqual(self.app._haul_stats.last_run_profit, 350_000)
        self.assertEqual(self.app._haul_stats.last_run_elapsed_s, 180.0)

    def test_haul_stats_log_ignored_station_1_sell_before_clean_departure(self) -> None:
        self.app._ship.status = "in_station"
        self.app._ship.station = "Pawelczyk Dock"
        self.app._time_fn = lambda: 100.0
        self.app._start_haul_stats(
            station_1_buying="Aluminium",
            station_2_buying="Bertrandite",
            station_1="Pawelczyk Dock",
            station_2="Hutton Orbital",
        )

        self.app._handle_haul_event({"event": "MarketSell", "TotalSale": 400_000}, station_before="Pawelczyk Dock")

        self.assertEqual(self.app._haul_stats.current_run_profit, 0)
        self.assertIn(
            "Ignoring station 1 sale for haul stats (discarding profit from prior run).",
            "\n".join(self.app.logged),
        )

    def test_haul_stats_ignore_partial_resume_until_next_clean_departure(self) -> None:
        self.app._ship.status = "in_supercruise"
        self.app._time_fn = lambda: 50.0
        self.app._start_haul_stats(
            station_1_buying="Aluminium",
            station_2_buying="Bertrandite",
            station_1="Pawelczyk Dock",
            station_2="Hutton Orbital",
        )

        self.assertTrue(self.app._haul_stats.resumed_mid_run)
        self.assertEqual(self.app._haul_stats.current_run_started_at, 50.0)

        self.app._time_fn = lambda: 200.0
        self.app._handle_haul_event({"event": "MarketSell", "TotalSale": 400_000}, station_before="Pawelczyk Dock")
        self.assertEqual(self.app._haul_stats.current_run_profit, 0)

        self.app._handle_haul_event({"event": "Docked", "StationName": "Pawelczyk Dock"}, station_before=None)
        self.assertTrue(self.app._haul_stats.waiting_for_station_1_departure)
        self.assertFalse(self.app._haul_stats.clean_run_active)
        self.assertEqual(self.app._haul_stats.current_run_elapsed_s, 150.0)
        self.assertEqual(self.app._haul_stats.completed_runs, 0)

        self.app._handle_haul_event({"event": "MarketBuy", "TotalCost": 175_000}, station_before="Pawelczyk Dock")
        self.assertEqual(self.app._haul_stats.current_run_profit, -175_000)
        self.assertIsNone(self.app._haul_stats.current_run_started_at)

        self.app._time_fn = lambda: 225.0
        self.app._handle_haul_event({"event": "Undocked"}, station_before="Pawelczyk Dock")
        self.assertTrue(self.app._haul_stats.clean_run_active)
        self.assertEqual(self.app._haul_stats.current_run_started_at, 225.0)
        self.assertEqual(self.app._haul_stats.current_run_profit, -175_000)

    def test_stop_haul_stats_announces_session_summary(self) -> None:
        self.app._tts = _FakeTTS()
        self.app._haul_stats.station_1_buying = "Aluminium"
        self.app._haul_stats.completed_runs = 2
        self.app._haul_stats.accumulated_profit = 1_250_000

        self.app._stop_haul_stats()

        self.assertIn(
            (AnnouncementId.SESSION_COMPLETE, {"cycle_count": 2, "total_profit_short": "1.2 million credits"}),
            self.app._tts.calls,
        )

    def test_handle_event_announces_destination_only(self) -> None:
        self.app._tts = _FakeTTS()

        self.app._handle_event({"event": "FSDTarget", "Name": "Achenar"})

        self.assertIn((AnnouncementId.DESTINATION_SET, {"system_name": "Achenar"}), self.app._tts.calls)

    def test_handle_event_does_not_announce_undocking_outside_haul(self) -> None:
        self.app._tts = _FakeTTS()
        self.app._ship.station = "Pawelczyk Dock"
        self.app._ship.status = "in_station"

        self.app._handle_event({"event": "Undocked", "StationName": "Pawelczyk Dock"})

        self.assertNotIn((AnnouncementId.UNDOCKING, {}), self.app._tts.calls)

    def test_handle_event_announces_undocking_during_active_haul(self) -> None:
        self.app._tts = _FakeTTS()
        self.app._ship.station = "Pawelczyk Dock"
        self.app._ship.status = "in_station"
        self.app._start_haul_stats(
            station_1_buying="Aluminium",
            station_2_buying="Bertrandite",
            station_1="Pawelczyk Dock",
            station_2="Hutton Orbital",
        )

        self.app._handle_event({"event": "Undocked", "StationName": "Pawelczyk Dock"})

        self.assertIn((AnnouncementId.UNDOCKING, {}), self.app._tts.calls)

    def test_handle_event_announces_sale_revenue_not_profit(self) -> None:
        self.app._tts = _FakeTTS()

        self.app._handle_event({"event": "MarketSell", "TotalSale": 250_000})

        self.assertIn(
            (AnnouncementId.SALE_PROFIT, {"revenue_short": "250 thousand credits"}),
            self.app._tts.calls,
        )

    def test_handle_event_market_sell_clears_manifest_when_cargo_reaches_zero(self) -> None:
        self.app._ship.cargo_count = 4
        self.app._ship.cargo_inventory = [
            {"Name": "gold", "Name_Localised": "Gold", "Count": 4, "Stolen": 0},
        ]
        (Path(self.tmpdir.name) / "Cargo.json").write_text(
            json.dumps({"Inventory": []}),
            encoding="utf-8",
        )

        self.app._handle_event(
            {
                "event": "MarketSell",
                "Type": "gold",
                "Type_Localised": "Gold",
                "Count": 4,
                "TotalSale": 250_000,
            }
        )

        self.assertEqual(self.app._ship.cargo_count, 0)
        self.assertEqual(self.app._ship.cargo_inventory, [])

    def test_handle_event_market_sell_reloads_cargo_manifest_from_json(self) -> None:
        self.app._ship.cargo_count = 8
        self.app._ship.cargo_inventory = [
            {"Name": "gold", "Name_Localised": "Gold", "Count": 8, "Stolen": 0},
        ]
        (Path(self.tmpdir.name) / "Cargo.json").write_text(
            json.dumps(
                {
                    "Inventory": [
                        {"Name": "silver", "Name_Localised": "Silver", "Count": 2, "Stolen": 0},
                    ]
                }
            ),
            encoding="utf-8",
        )

        self.app._handle_event(
            {
                "event": "MarketSell",
                "Type": "gold",
                "Type_Localised": "Gold",
                "Count": 6,
                "TotalSale": 250_000,
            }
        )

        self.assertEqual(self.app._ship.cargo_count, 2)
        self.assertEqual(
            self.app._ship.cargo_inventory,
            [{"Name": "silver", "Name_Localised": "Silver", "Count": 2, "Stolen": 0}],
        )

    def test_handle_event_market_buy_reloads_cargo_manifest_from_json(self) -> None:
        self.app._ship.cargo_count = 1
        self.app._ship.cargo_inventory = [
            {"Name": "gold", "Name_Localised": "Gold", "Count": 1, "Stolen": 0},
        ]
        (Path(self.tmpdir.name) / "Cargo.json").write_text(
            json.dumps(
                {
                    "Inventory": [
                        {"Name": "gold", "Name_Localised": "Gold", "Count": 1, "Stolen": 0},
                        {"Name": "silver", "Name_Localised": "Silver", "Count": 3, "Stolen": 0},
                    ]
                }
            ),
            encoding="utf-8",
        )

        self.app._handle_event(
            {
                "event": "MarketBuy",
                "Type": "silver",
                "Type_Localised": "Silver",
                "Count": 3,
                "TotalCost": 180_000,
            }
        )

        self.assertEqual(self.app._ship.cargo_count, 4)
        self.assertEqual(
            self.app._ship.cargo_inventory,
            [
                {"Name": "gold", "Name_Localised": "Gold", "Count": 1, "Stolen": 0},
                {"Name": "silver", "Name_Localised": "Silver", "Count": 3, "Stolen": 0},
            ],
        )

    def test_handle_event_appends_to_control_room_artifact_log(self) -> None:
        log_path = Path(self.tmpdir.name) / "control-room-artifact.log"
        self.app._journal_artifact_log_path = log_path
        self.app._handle_event({"event": "SupercruiseExit", "Body": "Wells Terminal"})
        if self.app._journal_artifact_log_handle is not None:
            self.app._journal_artifact_log_handle.close()
            self.app._journal_artifact_log_handle = None

        lines = log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0]), {"event": "SupercruiseExit", "Body": "Wells Terminal"})

    def test_debug_log_writes_control_room_debug_artifact(self) -> None:
        log_path = Path(self.tmpdir.name) / "control-room-debug.log"
        self.app._debug_artifact_log_path = log_path

        ControlRoomApp._debug_log(
            self.app,
            "trade_route_picker_refresh",
            route_count=50,
            first_label="[89.6m/h] 1. Fontana City -> Stronghold Carrier",
        )

        lines = log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["event"], "trade_route_picker_refresh")
        self.assertEqual(payload["route_count"], 50)
        self.assertEqual(
            payload["first_label"],
            "[89.6m/h] 1. Fontana City -> Stronghold Carrier",
        )

    def test_append_journal_event_defers_flush_until_batch_threshold(self) -> None:
        handle = _ArtifactLogHandleStub()
        self.app._journal_artifact_log_handle = handle

        self.app._append_journal_event({"event": "FSDTarget", "Name": "Achenar"})

        self.assertEqual(handle.flush_calls, 0)
        self.assertEqual(self.app._journal_artifact_log_pending_writes, 1)

        for index in range(_JOURNAL_ARTIFACT_LOG_FLUSH_EVERY - 1):
            self.app._append_journal_event({"event": "Scan", "BodyName": f"Body {index}"})

        self.assertEqual(handle.flush_calls, 1)
        self.assertEqual(self.app._journal_artifact_log_pending_writes, 0)

    def test_finalize_shutdown_flushes_pending_control_room_artifact_log_writes(self) -> None:
        app = _ShutdownHarnessApp(_make_context(Path(self.tmpdir.name)))
        app._tts = _FakeTTS()
        handle = _ArtifactLogHandleStub()
        app._journal_artifact_log_handle = handle
        app._journal_artifact_log_pending_writes = 2

        app._finalize_shutdown()

        self.assertEqual(handle.flush_calls, 1)
        self.assertEqual(handle.close_calls, 1)
        self.assertTrue(handle.closed)
        self.assertEqual(app.exit_calls, 1)
        self.assertEqual(app._journal_artifact_log_pending_writes, 0)

    def test_finalize_shutdown_closes_control_room_artifact_log(self) -> None:
        app = _ShutdownHarnessApp(_make_context(Path(self.tmpdir.name)))
        app._tts = _FakeTTS()
        app._journal_artifact_log_path = Path(self.tmpdir.name) / "control-room-artifact.log"

        app._append_journal_event({"event": "FSDTarget", "Name": "Achenar"})
        handle = app._journal_artifact_log_handle

        self.assertIsNotNone(handle)
        self.assertFalse(handle.closed)

        app._finalize_shutdown()

        self.assertIsNone(app._journal_artifact_log_handle)
        self.assertTrue(handle.closed)
        self.assertEqual(app.exit_calls, 1)


class ActivityLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_activity_log_accepts_explicit_max_lines(self) -> None:
        activity = ActivityLog(max_lines=17)

        self.assertEqual(activity.max_lines, 17)

    def test_control_room_defaults_activity_log_max_lines_from_config(self) -> None:
        app = ControlRoomApp(
            _make_context(Path(self.tmpdir.name), activity_log_max_lines=17)
        )

        self.assertEqual(app._activity_log_max_lines, 17)

    def test_control_room_injected_max_lines_override_config(self) -> None:
        app = ControlRoomApp(
            _make_context(Path(self.tmpdir.name), activity_log_max_lines=17),
            activity_log_max_lines=5,
        )

        self.assertEqual(app._activity_log_max_lines, 5)

    def test_manual_scroll_pauses_auto_follow_for_ten_seconds(self) -> None:
        timer = _TimerStub()
        changes: list[bool] = []
        activity = _HarnessActivityLog(max_scroll_y=10.0, on_pause_changed=changes.append)
        activity.set_timer = lambda delay, callback, *args, **kwargs: timer  # type: ignore[method-assign]
        activity.scroll_y = 4.0

        activity.sync_auto_follow_to_scroll_position()

        self.assertFalse(activity.auto_scroll)
        self.assertEqual(changes, [True])
        self.assertIs(activity._resume_timer, timer)

    def test_reaching_bottom_resumes_auto_follow_immediately(self) -> None:
        changes: list[bool] = []
        activity = _HarnessActivityLog(max_scroll_y=10.0, on_pause_changed=changes.append)
        activity.auto_scroll = False
        activity._resume_timer = _TimerStub()
        activity.scroll_y = 10.0

        activity.sync_auto_follow_to_scroll_position()

        self.assertTrue(activity.auto_scroll)
        self.assertEqual(changes, [False])
        self.assertIsNone(activity._resume_timer)

    def test_pause_resets_existing_resume_timer(self) -> None:
        first_timer = _TimerStub()
        second_timer = _TimerStub()
        activity = _HarnessActivityLog(max_scroll_y=10.0)
        timers = iter([first_timer, second_timer])
        activity.set_timer = lambda delay, callback, *args, **kwargs: next(timers)  # type: ignore[method-assign]
        activity.scroll_y = 4.0

        activity.sync_auto_follow_to_scroll_position()
        activity.sync_auto_follow_to_scroll_position()

        self.assertTrue(first_timer.stopped)
        self.assertIs(activity._resume_timer, second_timer)


class ControlRoomDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.app = _HarnessApp(_make_context(Path(self.tmpdir.name)))
        self.addCleanup(self._close_artifact_log)

    def _close_artifact_log(self) -> None:
        if self.app._journal_artifact_log_handle is not None:
            self.app._journal_artifact_log_handle.close()
            self.app._journal_artifact_log_handle = None

    def _last_history(self) -> CommandHistoryEntry | None:
        history = self.app._saved_state.history
        return history[-1] if history else None

    def test_unknown_verb_logs_warning_and_records_history(self) -> None:
        self.app._dispatch_command("frobnicate now")

        output = "\n".join(self.app.logged)
        self.assertIn("Unknown command: frobnicate now", output)
        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "frobnicate")
        self.assertEqual(entry.raw, "frobnicate now")
        self.assertEqual(entry.params, {"value": "now"})

    def test_invalid_buy_amount_records_history(self) -> None:
        self.app._controls = object()
        self.app._dispatch_command("buy aluminium 0")

        output = "\n".join(self.app.logged)
        self.assertIn("Invalid amount", output)
        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "buy")
        self.assertEqual(entry.raw, "buy aluminium 0")
        self.assertEqual(entry.params, {"target": "aluminium", "amount": None})

    def test_buy_multi_word_item_records_full_target_and_defaults_to_max(self) -> None:
        self.app._controls = object()
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_sleeper = lambda: (lambda _: None)
        self.app._make_watcher = lambda: object()
        self.app._run_in_thread = lambda fn: fn()

        captured: dict[str, object] = {}

        def fake_market_buy(controls, watcher, **kwargs):
            captured["kwargs"] = kwargs
            return None

        with patch("edap.control_room.routines_trade.market_buy", new=fake_market_buy):
            self.app._dispatch_command("buy food cartridges")

        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "buy")
        self.assertEqual(entry.raw, "buy food cartridges")
        self.assertEqual(entry.params, {"target": "food cartridges", "amount": "MAX"})
        self.assertEqual(captured["kwargs"]["target"], "food cartridges")
        self.assertEqual(captured["kwargs"]["amount"], "MAX")

    def test_verb_routing_is_case_insensitive(self) -> None:
        self.app._dispatch_command("HELP set_dest")

        output = "\n".join(self.app.logged)
        self.assertIn("dest <system>", output)
        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "help")

    def test_home_without_saved_system_reports_error(self) -> None:
        self.app._dispatch_command("home")

        output = "\n".join(self.app.logged)
        self.assertIn("Home system is not set", output)
        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "home")
        self.assertEqual(entry.raw, "home")

    def test_home_routes_to_saved_system(self) -> None:
        self.app._config = replace(
            self.app._config,
            control_room=replace(
                self.app._config.control_room,
                home_system="Achenar",
            ),
        )
        captured: dict[str, object] = {}

        def fake_cmd_dest(app, destination, *, skip_delay=False, raw_command=None):
            captured["destination"] = destination
            captured["skip_delay"] = skip_delay
            captured["raw_command"] = raw_command

        with patch("edap.control_room.routines_nav.cmd_dest", new=fake_cmd_dest):
            self.app._dispatch_command("home")

        self.assertEqual(captured["destination"], "Achenar")
        self.assertEqual(captured["raw_command"], "home")

    def test_dest_home_routes_to_saved_system(self) -> None:
        self.app._controls = object()
        self.app._config = replace(
            self.app._config,
            control_room=replace(
                self.app._config.control_room,
                home_system="Achenar",
            ),
        )

        self.app._dispatch_command("dest home")

        self.assertEqual(self.app._prompt_state.dest_prompt_destination, "Achenar")
        self.assertEqual(self.app._prompt_state.dest_prompt_raw_command, "dest home")

    def test_dest_home_requires_saved_home_system(self) -> None:
        self.app._controls = object()

        self.app._dispatch_command("dest home")

        output = "\n".join(self.app.logged)
        self.assertIn("Home system is not set", output)
        self.assertEqual(self.app._prompt_state.dest_prompt_destination, "")

    def test_home_set_updates_config_file_and_runtime_config(self) -> None:
        config_path = Path(self.tmpdir.name) / "config.toml"
        config_path.write_text(
            """
[paths]

[controls]

[screen]

[runtime]
""".strip() + "\n",
            encoding="utf-8",
        )
        self.app._config_path = config_path

        self.app._dispatch_command("home set Shinrarta Dezhra")

        self.assertEqual(self.app._config.control_room.home_system, "Shinrarta Dezhra")
        saved = config_path.read_text(encoding="utf-8")
        self.assertIn('home_system = "Shinrarta Dezhra"', saved)
        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "home")
        self.assertEqual(entry.params, {"mode": "set", "system": "Shinrarta Dezhra"})

    def test_home_set_without_argument_uses_current_system(self) -> None:
        config_path = Path(self.tmpdir.name) / "config.toml"
        config_path.write_text(
            """
[paths]

[controls]

[screen]

[runtime]
""".strip() + "\n",
            encoding="utf-8",
        )
        self.app._config_path = config_path
        self.app._ship.system = "Sol"

        self.app._dispatch_command("home set")

        self.assertEqual(self.app._config.control_room.home_system, "Sol")
        saved = config_path.read_text(encoding="utf-8")
        self.assertIn('home_system = "Sol"', saved)
        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "home")
        self.assertEqual(entry.params, {"mode": "set", "system": "Sol"})

    def test_home_set_without_argument_requires_known_current_system(self) -> None:
        self.app._ship.system = None

        self.app._dispatch_command("home set")

        output = "\n".join(self.app.logged)
        self.assertIn("Cannot infer a home system yet", output)
        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "home")
        self.assertEqual(entry.raw, "home set")

    def test_home_set_creates_repo_config_when_running_from_example_fallback(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            config_path = temp_root / "config.example.toml"
            config_path.write_text(
                """
[paths]

[controls]

[screen]

[runtime]
""".strip() + "\n",
                encoding="utf-8",
            )
            self.app._config_path = config_path
            self.app._config_loaded_from_example_fallback = True

            try:
                os.chdir(temp_root)
                self.app._dispatch_command("home set Sol")
            finally:
                os.chdir(original_cwd)

            created = temp_root / "config.toml"
            self.assertTrue(created.exists())
            self.assertIn('home_system = "Sol"', created.read_text(encoding="utf-8"))

    def test_history_alias_opens_replay_picker(self) -> None:
        self.app._saved_state.history = [
            CommandHistoryEntry(raw="dock", command="dock", timestamp="1"),
        ]

        self.app._dispatch_command("history")

        self.assertTrue(self.app._resume_open)
        entry = self._last_history()
        self.assertEqual(entry.command, "replay")

    def test_ctrl_r_opens_replay_picker_when_command_input_has_focus(self) -> None:
        self.app._saved_state.history = [
            CommandHistoryEntry(raw="dock", command="dock", timestamp="1"),
        ]
        event = _KeyEventStub("ctrl+r")

        self.app.on_key(event)

        self.assertTrue(event.prevented)
        self.assertTrue(self.app._resume_open)

    def test_replay_command_does_not_execute_selected_entry_from_same_enter(self) -> None:
        self.app._saved_state.history = [
            CommandHistoryEntry(raw="jump", command="jump", timestamp="1"),
        ]
        self.app._time_fn = lambda: 100.0

        class _SubmittedEvent:
            def __init__(self, input_widget) -> None:
                self.value = "replay"
                self.input = input_widget

        self.app.on_input_submitted(_SubmittedEvent(self.app._command_input))
        executions: list[str] = []
        self.app._resume_execute_selected = lambda: executions.append("executed")  # type: ignore[method-assign]

        first_enter = _KeyEventStub("enter")
        self.app.on_key(first_enter)

        self.assertTrue(first_enter.prevented)
        self.assertTrue(self.app._resume_open)
        self.assertEqual(executions, [])

        self.app._time_fn = lambda: 101.0
        second_enter = _KeyEventStub("enter")
        self.app.on_key(second_enter)

        self.assertTrue(second_enter.prevented)
        self.assertEqual(executions, ["executed"])

    def test_exit_alias_requests_shutdown(self) -> None:
        self.app._dispatch_command("exit")

        self.assertTrue(self.app._shutdown_requested)
        entry = self._last_history()
        self.assertEqual(entry.command, "quit")
        self.assertEqual(entry.raw, "exit")

    def test_blank_command_is_ignored(self) -> None:
        original_history_count = len(self.app._saved_state.history)

        control_room_commands.dispatch(self.app, "")

        self.assertEqual(len(self.app._saved_state.history), original_history_count)

    def test_verbose_on_toggles_state_and_records_history(self) -> None:
        self.app._dispatch_command("verbose on")

        self.assertTrue(self.app._verbose_controls)
        entry = self._last_history()
        self.assertEqual(entry.command, "verbose")
        self.assertEqual(entry.params, {"value": "on"})

    def test_instant_toggle_flips_runtime_mode_and_records_history(self) -> None:
        self.app._dispatch_command("instant")

        self.assertTrue(self.app._instant_mode)
        self.assertTrue(self.app._saved_state.instant_mode)
        entry = self._last_history()
        self.assertEqual(entry.command, "instant")
        self.assertEqual(entry.params, {"value": ""})
        self.assertIn("Instant mode on", "\n".join(self.app.logged))

    def test_instant_off_restores_configured_delay(self) -> None:
        self.app._instant_mode = True

        self.app._dispatch_command("instant off")

        self.assertFalse(self.app._instant_mode)
        self.assertFalse(self.app._saved_state.instant_mode)
        self.assertIn("Instant mode off", "\n".join(self.app.logged))

    def test_set_pid_auto_targets_default_process_name(self) -> None:
        self.app = _HarnessApp(_make_context(Path(self.tmpdir.name), input_controller=_InputControllerStub()))

        self.app._dispatch_command("set_pid")

        self.assertIn("Input target: pid 4242 (EliteDangerous64.exe)", "\n".join(self.app.logged))
        entry = self._last_history()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.command, "set_pid")

    def test_set_pid_foreground_clears_target(self) -> None:
        controller = _InputControllerStub()
        controller.set_pid_target(999)
        self.app = _HarnessApp(_make_context(Path(self.tmpdir.name), input_controller=controller))

        self.app._dispatch_command("set_pid foreground")

        self.assertIn("Input target: foreground window", "\n".join(self.app.logged))

    def test_set_hwnd_reports_platform_unsupported_error(self) -> None:
        self.app = _HarnessApp(_make_context(Path(self.tmpdir.name), input_controller=_InputControllerStub()))

        self.app._dispatch_command("set_hwnd")

        self.assertIn("does not support hwnd-targeted input", "\n".join(self.app.logged))

    def test_load_saved_state_restores_persisted_instant_mode(self) -> None:
        self.app._instant_mode = True
        self.app._save_saved_state()
        self.app._instant_mode = False

        self.app._load_saved_state()

        self.assertTrue(self.app._instant_mode)

    def test_load_saved_state_restores_persisted_session_summary(self) -> None:
        self.app._haul_stats.session_started_at = 100.0
        self.app._haul_stats.session_active = True
        self.app._haul_stats.accumulated_profit = 1_250_000
        self.app._haul_stats.completed_runs = 3
        self.app._haul_stats.total_run_elapsed_s = 900.0
        self.app._haul_stats.last_run_profit = 400_000
        self.app._haul_stats.last_run_elapsed_s = 240.0
        self.app._time_fn = lambda: 460.0
        self.app._save_saved_state()

        self.app._haul_stats = HaulStats()
        self.app._time_fn = lambda: 500.0

        self.app._load_saved_state()

        self.assertEqual(self.app._haul_stats.accumulated_profit, 1_250_000)
        self.assertEqual(self.app._haul_stats.completed_runs, 3)
        self.assertEqual(self.app._haul_stats.total_run_elapsed_s, 900.0)
        self.assertEqual(self.app._haul_stats.last_run_profit, 400_000)
        self.assertEqual(self.app._haul_stats.last_run_elapsed_s, 240.0)
        self.assertEqual(self.app._haul_stats.session_started_at, 140.0)

    def test_load_saved_state_clears_persisted_session_when_configured(self) -> None:
        self.app._haul_stats.session_started_at = 50.0
        self.app._haul_stats.accumulated_profit = 999_000
        self.app._time_fn = lambda: 200.0
        self.app._save_saved_state()
        self.app._haul_stats = HaulStats()
        self.app._config = replace(
            self.app._config,
            control_room=replace(
                self.app._config.control_room,
                clear_session_on_launch=True,
            ),
        )
        self.app._time_fn = lambda: 300.0

        self.app._load_saved_state()

        self.assertEqual(self.app._haul_stats.accumulated_profit, 0)
        self.assertEqual(self.app._haul_stats.completed_runs, 0)
        self.assertIsNone(self.app._haul_stats.last_run_profit)
        self.assertEqual(self.app._haul_stats.session_started_at, 300.0)
        self.assertIn("Cleared persisted haul session on launch.", "\n".join(self.app.logged))

    def test_log_startup_modes_reports_instant_mode_state(self) -> None:
        self.app._instant_mode = True

        self.app._log_startup_modes()

        self.assertIn("Instant mode on — control with: instant", "\n".join(self.app.logged))

    def test_new_session_clears_persisted_session_and_records_history(self) -> None:
        self.app._haul_stats.station_1_buying = "Aluminium"
        self.app._haul_stats.station_2_buying = "Bertrandite"
        self.app._haul_stats.station_1 = "Pawelczyk Dock"
        self.app._haul_stats.station_2 = "Hutton Orbital"
        self.app._haul_stats.active = True
        self.app._haul_stats.clean_run_active = True
        self.app._haul_stats.current_run_started_at = 100.0
        self.app._haul_stats.current_run_profit = 250_000
        self.app._haul_stats.session_started_at = 50.0
        self.app._haul_stats.accumulated_profit = 900_000
        self.app._haul_stats.cargo_moved_t = 640
        self.app._haul_stats.completed_runs = 2
        self.app._haul_stats.total_run_elapsed_s = 600.0
        self.app._haul_stats.last_run_profit = 450_000
        self.app._haul_stats.last_run_elapsed_s = 200.0
        self.app._time_fn = lambda: 300.0

        self.app._dispatch_command("new_session")

        self.assertEqual(self.app._haul_stats.session_started_at, 300.0)
        self.assertEqual(self.app._haul_stats.accumulated_profit, 0)
        self.assertEqual(self.app._haul_stats.cargo_moved_t, 0)
        self.assertEqual(self.app._haul_stats.current_run_profit, 0)
        self.assertEqual(self.app._haul_stats.completed_runs, 0)
        self.assertEqual(self.app._haul_stats.total_run_elapsed_s, 0.0)
        self.assertIsNone(self.app._haul_stats.last_run_profit)
        self.assertEqual(self.app._saved_state.session_profit, 0)
        self.assertIn("Started a new persisted haul session.", "\n".join(self.app.logged))
        entry = self._last_history()
        self.assertEqual(entry.command, "new_session")

    def test_clear_alias_clears_persisted_session_and_records_history(self) -> None:
        self.app._haul_stats.accumulated_profit = 123_000
        self.app._haul_stats.session_started_at = 50.0
        self.app._time_fn = lambda: 300.0

        self.app._dispatch_command("clear")

        self.assertEqual(self.app._haul_stats.accumulated_profit, 0)
        self.assertEqual(self.app._haul_stats.session_started_at, 300.0)
        entry = self._last_history()
        self.assertEqual(entry.command, "new_session")

    def test_stop_freezes_persisted_session_elapsed_time(self) -> None:
        self.app._haul_stats.session_started_at = 50.0
        self.app._haul_stats.session_active = True
        self.app._haul_stats.accumulated_profit = 123_000
        self.app._time_fn = lambda: 300.0

        self.app._dispatch_command("stop")

        self.assertIsNone(self.app._haul_stats.session_started_at)
        self.assertFalse(self.app._haul_stats.session_active)
        self.assertEqual(self.app._haul_stats.session_elapsed_s, 250.0)
        self.assertEqual(self.app._saved_state.session_elapsed_seconds, 250.0)
        self.assertFalse(self.app._saved_state.session_active)
        self.assertIn("Stopped the persisted haul session.", "\n".join(self.app.logged))
        entry = self._last_history()
        self.assertEqual(entry.command, "stop")

    def test_stop_refuses_while_haul_session_is_active(self) -> None:
        self.app._haul_stats.active = True
        self.app._haul_stats.session_started_at = 50.0
        self.app._haul_stats.session_active = True

        self.app._dispatch_command("stop")

        self.assertEqual(
            self.app._haul_stats.session_started_at,
            50.0,
        )
        self.assertTrue(self.app._haul_stats.session_active)
        self.assertIn("Stop the active haul before stopping the persisted session.", "\n".join(self.app.logged))
    def test_log_startup_modes_reports_input_target_when_backend_exists(self) -> None:
        self.app = _HarnessApp(_make_context(Path(self.tmpdir.name), input_controller=_InputControllerStub()))

        self.app._log_startup_modes()

        self.assertIn("Input target foreground window — control with: set_pid | set_hwnd", "\n".join(self.app.logged))
    def test_announce_startup_greeting_emits_tts_announcement(self) -> None:
        self.app._tts = _FakeTTS()

        self.app._announce_startup_greeting()

        self.assertIn((AnnouncementId.STARTUP_GREETING, {}), self.app._tts.calls)

    def test_mount_local_runtime_bootstraps_commander_before_startup_greeting(self) -> None:
        journal_dir = Path(self.tmpdir.name)
        (journal_dir / "Journal.240101000000.01.log").write_text(
            json.dumps({"event": "LoadGame", "Commander": "VRYAE"}) + "\n",
            encoding="utf-8",
        )
        ctx = _make_context(journal_dir)
        self.app = _HarnessApp(
            RuntimeContext(
                config=replace(
                    ctx.config,
                    tts=replace(
                        ctx.config.tts,
                        enabled=True,
                        title_mode="commander_name",
                        phrases={"startup_greeting": "Hello {title}"},
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
        )
        self.app._tts = TTSAnnouncer(
            self.app._config.tts,
            platform_name=self.app._config.runtime.platform,
            backend=NullSpeechBackend(),
        )
        self.app._build_controls = lambda: None
        self.app._log_bindings_status = lambda: None
        self.app._load_saved_state = lambda: None
        self.app._log_startup_modes = lambda: None
        self.app._start_update_check = lambda: None
        self.app._load_market_json = lambda: None
        self.app._refresh_status = lambda: None
        self.app._refresh_haul_stats = lambda: None
        self.app._refresh_market = lambda: None
        self.app._refresh_trade_routes = lambda: None
        self.app._start_watcher = lambda: None
        self.app.set_interval = lambda *args, **kwargs: None
        self.app.set_focus = lambda *args, **kwargs: None
        self.app._update_resume_detail = lambda: None

        self.app._mount_local_runtime()

        self.assertEqual(self.app._protocol_announcements[0].message_text, "Hello VRYAE")

    def test_log_current_version_reports_current_version(self) -> None:
        self.app._current_version = "1.7.1"

        self.app._log_current_version(is_latest=None)

        self.assertIn("Currently running version *v1.7.1* of EDControlRoom", "\n".join(self.app.logged))

    def test_log_current_version_reports_latest_version(self) -> None:
        self.app._current_version = "1.7.1"

        self.app._log_current_version(is_latest=True)

        self.assertIn(
            "Currently running latest version (*v1.7.1*) of EDControlRoom",
            "\n".join(self.app.logged),
        )

    def test_start_update_check_skips_when_disabled(self) -> None:
        self.app._config = AppConfig(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=self.app._config.control_room.command_delay_seconds,
                status_refresh_seconds=self.app._config.control_room.status_refresh_seconds,
                check_for_updates=False,
            ),
            tts=self.app._config.tts,
        )

        with patch.object(self.app, "_check_for_updates") as mock_check:
            self.app._start_update_check()

        mock_check.assert_not_called()
        self.assertIn(
            "Currently running version *v9.9.9* of EDControlRoom",
            "\n".join(self.app.logged),
        )

    def test_log_update_available_reports_newer_release(self) -> None:
        self.app._current_version = "1.7.1"

        self.app._log_update_available(
            GitHubRelease(
                tag_name="v1.8.0",
                name="",
                html_url="https://github.com/TheClooneyCollection/EDControlRoom/releases/tag/v1.8.0",
                published_at="2026-06-10T00:00:00Z",
            )
        )

        output = "\n".join(self.app.logged)
        self.assertIn("A newer EDControlRoom release is available: v1.8.0", output)
        self.assertIn("Currently running version *v1.7.1* of EDControlRoom", output)
        self.assertIn("releases/tag/v1.8.0", output)

    def test_log_bindings_status_reports_effective_bindings_file(self) -> None:
        bindings_path = Path(self.tmpdir.name) / "Custom.binds"
        resolved = ResolvedPath(
            configured={"path": str(bindings_path), "status": "ok", "reason": "test bindings file"},
            auto_detected={"path": str(bindings_path), "status": "ok", "reason": "test bindings file"},
            effective={
                "path": str(bindings_path),
                "status": "ok",
                "source": "configured",
                "reason": "test bindings file",
            },
        )
        self.app._ctx = RuntimeContext(
            config=self.app._ctx.config,
            game_paths=None,
            journal=self.app._ctx.journal,
            bindings=resolved,
            input_controller=None,
            screen_capture=None,
            timing_sampler=self.app._ctx.timing_sampler,
            binding_lookup=build_binding_lookup(bindings={}, actions=[]),
            config_path=self.app._ctx.config_path,
            used_example_config_fallback=self.app._ctx.used_example_config_fallback,
        )

        self.app._log_bindings_status()

        output = "\n".join(self.app.logged)
        self.assertIn(f"Bindings file: {bindings_path}", output)
        self.assertIn("source: configured", output)

    def test_log_bindings_status_warns_about_missing_mappings(self) -> None:
        bindings_path = Path(self.tmpdir.name) / "Custom.binds"
        resolved = ResolvedPath(
            configured={"path": str(bindings_path), "status": "ok", "reason": "test bindings file"},
            auto_detected={"path": str(bindings_path), "status": "ok", "reason": "test bindings file"},
            effective={
                "path": str(bindings_path),
                "status": "ok",
                "source": "configured",
                "reason": "test bindings file",
            },
        )
        lookup = build_binding_lookup(bindings={}, actions=["UI_Back", "SetSpeedZero"])
        self.app._ctx = RuntimeContext(
            config=self.app._ctx.config,
            game_paths=None,
            journal=self.app._ctx.journal,
            bindings=resolved,
            input_controller=None,
            screen_capture=None,
            timing_sampler=self.app._ctx.timing_sampler,
            binding_lookup=lookup,
            config_path=self.app._ctx.config_path,
            used_example_config_fallback=self.app._ctx.used_example_config_fallback,
        )

        self.app._log_bindings_status()

        output = "\n".join(self.app.logged)
        self.assertIn("Bindings warning", output)
        self.assertIn("UI_Back -> UI Back (General Controls > Interface Mode)", output)
        self.assertIn(
            "SetSpeedZero -> Set Speed to 0% (Ship Controls > Flight Throttle)",
            output,
        )

    def test_log_bindings_status_reports_joystick_only_binding_reason(self) -> None:
        bindings_path = Path(self.tmpdir.name) / "Custom.binds"
        resolved = ResolvedPath(
            configured={"path": str(bindings_path), "status": "ok", "reason": "test bindings file"},
            auto_detected={"path": str(bindings_path), "status": "ok", "reason": "test bindings file"},
            effective={
                "path": str(bindings_path),
                "status": "ok",
                "source": "configured",
                "reason": "test bindings file",
            },
        )
        lookup = build_binding_lookup(
            bindings={},
            missing_actions={
                "UseBoostJuice": "action has joystick/controller bindings, but none are keyboard bindings",
            },
            actions=["UseBoostJuice"],
        )
        self.app._ctx = RuntimeContext(
            config=self.app._ctx.config,
            game_paths=None,
            journal=self.app._ctx.journal,
            bindings=resolved,
            input_controller=None,
            screen_capture=None,
            timing_sampler=self.app._ctx.timing_sampler,
            binding_lookup=lookup,
            config_path=self.app._ctx.config_path,
            used_example_config_fallback=self.app._ctx.used_example_config_fallback,
        )

        self.app._log_bindings_status()

        output = "\n".join(self.app.logged)
        self.assertIn(
            "UseBoostJuice -> Engine Boost (Ship Controls > Flight Miscellaneous)",
            output,
        )
        self.assertIn("joystick/controller bindings", output)

    def test_log_bindings_status_ignores_unused_maneuver_mappings(self) -> None:
        bindings_path = Path(self.tmpdir.name) / "Custom.binds"
        resolved = ResolvedPath(
            configured={"path": str(bindings_path), "status": "ok", "reason": "test bindings file"},
            auto_detected={"path": str(bindings_path), "status": "ok", "reason": "test bindings file"},
            effective={
                "path": str(bindings_path),
                "status": "ok",
                "source": "configured",
                "reason": "test bindings file",
            },
        )
        lookup = build_binding_lookup(
            bindings={},
            actions=["RollLeftButton", "PitchUpButton", "YawLeftButton"],
        )
        self.app._ctx = RuntimeContext(
            config=self.app._ctx.config,
            game_paths=None,
            journal=self.app._ctx.journal,
            bindings=resolved,
            input_controller=None,
            screen_capture=None,
            timing_sampler=self.app._ctx.timing_sampler,
            binding_lookup=lookup,
            config_path=self.app._ctx.config_path,
            used_example_config_fallback=self.app._ctx.used_example_config_fallback,
        )

        self.app._log_bindings_status()

        output = "\n".join(self.app.logged)
        self.assertNotIn("Bindings warning", output)
        self.assertNotIn("RollLeftButton", output)
        self.assertNotIn("PitchUpButton", output)
        self.assertNotIn("YawLeftButton", output)

    def test_market_filter_sets_filter_and_records_raw_value(self) -> None:
        self.app._dispatch_command("market filter Aluminium")

        self.assertEqual(self.app._market_filter, "Aluminium")
        entry = self._last_history()
        self.assertEqual(entry.command, "market")
        self.assertEqual(entry.params, {"value": "filter Aluminium"})

    def test_market_lock_pins_display_to_current_market_and_keeps_matching_updates(self) -> None:
        market_path = Path(self.tmpdir.name) / "Market.json"
        market_path.write_text(
            json.dumps(
                {
                    "StationName": "Jameson Memorial",
                    "StarSystem": "Sol",
                    "MarketID": 128666762,
                    "timestamp": "2026-06-30T12:00:00Z",
                    "Items": [{"Name": "gold", "Stock": 42}],
                }
            ),
            encoding="utf-8",
        )
        self.app._load_market_json()
        self.app._sync_presented_market_from_current_data(force=True)

        self.assertEqual(self.app._market.station, "Jameson Memorial")
        self.assertEqual(self.app._presented_market.station, "Jameson Memorial")

        self.app._dispatch_command("market lock")

        market_path.write_text(
            json.dumps(
                {
                    "StationName": "Jameson Memorial",
                    "StarSystem": "Sol",
                    "MarketID": 128666762,
                    "timestamp": "2026-06-30T12:01:00Z",
                    "Items": [{"Name": "gold", "Stock": 84}],
                }
            ),
            encoding="utf-8",
        )
        self.app._market_mtime = None
        self.app._load_market_json()
        self.app._sync_presented_market_from_current_data()

        self.assertTrue(self.app._market.locked)
        self.assertEqual(self.app._market.station, "Jameson Memorial")
        self.assertEqual(self.app._market.items[0]["Stock"], 84)
        self.assertEqual(self.app._presented_market.station, "Jameson Memorial")
        self.assertEqual(self.app._presented_market.items[0]["Stock"], 84)

        market_path.write_text(
            json.dumps(
                {
                    "StationName": "Galileo",
                    "StarSystem": "Sol",
                    "MarketID": 3229359104,
                    "timestamp": "2026-06-30T12:02:00Z",
                    "Items": [{"Name": "silver", "Stock": 99}],
                }
            ),
            encoding="utf-8",
        )
        self.app._market_mtime = None
        self.app._load_market_json()
        self.app._sync_presented_market_from_current_data()

        self.assertTrue(self.app._market.locked)
        self.assertEqual(self.app._market.station, "Galileo")
        self.assertEqual(self.app._market.items[0]["Name"], "silver")
        self.assertEqual(self.app._presented_market.station, "Jameson Memorial")
        self.assertEqual(self.app._presented_market.items[0]["Name"], "gold")
        self.assertEqual(self.app._presented_market.items[0]["Stock"], 84)

        self.app._dispatch_command("market unlock")
        self.app._sync_presented_market_from_current_data()

        self.assertFalse(self.app._market.locked)
        self.assertEqual(self.app._presented_market.station, "Galileo")
        self.assertEqual(self.app._presented_market.items[0]["Name"], "silver")

    def test_typed_executable_command_waits_before_launch(self) -> None:
        delays: list[float] = []
        called: list[str] = []

        self.app._controls = object()
        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=5.0,
            ),
        )
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_watcher = lambda: object()
        self.app._make_sleeper = lambda: (lambda delay: delays.append(delay))
        self.app._run_in_thread = lambda fn: fn()

        def fake_jump(controls, watcher, **kwargs):
            called.append("jump")
            return None

        with patch("edap.control_room.routines_movement.jump", new=fake_jump):
            self.app._dispatch_command("jump")

        self.assertEqual(delays, [5.0])
        self.assertEqual(called, ["jump"])
        self.assertIn("Executing jump in 5.0s...", "\n".join(self.app.logged))
        self.assertIn("Starting jump sequence...", "\n".join(self.app.logged))

    def test_bang_prefixed_command_skips_delay_and_preserves_raw_history(self) -> None:
        delays: list[float] = []
        called: list[str] = []

        self.app._controls = object()
        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=5.0,
            ),
        )
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_watcher = lambda: object()
        self.app._make_sleeper = lambda: (lambda delay: delays.append(delay))
        self.app._run_in_thread = lambda fn: fn()

        def fake_jump(controls, watcher, **kwargs):
            called.append("jump")
            return None

        with patch("edap.control_room.routines_movement.jump", new=fake_jump):
            self.app._dispatch_command("!jump")

        self.assertEqual(delays, [])
        self.assertEqual(called, ["jump"])
        self.assertEqual(self._last_history().raw, "!jump")  # type: ignore[union-attr]
        self.assertNotIn("Executing jump in 5.0s...", "\n".join(self.app.logged))

    def test_instant_mode_skips_delay_without_bang_prefix(self) -> None:
        delays: list[float] = []
        called: list[str] = []

        self.app._controls = object()
        self.app._instant_mode = True
        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=5.0,
            ),
        )
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_watcher = lambda: object()
        self.app._make_sleeper = lambda: (lambda delay: delays.append(delay))
        self.app._run_in_thread = lambda fn: fn()

        def fake_jump(controls, watcher, **kwargs):
            called.append("jump")
            return None

        with patch("edap.control_room.routines_movement.jump", new=fake_jump):
            self.app._dispatch_command("jump")

        self.assertEqual(delays, [])
        self.assertEqual(called, ["jump"])
        self.assertNotIn("Executing jump in 5.0s...", "\n".join(self.app.logged))

    def test_replay_execute_uses_same_command_delay(self) -> None:
        delays: list[float] = []
        called: list[str] = []

        self.app._controls = object()
        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=5.0,
            ),
        )
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_watcher = lambda: object()
        self.app._make_sleeper = lambda: (lambda delay: delays.append(delay))
        self.app._run_in_thread = lambda fn: fn()

        def fake_jump(controls, watcher, **kwargs):
            called.append("jump")
            return None

        with patch("edap.control_room.routines_movement.jump", new=fake_jump):
            self.app._replay_history_entry(
                CommandHistoryEntry(raw="jump", command="jump", timestamp="1"),
                edit=False,
            )

        self.assertEqual(delays, [5.0])
        self.assertEqual(called, ["jump"])

    def test_replay_immediate_executes_without_prefixing_saved_history(self) -> None:
        delays: list[float] = []
        called: list[str] = []

        self.app._controls = object()
        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=5.0,
            ),
        )
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_watcher = lambda: object()
        self.app._make_sleeper = lambda: (lambda delay: delays.append(delay))
        self.app._run_in_thread = lambda fn: fn()

        def fake_jump(controls, watcher, **kwargs):
            called.append("jump")
            return None

        with patch("edap.control_room.routines_movement.jump", new=fake_jump):
            self.app._replay_history_entry(
                CommandHistoryEntry(raw="jump", command="jump", timestamp="1"),
                edit=False,
                skip_delay=True,
            )

        self.assertEqual(delays, [])
        self.assertEqual(called, ["jump"])
        self.assertEqual(self._last_history().raw, "jump")  # type: ignore[union-attr]

    def test_replay_edit_stays_immediate(self) -> None:
        delays: list[float] = []
        input_stub = _InputStub()
        focused: list[object] = []

        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=5.0,
            ),
        )
        self.app._make_sleeper = lambda: (lambda delay: delays.append(delay))
        self.app.query_one = lambda *args, **kwargs: input_stub  # type: ignore[method-assign]
        self.app.set_focus = lambda widget: focused.append(widget)  # type: ignore[method-assign]

        self.app._replay_history_entry(
            CommandHistoryEntry(raw="jump", command="jump", timestamp="1"),
            edit=True,
        )

        self.assertEqual(delays, [])
        self.assertEqual(input_stub.value, "jump")
        self.assertEqual(input_stub.cursor_position, 4)
        self.assertEqual(focused, [input_stub])
        self.assertTrue(self.app._prompt_state.command_input_prefill_active)
        self.assertEqual(self.app._prompt_state.command_input_value, "jump")

    def test_prompt_draft_survives_local_data_refresh_after_input_change(self) -> None:
        self.app._prompt_state.command_input_prefill_active = True
        self.app._prompt_state.command_input_placeholder = (
            "edit Inara search params then press Enter..."
        )
        self.app._prompt_state.command_input_value = "near_system='Sol'"
        self.app._prompt_state.haul_prompt_step = "search_edit"
        self.app._prompt_state.haul_prompt_mode = "search"
        self.app._command_input.placeholder = self.app._prompt_state.command_input_placeholder
        self.app._command_input.value = "near_system='Achenar'"
        self.app._command_input.cursor_position = 5

        changed_event = type(
            "_ChangedEvent",
            (),
            {"input": self.app._command_input, "value": self.app._command_input.value},
        )()
        self.app.on_input_changed(changed_event)

        self.assertEqual(self.app._prompt_state.command_input_value, "near_system='Achenar'")
        self.assertEqual(self.app._command_input.value, "near_system='Achenar'")
        self.assertEqual(self.app._command_input.cursor_position, 5)

    def test_non_executable_command_stays_immediate_even_with_delay_configured(self) -> None:
        delays: list[float] = []

        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=5.0,
            ),
        )
        self.app._make_sleeper = lambda: (lambda delay: delays.append(delay))

        self.app._dispatch_command("help dock")

        self.assertEqual(delays, [])
        self.assertIn("dock", "\n".join(self.app.logged))

    def test_cancellation_during_pending_delay_prevents_launch(self) -> None:
        called: list[str] = []

        self.app._controls = object()
        self.app._config = self.app._config.__class__(
            paths=self.app._config.paths,
            controls=self.app._config.controls,
            screen=self.app._config.screen,
            runtime=self.app._config.runtime,
            timing=self.app._config.timing,
            control_room=ControlRoomConfig(
                state_file=self.app._config.control_room.state_file,
                history_limit=self.app._config.control_room.history_limit,
                activity_log_max_lines=self.app._config.control_room.activity_log_max_lines,
                command_delay_seconds=5.0,
            ),
        )
        self.app._make_progress = lambda: (lambda _: None)
        self.app._make_controls = lambda progress: object()
        self.app._make_watcher = lambda: object()
        self.app._make_sleeper = lambda: (lambda delay: (_ for _ in ()).throw(RoutineCancelled()))

        def fake_run_in_thread(fn):
            try:
                return fn()
            except PendingRoutineCancelled as exc:
                self.app._log(f"[yellow]{exc}[/]")
                self.app._clear_routine()
                return None

        self.app._run_in_thread = fake_run_in_thread

        def fake_jump(controls, watcher, **kwargs):
            called.append("jump")
            return None

        with patch("edap.control_room.routines_movement.jump", new=fake_jump):
            self.app._dispatch_command("jump")

        self.assertEqual(called, [])
        self.assertFalse(self.app._routine_active)
        self.assertIn("Cancelled pending jump before execution.", "\n".join(self.app.logged))


class ControlRoomEventReducerTests(unittest.TestCase):
    def test_undocked_waits_for_no_track_before_clearing_station(self) -> None:
        ship = ShipState(system="HIP 58412", station="Pawelczyk Dock", status="in_station")

        apply_ship_event(ship, {"event": "Undocked", "StationName": "Pawelczyk Dock"})

        self.assertEqual(ship.status, "in_undocking")
        self.assertEqual(ship.station, "Pawelczyk Dock")

        apply_ship_event(ship, {"event": "Music", "MusicTrack": "DockingComputer"})

        self.assertEqual(ship.status, "in_undocking")
        self.assertEqual(ship.station, "Pawelczyk Dock")

        apply_ship_event(ship, {"event": "Music", "MusicTrack": "NoTrack"})

        self.assertEqual(ship.status, "in_space")
        self.assertIsNone(ship.station)

    def test_carrier_exploration_marks_manual_launch_resume(self) -> None:
        ship = ShipState(system="HIP 17597", station="Stronghold Carrier", status="in_station")

        apply_ship_event(
            ship,
            {"event": "Undocked", "StationName": "Stronghold Carrier", "StationType": "SurfaceStation"},
        )

        self.assertEqual(ship.status, "in_undocking")
        self.assertEqual(ship.station, "Stronghold Carrier")

        apply_ship_event(ship, {"event": "Music", "MusicTrack": "DockingComputer"})
        apply_ship_event(ship, {"event": "Music", "MusicTrack": "Exploration"})

        self.assertEqual(ship.status, "in_space")
        self.assertIsNone(ship.station)


class ControlRoomFailureMessageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.app = _HarnessApp(_make_context(Path(self.tmpdir.name)))

    def test_station_mismatch_includes_edit_guidance(self) -> None:
        result = RoutineResult(
            action="MarketBuy",
            dispatch=ActionDispatchResult(
                action="MarketBuy",
                status="error",
                reason=(
                    "Station check failed after 3 attempts: "
                    "Market.json is from 'Hsulong Orbital' but last Docked event is 'Jameson Memorial'"
                ),
            ),
        )

        message, suggestion = describe_routine_failure(result, self.app._config)

        self.assertIn("Station mismatch", message)
        self.assertIn("Hsulong Orbital", message)
        self.assertIn("Jameson Memorial", message)
        self.assertIn("market data indicates", message)
        self.assertIn("we are docked at", message)
        self.assertIsNotNone(suggestion)
        self.assertIn("Ctrl-R", suggestion or "")
        self.assertIn("press e to edit", suggestion or "")

    def test_route_mismatch_includes_replay_guidance(self) -> None:
        result = RoutineResult(
            action="GalaxyMapOpen",
            dispatch=ActionDispatchResult(
                action="GalaxyMapOpen",
                status="error",
                reason="route mismatch: expected 'Sol', got 'Achenar'",
            ),
        )

        message, suggestion = describe_routine_failure(result, self.app._config)

        self.assertIn("Destination mismatch", message)
        self.assertIn("Sol", message)
        self.assertIn("Achenar", message)
        self.assertIsNotNone(suggestion)
        self.assertIn("Ctrl-R", suggestion or "")

    def test_market_target_mismatch_uses_operator_language(self) -> None:
        result = RoutineResult(
            action="MarketSell",
            dispatch=ActionDispatchResult(
                action="MarketSell",
                status="error",
                reason="'Gold Ore' not found in market list (first items: ['Bertrandite'])",
            ),
        )

        message, suggestion = describe_routine_failure(result, self.app._config)

        self.assertEqual(
            message,
            "Commodity mismatch: Gold Ore was not found in this station's market list.",
        )
        self.assertIsNotNone(suggestion)
        self.assertIn("commodity name", suggestion or "")

    def test_worker_logs_failed_reason_and_try_line(self) -> None:
        app = _HarnessApp(_make_context(Path(tempfile.mkdtemp())))

        class _Worker:
            is_cancelled = False

        result = RoutineResult(
            action="MarketBuy",
            dispatch=ActionDispatchResult(
                action="MarketBuy",
                status="error",
                reason=(
                    "Station check failed after 3 attempts: "
                    "Market.json is from 'Hsulong Orbital' but last Docked event is 'Jameson Memorial'"
                ),
            ),
        )

        with patch("edap.control_room.workers.get_current_worker", return_value=_Worker()):
            run_routine_thread(app, lambda: result)

        joined = "\n".join(app.logged)
        self.assertIn("Failed: MarketBuy -- Station mismatch", joined)
        self.assertIn("Try: Open replay history with Ctrl-R, press e to edit", joined)

    def test_controls_unavailable_uses_configured_message(self) -> None:
        self.app._controls = None

        ready = self.app._check_routine_ready()

        self.assertFalse(ready)
        self.assertIn(
            error_text.render(self.app._config, "controls_unavailable"),
            "\n".join(self.app.logged),
        )


class ControlRoomPromptStateTests(unittest.TestCase):
    def test_advance_haul_prompt_progresses_from_station_1_buying_to_station_1(self) -> None:
        prompt_state = PromptState(
            haul_params={"station_1_buying": ""},
            haul_prompt_defaults={"station_1": "Jameson Memorial"},
            haul_prompt_step="station_1_buying",
        )

        transition = control_room_prompts.advance_haul_prompt(
            prompt_state,
            "Gold",
            current_station="Jameson Memorial",
            current_system="Sol",
            configured_galaxy_map_settle_default=2.0,
            configured_dock_timeout_default=1200.0,
            default_placeholder="cmd...",
            render_error=lambda key, **kwargs: key,
            parse_optional_nonnegative_float=lambda raw, default, label: default,
        )

        self.assertEqual(prompt_state.haul_prompt_step, "station_1")
        self.assertEqual(prompt_state.haul_params["station_1_buying"], "Gold")
        self.assertEqual(
            transition.log_lines,
            (
                "  Station 1 buying: [cyan]Gold[/]",
                "[dim]Station 1 name? (Enter = Jameson Memorial)[/]",
            ),
        )
        assert transition.ui_state is not None
        self.assertEqual(transition.ui_state.placeholder, "station 1 (Enter = Jameson Memorial)...")
        self.assertEqual(transition.ui_state.value, "Jameson Memorial")

    def test_advance_haul_prompt_rejects_missing_station_2_name(self) -> None:
        prompt_state = PromptState(
            haul_params={},
            haul_prompt_defaults={},
            haul_prompt_step="station_2",
        )

        transition = control_room_prompts.advance_haul_prompt(
            prompt_state,
            "",
            current_station="Jameson Memorial",
            current_system="Sol",
            configured_galaxy_map_settle_default=2.0,
            configured_dock_timeout_default=1200.0,
            default_placeholder="cmd...",
            render_error=lambda key, **kwargs: key,
            parse_optional_nonnegative_float=lambda raw, default, label: default,
        )

        self.assertEqual(prompt_state.haul_prompt_step, "station_2")
        self.assertEqual(
            transition.log_lines,
            ("[red]station_2_name_required[/]",),
        )
        self.assertIsNone(transition.ui_state)

    def test_advance_haul_prompt_finishes_and_requests_dispatch(self) -> None:
        prompt_state = PromptState(
            haul_params={"dock_timeout": ""},
            haul_prompt_defaults={"dock_timeout": "1200.0"},
            haul_prompt_step="dock_timeout",
            haul_prompt_raw_command="haul gold",
            haul_prompt_skip_delay=True,
        )

        transition = control_room_prompts.advance_haul_prompt(
            prompt_state,
            "",
            current_station="Jameson Memorial",
            current_system="Sol",
            configured_galaxy_map_settle_default=2.0,
            configured_dock_timeout_default=1200.0,
            default_placeholder="cmd...",
            render_error=lambda key, **kwargs: key,
            parse_optional_nonnegative_float=lambda raw, default, label: default,
        )

        self.assertEqual(prompt_state.haul_prompt_step, "")
        self.assertEqual(prompt_state.haul_prompt_defaults, {})
        self.assertEqual(prompt_state.haul_params["dock_timeout"], "1200.0")
        self.assertTrue(transition.launch_haul_loop)
        self.assertTrue(transition.skip_delay)
        self.assertEqual(transition.raw_command, "haul gold")
        assert transition.ui_state is not None
        self.assertEqual(transition.ui_state.placeholder, "cmd...")

    def test_begin_haul_prompt_uses_explicit_prompt_state(self) -> None:
        prompt_state = PromptState()

        ui_state = control_room_prompts.begin_haul_prompt(
            prompt_state,
            commodity="Gold",
            prompt_for_commodity=True,
            haul_prompt_defaults={"station_1_buying": "Aluminium"},
            current_station="Jameson Memorial",
            raw_command="haul gold",
            skip_delay=False,
        )

        self.assertEqual(prompt_state.haul_prompt_step, "station_1_buying")
        self.assertEqual(prompt_state.haul_params["station_1_buying"], "Gold")
        self.assertEqual(prompt_state.haul_prompt_raw_command, "haul gold")
        self.assertEqual(ui_state.placeholder, "station 1 buying (Enter = Aluminium)...")
        self.assertEqual(ui_state.value, "Aluminium")

    def test_resolve_haul_confirm_prompt_updates_prompt_state(self) -> None:
        prompt_state = PromptState(
            haul_params={},
            haul_confirm_buy_station="Jameson Memorial",
            haul_prompt_raw_command="haul gold",
            haul_prompt_skip_delay=True,
        )

        resolution = control_room_prompts.resolve_haul_confirm_prompt(prompt_state, "")

        self.assertIsNotNone(resolution)
        assert resolution is not None
        self.assertTrue(resolution.launch_haul_loop)
        self.assertEqual(resolution.station_1, "Jameson Memorial")
        self.assertEqual(prompt_state.haul_params["station_1"], "Jameson Memorial")
        self.assertEqual(prompt_state.haul_confirm_buy_station, "")

    def test_clear_haul_prompt_resets_prompt_state(self) -> None:
        prompt_state = PromptState(
            haul_params={"station_1_buying": "Gold"},
            haul_prompt_defaults={"station_1": "Jameson Memorial"},
            haul_prompt_step="station_1",
            haul_prompt_raw_command="haul gold",
            haul_prompt_skip_delay=True,
        )

        control_room_prompts.clear_haul_prompt(prompt_state)

        self.assertEqual(prompt_state.haul_params, {})
        self.assertEqual(prompt_state.haul_prompt_defaults, {})
        self.assertEqual(prompt_state.haul_prompt_step, "")
        self.assertEqual(prompt_state.haul_prompt_raw_command, "")
        self.assertFalse(prompt_state.haul_prompt_skip_delay)

    def test_begin_and_resolve_destination_prompt_use_explicit_prompt_state(self) -> None:
        prompt_state = PromptState()

        default_settle = control_room_prompts.begin_destination_prompt(
            prompt_state,
            configured_settle_default=2.0,
            destination="Achenar",
            skip_delay=True,
        )

        self.assertEqual(default_settle, 2.0)
        self.assertEqual(prompt_state.dest_prompt_destination, "Achenar")
        self.assertEqual(prompt_state.dest_prompt_raw_command, "!dest Achenar")
        self.assertTrue(prompt_state.dest_prompt_skip_delay)

        dispatch = control_room_prompts.resolve_destination_prompt_submission(
            prompt_state,
            "",
            parse_optional_nonnegative_float=lambda raw, default, label: default,
        )

        self.assertIsNotNone(dispatch)
        assert dispatch is not None
        self.assertEqual(dispatch.destination, "Achenar")
        self.assertEqual(dispatch.galaxy_map_settle, 2.0)
        self.assertTrue(dispatch.skip_delay)
        self.assertEqual(dispatch.raw_command, "!dest Achenar")
        self.assertEqual(prompt_state.dest_prompt_destination, "")
        self.assertIsNone(prompt_state.dest_prompt_settle_default)
        self.assertEqual(prompt_state.dest_prompt_raw_command, "")
        self.assertFalse(prompt_state.dest_prompt_skip_delay)

    def test_invalid_destination_prompt_submission_preserves_prompt_state(self) -> None:
        prompt_state = PromptState(
            dest_prompt_destination="Sol",
            dest_prompt_settle_default=2.0,
            dest_prompt_raw_command="dest Sol",
        )

        dispatch = control_room_prompts.resolve_destination_prompt_submission(
            prompt_state,
            "bad-number",
            parse_optional_nonnegative_float=lambda raw, default, label: None,
        )

        self.assertIsNone(dispatch)
        self.assertEqual(prompt_state.dest_prompt_destination, "Sol")
        self.assertEqual(prompt_state.dest_prompt_settle_default, 2.0)
        self.assertEqual(prompt_state.dest_prompt_raw_command, "dest Sol")


if __name__ == "__main__":
    unittest.main()
