"""
ED AutoPilot Control Room

Live TUI: ship status, activity log, market tracker, and routine dispatch.

Usage:
    uv run python3 control_room.py
    uv run python3 control_room.py --market aluminium

Routine commands (type in the input bar):
    dock               dock + auto-refuel/repair; skips supercruise-exit wait if already in normal space
    undock             launch from station
    boost              fire boost three times immediately
    escape             set speed full, then boost until Status.json says mass lock cleared
    buy <item> [N]     buy N units (default MAX) of commodity
    sell [item] [N]    sell commodity (default: market filter); amount default MAX
    jump               FSD jump sequence
    haul [commodity]   start haul loop; or use `haul load [path]` / `haul search [system]` / `haul search url <inara-url>` / `haul route <n>`
    multi_leg_haul <route.json|spansh-url>   run a standalone multi-leg haul route
    dest <system>      open galaxy map and plot a route to the named system
    set_dest <system>  alias for dest
    home               route to the configured home system
    home set <system>  save the home system into config and use it later with `home`

Market commands:
    market filter <name>   filter market panel by commodity name (e.g. market filter aluminium)
    market [clear]         clear the filter (default when no args)
    market lock            pin panel to current market
    market unlock          follow latest market

Other:
    commands           list supported commands
    help [command]     explain a command in plain English
    replay             open the replay history browser
    new_session        clear persisted haul session time/profit and start a fresh session now
    stop               freeze persisted haul session time/profit until hauling resumes or you start a new session
    q / quit           cancel active work if needed, then exit
"""
from __future__ import annotations

import argparse
import json
import signal
import socket
import sys
import time
from pathlib import Path
from typing import IO, Any, Callable, Protocol

from rich.markup import escape
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.app import ScreenStackError
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import MouseScrollDown, MouseScrollUp
from textual.widgets import Footer, Header, Input, OptionList, RichLog, Static, Tab, Tabs

from edap.config import AppConfig
from edap.control_room.backend import ControlRoomBackend, LocalControlRoomBackend
from edap.control_room.dependencies import (
    ControlRoomDependencies,
    build_local_control_room_dependencies,
)
from edap.control_room import (
    bootstrap as _bootstrap,
    commands as _commands,
    error_text,
    events as _events,
    facade as _facade,
    haul_tracking as _haul_tracking,
    help as _help,
    history as _history,
    persistence as _persistence,
    prompts as _prompts,
    replay as _replay,
    rendering as _rendering,
    tts as _tts_module,
    routines_haul,
    routines_movement,
    routines_nav,
    routines_station,
    routines_trade,
    workers as _workers,
)
from edap.control_room.models import (
    HaulStats,
    HistoryState,
    MarketData,
    PromptState,
    ReplayBrowserState,
    ReplaySelection,
    RuntimeUIState,
    ShipState,
    TradeRoutePickerState,
    TradeRoutesData,
)
from edap.control_room import view_models as _view_models
from edap.control_room.app_view_actions import build_control_room_app_view_actions
from edap.control_room.view_actions import ControlRoomViewActions
from edap.control_room.protocol.adapters import (
    build_activity_log_entry,
    build_announcement_event,
)
from edap.control_room.protocol.events import (
    ActivityLogAppendedEvent,
    ActivityLogEntry,
    AnnouncementEvent,
    DataUpdatedEvent,
)
from edap.control_room.protocol.sink import ControlRoomEventSink
from edap.inara.trade_routes import TradeRoute

# Modules eligible for in-place hot reload via the `reload` command.
# Order matters: leaf modules first, then modules that import from them.
_RELOADABLE_MODULES = [
    routines_haul,
    routines_trade,
    routines_nav,
    routines_movement,
    routines_station,
    _bootstrap,
    _events,
    _facade,
    _haul_tracking,
    _history,
    _help,
    _commands,
    _persistence,
    _prompts,
    _replay,
    _rendering,
    _tts_module,
    _workers,
]
from edap.control_room_state import (
    CommandHistoryEntry,
    ControlRoomState,
)
from edap.binding_names import format_binding_action_hint
from edap.runtime import RuntimeContext, build_runtime_context, load_config_with_fallback
from edap.ship_controls import DEFAULT_SHIP_CONTROL_ACTIONS, ShipControls
from edap.tts import AnnouncementId, TTSAnnouncer, format_credits_short, parse_announcement_id
from edap import version as _version


# ── All actions needed across every supported routine ──────────────────────────

_ALL_ROUTINE_ACTIONS = list(DEFAULT_SHIP_CONTROL_ACTIONS)
_STARTUP_BINDING_WARNING_IGNORED_ACTIONS = frozenset({
    "RollLeftButton",
    "RollRightButton",
    "PitchUpButton",
    "PitchDownButton",
    "YawLeftButton",
    "YawRightButton",
})

_DEFAULT_COMMAND_PLACEHOLDER = "commands | help dock | replay | dock | undock | boost | escape | jump | buy <item> [N] | sell [item] | haul [commodity] | haul load | haul search [system] | haul search url <url> | haul route <n> | multi_leg_haul <route> | dest <system> | home | set_pid | set_hwnd | market ... | instant | new_session | stop | reload | q"
_ACTIVITY_AUTO_FOLLOW_DEBOUNCE_SECONDS = 10.0
_JOURNAL_ARTIFACT_LOG_PATH = Path("artifacts/control-room.log")
_DEBUG_ARTIFACT_LOG_PATH = Path("artifacts/control-room-debug.log")
_JOURNAL_ARTIFACT_LOG_BUFFER_SIZE = 8192
_JOURNAL_ARTIFACT_LOG_FLUSH_EVERY = 20
_PROTOCOL_ANNOUNCEMENT_CACHE_LIMIT = 200

_RoutineCancelled = _workers.RoutineCancelled
_CancellationProxy = _workers.CancellationProxy


# ── Helpers ────────────────────────────────────────────────────────────────────


def _fmt_cr(n: int) -> str:
    return _rendering.fmt_cr(n)


def _fuel_bar(level: float, capacity: float) -> str:
    return _rendering.fuel_bar(level, capacity)


def _loc(item: dict[str, Any], key: str) -> str:
    return _rendering.loc(item, key)


def _hhmmss() -> str:
    return _rendering.hhmmss()


def _is_recent(ev: dict[str, Any], threshold_s: float = 120.0) -> bool:
    return _rendering.is_recent(ev, threshold_s=threshold_s)


def _fmt_duration(seconds: float | None) -> str:
    return _rendering.fmt_duration(seconds)


def _build_log_text(msg: str, *, timestamp: str) -> Text:
    return _rendering.build_log_text(msg, timestamp=timestamp)


def _read_cargo_inventory(journal_dir: Path) -> list[dict[str, Any]]:
    return _rendering.read_cargo_inventory(journal_dir)


def _cargo_summary_lines(inventory: list[dict[str, Any]], *, limit: int = 3) -> list[str]:
    return _rendering.cargo_summary_lines(inventory, limit=limit)


class VersionSource(Protocol):
    def get_current_version(self) -> str: ...

    def fetch_latest_github_release(self) -> _version.GitHubRelease | None: ...


class DefaultVersionSource:
    def get_current_version(self) -> str:
        return _version.get_current_version()

    def fetch_latest_github_release(self) -> _version.GitHubRelease | None:
        return _version.fetch_latest_github_release()


class ActivityLog(RichLog):
    def __init__(
        self,
        *,
        max_lines: int | None = None,
        pause_seconds: float = _ACTIVITY_AUTO_FOLLOW_DEBOUNCE_SECONDS,
        time_fn: Callable[[], float] | None = None,
        on_pause_changed: Callable[[bool], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(max_lines=max_lines, **kwargs)
        self._pause_seconds = pause_seconds
        self._time_fn = time_fn or time.monotonic
        self._on_pause_changed = on_pause_changed
        self._resume_timer: Any | None = None

    @property
    def auto_follow_paused(self) -> bool:
        return not self.auto_scroll

    def configure_auto_follow(
        self,
        *,
        time_fn: Callable[[], float] | None = None,
        on_pause_changed: Callable[[bool], None] | None = None,
    ) -> None:
        if time_fn is not None:
            self._time_fn = time_fn
        if on_pause_changed is not None:
            self._on_pause_changed = on_pause_changed

    def _set_auto_follow_paused(self, paused: bool) -> None:
        if paused == self.auto_follow_paused:
            if paused:
                self._schedule_resume_timer()
            return
        self.auto_scroll = not paused
        if paused:
            self._schedule_resume_timer()
        else:
            self._cancel_resume_timer()
        if self._on_pause_changed is not None:
            self._on_pause_changed(paused)

    def _schedule_resume_timer(self) -> None:
        self._cancel_resume_timer()
        self._resume_timer = self.set_timer(
            self._pause_seconds,
            self.resume_auto_follow,
        )

    def _cancel_resume_timer(self) -> None:
        if self._resume_timer is None:
            return
        self._resume_timer.stop()
        self._resume_timer = None

    def resume_auto_follow(self) -> None:
        self._set_auto_follow_paused(False)

    def sync_auto_follow_to_scroll_position(self) -> None:
        if self.scroll_y >= self.max_scroll_y:
            self.resume_auto_follow()
            return
        self._set_auto_follow_paused(True)

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        super()._on_mouse_scroll_up(event)
        self.sync_auto_follow_to_scroll_position()

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        super()._on_mouse_scroll_down(event)
        self.sync_auto_follow_to_scroll_position()

    def action_scroll_up(self) -> None:
        super().action_scroll_up()
        self.sync_auto_follow_to_scroll_position()

    def action_scroll_down(self) -> None:
        super().action_scroll_down()
        self.sync_auto_follow_to_scroll_position()

    def action_page_up(self) -> None:
        super().action_page_up()
        self.sync_auto_follow_to_scroll_position()

    def action_page_down(self) -> None:
        super().action_page_down()
        self.sync_auto_follow_to_scroll_position()

    def action_scroll_home(self) -> None:
        super().action_scroll_home()
        self.sync_auto_follow_to_scroll_position()

    def action_scroll_end(self) -> None:
        super().action_scroll_end()
        self.sync_auto_follow_to_scroll_position()


# ── App ────────────────────────────────────────────────────────────────────────


class ControlRoomApp(App[None]):
    BINDINGS = [
        ("ctrl+c", "request_interrupt", "Interrupt"),
        ("ctrl+d", "request_exit", "Exit"),
        ("ctrl+r", "open_history", "History"),
    ]

    CSS = """
    Screen  { layout: vertical; }
    #main   { height: 1fr; }
    #left   { width: 58%; }
    #right  { width: 42%; }
    #status {
        height: auto;
        max-height: 14;
        border: solid $primary;
        padding: 0 1;
    }
    #activity-pane {
        height: 1fr;
    }
    #activity {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }
    #haul {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }
    #market-pane {
        height: 1fr;
        border: solid $primary;
    }
    #market-tabs {
        dock: top;
    }
    #market {
        height: 1fr;
        padding: 0 1;
    }
    #market-content {
        height: auto;
    }
    #trade-route-picker {
        display: none;
        height: 1fr;
        border: heavy $primary;
        padding: 1;
    }
    #trade-route-help {
        height: auto;
        padding: 0 0 1 0;
    }
    #trade-route-list {
        height: 1fr;
        border: solid $accent;
    }
    #trade-route-detail {
        height: 8;
        border: solid $primary;
        padding: 0 1;
        margin: 1 0 0 0;
    }
    #cmd { height: 3; }
    #resume-browser {
        display: none;
        height: 1fr;
        border: heavy $primary;
        padding: 1;
    }
    #resume-help {
        height: auto;
        padding: 0 0 1 0;
    }
    #resume-list {
        height: 1fr;
        border: solid $accent;
    }
    #resume-detail {
        height: 6;
        border: solid $primary;
        padding: 0 1;
        margin: 1 0 0 0;
    }
    """

    def __init__(
        self,
        ctx: RuntimeContext,
        market_filter: str | None = None,
        *,
        activity_log_max_lines: int | None = None,
        version_source: VersionSource | None = None,
        backend: ControlRoomBackend | None = None,
        dependencies: ControlRoomDependencies | None = None,
        view_actions: ControlRoomViewActions | None = None,
        title_override: str | None = None,
    ) -> None:
        super().__init__()
        self._ctx = ctx
        self._config: AppConfig = ctx.config
        self._config_path: Path = ctx.config_path
        self._config_loaded_from_example_fallback = ctx.used_example_config_fallback
        self._default_command_placeholder = _DEFAULT_COMMAND_PLACEHOLDER
        self._journal_dir: Path | None = ctx.journal.effective_path
        self._market_path: Path | None = (
            self._journal_dir / "Market.json" if self._journal_dir is not None else None
        )
        self._ship = ShipState()
        self._market = MarketData()
        self._presented_market = MarketData()
        self._haul_stats = HaulStats()
        self._trade_routes = TradeRoutesData()
        self._market_filter = market_filter
        self._market_mtime: float | None = None
        self._controls: ShipControls | None = None
        self._runtime_state = RuntimeUIState()
        self._prompt_state = PromptState()
        self._history_state = HistoryState()
        self._state_path: Path = self._config.control_room.state_file
        self._activity_log_max_lines = (
            self._config.control_room.activity_log_max_lines
            if activity_log_max_lines is None
            else activity_log_max_lines
        )
        self._journal_artifact_log_path = _JOURNAL_ARTIFACT_LOG_PATH
        self._journal_artifact_log_handle: IO[str] | None = None
        self._journal_artifact_log_pending_writes = 0
        self._debug_artifact_log_path = _DEBUG_ARTIFACT_LOG_PATH
        self._protocol_activity_log: list[ActivityLogEntry] = []
        self._local_activity_log: list[ActivityLogEntry] = []
        self._activity_display_order: dict[tuple[str, str, str], int] = {}
        self._next_activity_display_order = 0
        self._protocol_announcements: list[AnnouncementEvent] = []
        self._protocol_external_event_sink: ControlRoomEventSink | None = None
        self._saved_state = ControlRoomState()
        self._replay_state = ReplayBrowserState()
        self._trade_route_picker_state = TradeRoutePickerState()
        self._watcher_worker: Any | None = None
        self._routine_worker: Any | None = None
        self._time_fn: Callable[[], float] = time.monotonic
        self._tts = TTSAnnouncer(self._config.tts, platform_name=self._config.runtime.platform)
        self._version_source = version_source or DefaultVersionSource()
        self._current_version = self._version_source.get_current_version()
        self._facade = _facade.ControlRoomFacade(
            self,
            default_placeholder=_DEFAULT_COMMAND_PLACEHOLDER,
            reloadable_modules=_RELOADABLE_MODULES,
        )
        self._dependencies = dependencies or build_local_control_room_dependencies(self)
        self._view_actions = view_actions or build_control_room_app_view_actions(self)
        self._backend: ControlRoomBackend = backend or LocalControlRoomBackend(self)
        self._backend_event_unsubscribe: Callable[[], None] | None = None
        self._title_override = title_override
        self._exit_requested_once = False
        self._exit_prompt_active = False
        self._suppress_replay_enter_until = 0.0

    def __getattr__(self, name: str) -> Any:
        target = _facade.FACADE_METHOD_MAP.get(name)
        if target is None:
            raise AttributeError(name)
        return getattr(self._facade, target)

    @property
    def backend(self) -> ControlRoomBackend:
        return self._backend

    @property
    def dependencies(self) -> ControlRoomDependencies:
        return self._dependencies

    @property
    def view_actions(self) -> ControlRoomViewActions:
        return self._view_actions

    @property
    def _protocol_event_sink(self) -> ControlRoomEventSink | None:
        return self._protocol_external_event_sink

    @_protocol_event_sink.setter
    def _protocol_event_sink(self, sink: ControlRoomEventSink | None) -> None:
        self._protocol_external_event_sink = sink

    @property
    def _haul_params(self) -> dict[str, str]:
        return self._prompt_state.haul_params

    @_haul_params.setter
    def _haul_params(self, value: dict[str, str]) -> None:
        self._prompt_state.haul_params = value

    @property
    def _haul_prompt_defaults(self) -> dict[str, str]:
        return self._prompt_state.haul_prompt_defaults

    @_haul_prompt_defaults.setter
    def _haul_prompt_defaults(self, value: dict[str, str]) -> None:
        self._prompt_state.haul_prompt_defaults = value

    @property
    def _haul_prompt_step(self) -> str:
        return self._prompt_state.haul_prompt_step

    @_haul_prompt_step.setter
    def _haul_prompt_step(self, value: str) -> None:
        self._prompt_state.haul_prompt_step = value

    @property
    def _haul_confirm_buy_station(self) -> str:
        return self._prompt_state.haul_confirm_buy_station

    @_haul_confirm_buy_station.setter
    def _haul_confirm_buy_station(self, value: str) -> None:
        self._prompt_state.haul_confirm_buy_station = value

    @property
    def _haul_prompt_raw_command(self) -> str:
        return self._prompt_state.haul_prompt_raw_command

    @_haul_prompt_raw_command.setter
    def _haul_prompt_raw_command(self, value: str) -> None:
        self._prompt_state.haul_prompt_raw_command = value

    @property
    def _haul_prompt_skip_delay(self) -> bool:
        return self._prompt_state.haul_prompt_skip_delay

    @_haul_prompt_skip_delay.setter
    def _haul_prompt_skip_delay(self, value: bool) -> None:
        self._prompt_state.haul_prompt_skip_delay = value

    @property
    def _dest_prompt_destination(self) -> str:
        return self._prompt_state.dest_prompt_destination

    @_dest_prompt_destination.setter
    def _dest_prompt_destination(self, value: str) -> None:
        self._prompt_state.dest_prompt_destination = value

    @property
    def _dest_prompt_settle_default(self) -> float | None:
        return self._prompt_state.dest_prompt_settle_default

    @_dest_prompt_settle_default.setter
    def _dest_prompt_settle_default(self, value: float | None) -> None:
        self._prompt_state.dest_prompt_settle_default = value

    @property
    def _dest_prompt_raw_command(self) -> str:
        return self._prompt_state.dest_prompt_raw_command

    @_dest_prompt_raw_command.setter
    def _dest_prompt_raw_command(self, value: str) -> None:
        self._prompt_state.dest_prompt_raw_command = value

    @property
    def _dest_prompt_skip_delay(self) -> bool:
        return self._prompt_state.dest_prompt_skip_delay

    @_dest_prompt_skip_delay.setter
    def _dest_prompt_skip_delay(self, value: bool) -> None:
        self._prompt_state.dest_prompt_skip_delay = value

    @property
    def _history(self) -> list[str]:
        return self._history_state.entries

    @_history.setter
    def _history(self, value: list[str]) -> None:
        self._history_state.entries = value

    @property
    def _history_pos(self) -> int:
        return self._history_state.pos

    @_history_pos.setter
    def _history_pos(self, value: int) -> None:
        self._history_state.pos = value

    @property
    def _history_draft(self) -> str:
        return self._history_state.draft

    @_history_draft.setter
    def _history_draft(self, value: str) -> None:
        self._history_state.draft = value

    @property
    def _resume_entries(self) -> list[ReplaySelection]:
        return self._replay_state.entries

    @_resume_entries.setter
    def _resume_entries(self, value: list[ReplaySelection]) -> None:
        self._replay_state.entries = value

    @property
    def _resume_open(self) -> bool:
        return self._replay_state.open

    @_resume_open.setter
    def _resume_open(self, value: bool) -> None:
        self._replay_state.open = value

    @property
    def _resume_filter(self) -> str:
        return self._replay_state.filter_text

    @_resume_filter.setter
    def _resume_filter(self, value: str) -> None:
        self._replay_state.filter_text = value

    @property
    def _selected_resume_history_entry(self) -> CommandHistoryEntry | None:
        return self._replay_state.selected_history_entry

    @_selected_resume_history_entry.setter
    def _selected_resume_history_entry(self, value: CommandHistoryEntry | None) -> None:
        self._replay_state.selected_history_entry = value

    @property
    def _trade_route_picker_open(self) -> bool:
        return self._trade_route_picker_state.open

    @_trade_route_picker_open.setter
    def _trade_route_picker_open(self, value: bool) -> None:
        self._trade_route_picker_state.open = value

    @property
    def _selected_trade_route_index(self) -> int | None:
        return self._trade_route_picker_state.selected_route_index

    @_selected_trade_route_index.setter
    def _selected_trade_route_index(self, value: int | None) -> None:
        self._trade_route_picker_state.selected_route_index = value

    @property
    def _presented_trade_route_query_url(self) -> str:
        return self._trade_route_picker_state.presented_query_url

    @_presented_trade_route_query_url.setter
    def _presented_trade_route_query_url(self, value: str) -> None:
        self._trade_route_picker_state.presented_query_url = value

    @property
    def _presented_trade_route_searched_at(self) -> str:
        return self._trade_route_picker_state.presented_searched_at

    @_presented_trade_route_searched_at.setter
    def _presented_trade_route_searched_at(self, value: str) -> None:
        self._trade_route_picker_state.presented_searched_at = value

    @property
    def _routine_active(self) -> bool:
        return self._runtime_state.routine_active

    @_routine_active.setter
    def _routine_active(self, value: bool) -> None:
        self._runtime_state.routine_active = value

    @property
    def _active_routine_name(self) -> str | None:
        return self._runtime_state.active_routine_name

    @_active_routine_name.setter
    def _active_routine_name(self, value: str | None) -> None:
        self._runtime_state.active_routine_name = value

    @property
    def _haul_stop_requested(self) -> bool:
        return self._runtime_state.haul_stop_requested

    @_haul_stop_requested.setter
    def _haul_stop_requested(self, value: bool) -> None:
        self._runtime_state.haul_stop_requested = value

    def _set_haul_phase(self, phase: str | None, station_index: int | None) -> None:
        self._runtime_state.haul_phase = phase
        self._runtime_state.haul_phase_station_index = station_index
        self._publish_protocol_data_refresh()

    @property
    def _verbose_controls(self) -> bool:
        return self._runtime_state.verbose_controls

    @_verbose_controls.setter
    def _verbose_controls(self, value: bool) -> None:
        self._runtime_state.verbose_controls = value

    @property
    def _instant_mode(self) -> bool:
        return self._runtime_state.instant_mode

    @_instant_mode.setter
    def _instant_mode(self, value: bool) -> None:
        self._runtime_state.instant_mode = value

    @property
    def _sigint_pending(self) -> bool:
        return self._runtime_state.sigint_pending

    @_sigint_pending.setter
    def _sigint_pending(self, value: bool) -> None:
        self._runtime_state.sigint_pending = value

    @property
    def _shutdown_requested(self) -> bool:
        return self._runtime_state.shutdown_requested

    @_shutdown_requested.setter
    def _shutdown_requested(self, value: bool) -> None:
        self._runtime_state.shutdown_requested = value

    @property
    def _shutdown_finalized(self) -> bool:
        return self._runtime_state.shutdown_finalized

    @_shutdown_finalized.setter
    def _shutdown_finalized(self, value: bool) -> None:
        self._runtime_state.shutdown_finalized = value

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Static(id="status")
                with Vertical(id="activity-pane"):
                    yield ActivityLog(
                        id="activity",
                        markup=True,
                        highlight=True,
                        wrap=True,
                        max_lines=self._activity_log_max_lines,
                    )
                    with Vertical(id="resume-browser"):
                        yield Static(
                            "Replay history  |  Enter execute  |  ! execute now  |  e edit  |  * set default haul  |  Esc/q close",
                            id="resume-help",
                        )
                        yield OptionList(id="resume-list")
                        yield Static(id="resume-detail")
            with Vertical(id="right"):
                with Vertical(id="market-pane"):
                    yield Tabs(
                        Tab("Buy", id="market-tab-buy"),
                        Tab("Sell", id="market-tab-sell"),
                        id="market-tabs",
                        active="market-tab-buy",
                    )
                    with VerticalScroll(id="market"):
                        yield Static(id="market-content")
                yield Static(id="haul")
        with Vertical(id="trade-route-picker"):
            yield Static(
                "Haul routes  |  Up/Down move  |  Enter load route  |  d set destination  |  Esc/q close",
                id="trade-route-help",
            )
            yield OptionList(id="trade-route-list")
            yield Static(id="trade-route-detail")
        yield Input(placeholder=_DEFAULT_COMMAND_PLACEHOLDER, id="cmd")
        yield Footer()

    def on_mount(self) -> None:
        self._configure_screen_widgets()
        if self._backend.exit_detaches_remote_session():
            self._mount_remote_runtime()
            return
        self._mount_local_runtime()

    def _configure_screen_widgets(self) -> None:
        self.title = self._title_override or "ED Control Room"
        self.query_one("#status", Static).border_title = "SHIP STATUS"
        self.query_one("#activity", ActivityLog).configure_auto_follow(
            time_fn=lambda: self._time_fn(),
            on_pause_changed=lambda paused: self._refresh_activity_title(),
        )
        self._refresh_activity_title()
        self.query_one("#resume-browser", Vertical).border_title = "REPLAY HISTORY"
        self.query_one("#haul", Static).border_title = "HAUL"
        self.query_one("#market-pane", Vertical).border_title = "MARKET"
        self.query_one("#market-tabs", Tabs).active = self._market_tab_id(
            self._runtime_state.market_panel_tab
        )
        self.query_one("#trade-route-picker", Vertical).border_title = "HAUL ROUTES"

    def _mount_local_runtime(self) -> None:
        if self._journal_dir is None or self._market_path is None:
            raise RuntimeError("Local control-room runtime requires a resolved journal directory.")
        self._build_controls()
        self._log_bindings_status()
        self._load_saved_state()
        self._log_startup_modes()
        self._bootstrap_ship_state()
        self._announce_startup_greeting()
        self._start_update_check()
        self._load_market_json()
        self._refresh_status()
        self._refresh_haul_stats()
        self._refresh_market()
        self._refresh_trade_routes()
        self._watcher_worker = self._start_watcher()
        self.set_interval(0.1, self._drain_pending_sigint)
        self.set_focus(self.query_one("#cmd", Input))
        self._update_resume_detail()

    def _mount_remote_runtime(self) -> None:
        self._backend_event_unsubscribe = self._backend.subscribe_events(
            self._handle_backend_event
        )
        start = getattr(self._backend, "start", None)
        if callable(start):
            start()
        self._apply_data_state(
            self._dependencies.data_source.current(),
            replace_activity=True,
        )
        self._refresh_command_input()
        self.set_focus(self.query_one("#cmd", Input))

    def on_unmount(self) -> None:
        if self._backend_event_unsubscribe is not None:
            self._backend_event_unsubscribe()
            self._backend_event_unsubscribe = None
        close = getattr(self._backend, "close", None)
        if callable(close):
            close()

    def _handle_backend_event(self, event) -> None:
        self.call_from_thread(self._apply_backend_event, event)

    def _apply_backend_event(self, event) -> None:
        if isinstance(event, DataUpdatedEvent):
            self._apply_data_state(event.data, replace_activity=True)
            return
        if isinstance(event, ActivityLogAppendedEvent):
            self._remember_activity_display_order(event.entry)
            self._protocol_activity_log.append(event.entry)
            if len(self._protocol_activity_log) > self._activity_log_max_lines:
                self._protocol_activity_log = self._protocol_activity_log[
                    -self._activity_log_max_lines :
                ]
            activity = self.query_one("#activity", ActivityLog)
            activity.write(
                _build_log_text(event.entry.message_text, timestamp=event.entry.timestamp)
            )
            self._refresh_activity_title()
            return
        if isinstance(event, AnnouncementEvent):
            self._play_local_announcement(event)

    def _apply_data_state(self, data, *, replace_activity: bool) -> None:
        self._runtime_state.routine_active = data.routine.routine_active
        self._runtime_state.active_routine_name = data.routine.active_routine_name
        self._runtime_state.haul_stop_requested = data.routine.haul_stop_requested
        self._runtime_state.verbose_controls = data.routine.verbose_controls
        self._runtime_state.instant_mode = data.routine.instant_mode
        self._runtime_state.shutdown_requested = data.routine.shutdown_requested
        self._runtime_state.shutdown_finalized = data.routine.shutdown_finalized
        self._runtime_state.haul_phase = data.routine.haul_phase
        self._runtime_state.haul_phase_station_index = data.routine.haul_phase_station_index
        self._saved_state.default_haul = dict(data.command_history.default_haul)
        self._saved_state.history = list(data.command_history.history_entries)
        self._ship = ShipState(
            commander=data.ship.commander,
            ship_type=data.ship.ship_type,
            system=data.ship.system,
            station=data.ship.station,
            status=data.ship.status,
            fuel_level=data.ship.fuel_level,
            fuel_capacity=data.ship.fuel_capacity,
            credits=data.ship.credits,
            cargo_count=data.ship.cargo_count,
            cargo_capacity=data.ship.cargo_capacity,
            cargo_inventory=list(data.ship.cargo_inventory),
            target=data.ship.target,
            destination_system=data.ship.destination_system,
            destination_body=data.ship.destination_body,
            destination_name=data.ship.destination_name,
        )
        self._market = MarketData(
            station=data.market.station,
            system=data.market.system,
            timestamp=data.market.timestamp,
            market_id=data.market.market_id,
            items=list(data.market.items),
            locked=self._market.locked,
        )
        self._tts.set_commander_name(data.ship.commander)
        if replace_activity:
            self._replace_activity_log(
                [
                    ActivityLogEntry(
                        entry_id=entry.entry_id,
                        timestamp=entry.timestamp,
                        message_text=entry.message_text,
                        severity=entry.severity,
                    )
                    for entry in data.activity_log.entries
                ]
            )
        self._refresh_status()
        self._refresh_haul_stats()
        self._refresh_market()
        self._refresh_trade_routes()
        self._update_resume_detail()
        self._refresh_command_input()

    def _play_local_announcement(self, event: AnnouncementEvent) -> None:
        parsed_id = parse_announcement_id(event.announcement_id)
        if parsed_id is None:
            return
        self._tts.announce(parsed_id, **event.message_values)

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _build_controls(self) -> None:
        if self._ctx.binding_lookup is None or self._ctx.input_controller is None:
            self._log("[yellow]Bindings not loaded — routine commands (dock/undock/buy/sell) unavailable[/]")
            return
        self._controls = ShipControls.from_binding_lookup(
            self._ctx.binding_lookup,
            self._ctx.input_controller,
            minimum_action_hold_s=self._config.controls.minimum_action_hold_seconds,
            continuous_action_hold_s=self._config.controls.continuous_action_hold_seconds,
            sleeper=self._make_sleeper(),
        )

    def _load_saved_state(self) -> None:
        _persistence.load_saved_state(self)

    def _log_bindings_status(self) -> None:
        bindings_path = self._ctx.bindings.effective.get("path")
        bindings_source = self._ctx.bindings.cli_source_status()
        reason = self._ctx.bindings.effective.get("reason", "unknown")

        if bindings_path:
            self._log(
                f"[dim]Bindings file: {escape(str(bindings_path))} "
                f"(source: {escape(bindings_source)})[/]"
            )
        else:
            self._log(
                f"[yellow]Bindings file unavailable "
                f"(source: {escape(bindings_source)}; reason: {escape(str(reason))})[/]"
            )

        if self._ctx.binding_lookup is None:
            return

        issues = {
            action: result
            for action, result in self._ctx.binding_lookup.issues().items()
            if action not in _STARTUP_BINDING_WARNING_IGNORED_ACTIONS
        }
        if not issues:
            return

        self._log(
            f"[yellow]Bindings warning — {len(issues)} routine action(s) "
            "have no usable keyboard mapping.[/]"
        )
        for action, result in sorted(issues.items()):
            reason = result.reason or result.status
            hint = format_binding_action_hint(action)
            self._log(
                f"[yellow]- {escape(action)} -> {escape(hint)}: {escape(reason)}[/]"
            )

    def _save_saved_state(self) -> None:
        _persistence.save_saved_state(self)

    def _clear_session_stats(self) -> None:
        _persistence.clear_session_stats(self)
        self._refresh_haul_stats()
        self._publish_protocol_data_refresh()

    def _stop_session_stats(self) -> None:
        _persistence.stop_session_stats(self)
        self._refresh_haul_stats()
        self._publish_protocol_data_refresh()

    def _log_startup_modes(self) -> None:
        state = "on" if self._instant_mode else "off"
        self._log(f"[dim]Instant mode {state} — control with: instant[/]")
        if self._ctx.input_controller is not None:
            self._log(
                f"[dim]Input target {escape(self._describe_input_target())} "
                "— control with: set_pid | set_hwnd[/]"
            )

    def _describe_input_target(self) -> str:
        controller = self._ctx.input_controller
        if controller is None:
            return "unavailable"
        return controller.current_target().summary()

    def _set_foreground_input_target(self) -> str:
        controller = self._require_input_controller()
        target = controller.set_foreground_target()
        return target.summary()

    def _set_pid_input_target(self, pid: int) -> str:
        controller = self._require_input_controller()
        target = controller.set_pid_target(pid)
        return target.summary()

    def _set_hwnd_input_target(self, hwnd: int) -> str:
        controller = self._require_input_controller()
        target = controller.set_hwnd_target(hwnd)
        return target.summary()

    def _auto_target_input(self, process_name: str, *, prefer: str) -> str:
        controller = self._require_input_controller()
        target = controller.auto_target(process_name, prefer=prefer)
        return target.summary()

    def _require_input_controller(self):
        controller = self._ctx.input_controller
        if controller is None:
            raise RuntimeError("No local input backend is available for this runtime.")
        return controller

    def _announce_startup_greeting(self) -> None:
        self._announce_tts(AnnouncementId.STARTUP_GREETING)

    def _start_update_check(self) -> None:
        if not self._config.control_room.check_for_updates:
            self._log_current_version(is_latest=None)
            return
        self._check_for_updates()

    def _log_current_version(self, *, is_latest: bool | None) -> None:
        current = _version.display_version(self._current_version)
        if is_latest is True:
            self._log(
                f"[dim]Currently running latest version "
                f"(*{escape(current)}*) of {_version.PROJECT_DISPLAY_NAME}[/]"
            )
            return
        self._log(
            f"[dim]Currently running version *{escape(current)}* of {_version.PROJECT_DISPLAY_NAME}[/]"
        )

    def _log_update_available(self, release: _version.GitHubRelease) -> None:
        self._log(
            f"[yellow]A newer {_version.PROJECT_DISPLAY_NAME} release is available: "
            f"{escape(release.display_name)}[/]"
        )
        self._log_current_version(is_latest=False)
        self._log(f"[dim]{escape(release.html_url)}[/]")

    def _bootstrap_ship_state(self) -> None:
        _bootstrap.bootstrap_ship_state(self)
        self._tts.set_commander_name(self._ship.commander)

    def _sync_status_state(self) -> None:
        _bootstrap.sync_status_state(self)
        _bootstrap.sync_cargo_manifest(self, update_count=False)

    # ── Rendering ──────────────────────────────────────────────────────────────

    def _refresh_status(self) -> None:
        self.query_one("#status", Static).update(
            Text.from_markup(_rendering.status_panel_markup(self._status_panel_view_model()))
        )

    def _refresh_haul_stats(self) -> None:
        widget = self.query_one("#haul", Static)
        widget.update(Text.from_markup(
            _rendering.haul_panel_markup(
                self._haul_panel_view_model(),
                now_fn=self._time_fn,
            )
        ))

    def _refresh_market(self) -> None:
        self._sync_presented_market_from_current_data()
        view_model = self._market_panel_view_model()
        self.query_one("#market-content", Static).update(
            Text.from_markup(
                _rendering.market_panel_markup(view_model)
            )
        )

    @staticmethod
    def _market_tab_id(side: str) -> str:
        return "market-tab-sell" if side == "sell" else "market-tab-buy"

    def _set_market_panel_tab(self, side: str) -> None:
        self._view_actions.market.set_tab(side)

    def _lock_market_display(self) -> None:
        self._view_actions.market.lock_display()

    def _unlock_market_display(self) -> None:
        self._view_actions.market.unlock_display()

    def _set_market_filter(self, value: str) -> None:
        self._view_actions.market.set_filter(value)

    def _clear_market_filter(self) -> None:
        self._view_actions.market.clear_filter()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tabs.id != "market-tabs":
            return
        if event.tab.id == "market-tab-sell":
            self._set_market_panel_tab("sell")
        else:
            self._set_market_panel_tab("buy")

    def _refresh_trade_routes(self) -> None:
        self._refresh_trade_route_picker()

    def _refresh_trade_route_picker(self) -> None:
        try:
            picker = self.query_one("#trade-route-picker", Vertical)
            option_list = self.query_one("#trade-route-list", OptionList)
            detail = self.query_one("#trade-route-detail", Static)
            main = self.query_one("#main", Horizontal)
        except Exception:
            return

        view_model = self._trade_route_picker_view_model()
        labels = [_rendering.trade_route_option_label(route) for route in view_model.routes]
        option_list.clear_options()
        option_list.add_options(labels)
        if view_model.routes:
            first_route = view_model.routes[0]
            self._debug_log(
                "trade_route_picker_refresh",
                route_count=len(view_model.routes),
                selected_trade_route_index=self._selected_trade_route_index,
                first_route_index=first_route.index,
                first_route_profit_per_trip=first_route.profit_per_trip,
                first_route_profit_per_hour=first_route.profit_per_hour,
                first_label=labels[0] if labels else "",
            )
        if view_model.routes:
            if self._selected_trade_route_index is None and view_model.selected_route is not None:
                self._selected_trade_route_index = view_model.selected_route.index
            option_list.highlighted = view_model.highlighted_index
            self._update_trade_route_detail(view_model.selected_route)
        else:
            option_list.highlighted = None
            detail.update(Text.from_markup("[dim]No trade routes loaded.[/]"))

        if view_model.visible:
            main.styles.display = "none"
            picker.styles.display = "block"
            try:
                self.set_focus(option_list)
            except ScreenStackError:
                return
            return
        picker.styles.display = "none"
        main.styles.display = "block"

    def _trade_route_picker_view_model(self) -> _view_models.TradeRoutePickerViewModel:
        return _view_models.trade_route_picker_view_model(
            self._trade_routes,
            self._trade_route_picker_state,
        )

    def _activity_auto_follow_paused(self) -> bool:
        try:
            return self.query_one("#activity", ActivityLog).auto_follow_paused
        except ScreenStackError:
            return False

    def _selected_trade_route(self) -> TradeRoute | None:
        selected_index = self._selected_trade_route_index
        if selected_index is None:
            return None
        return next((route for route in self._trade_routes.routes if route.index == selected_index), None)

    def _update_trade_route_detail(self, route: TradeRoute | None) -> None:
        try:
            detail = self.query_one("#trade-route-detail", Static)
        except Exception:
            return
        if route is None:
            detail.update(Text.from_markup("[dim]No trade route selected.[/]"))
            return
        view_model = self._trade_route_picker_view_model()
        markup = _rendering.trade_route_detail_markup(
            route,
            system_name=view_model.system_name,
            searched_at=view_model.searched_at,
            route_count=len(view_model.routes),
        )
        self._debug_log(
            "trade_route_detail_update",
            route_index=route.index,
            profit_per_trip=route.profit_per_trip,
            profit_per_hour=route.profit_per_hour,
            markup=markup,
        )
        detail.update(
            Text.from_markup(markup)
        )

    def _apply_replay_browser_visibility(self) -> None:
        try:
            activity = self.query_one("#activity", ActivityLog)
            replay_browser = self.query_one("#resume-browser", Vertical)
        except Exception:
            return
        if self._resume_open:
            activity.styles.display = "none"
            replay_browser.styles.display = "block"
            try:
                _replay.refresh_resume_help(self)
                _replay.update_resume_detail(self)
            except Exception:
                return
            return
        activity.styles.display = "block"
        replay_browser.styles.display = "none"

    def _replace_activity_log(self, entries: list[ActivityLogEntry]) -> None:
        entries = list(entries)
        if self._backend.exit_detaches_remote_session():
            entries += list(self._local_activity_log)
        entries = self._activity_entries_in_display_order(entries)
        if len(entries) > self._activity_log_max_lines:
            entries = entries[-self._activity_log_max_lines :]
        self._trim_activity_display_order(entries)
        activity = self.query_one("#activity", ActivityLog)
        clear = getattr(activity, "clear", None)
        if callable(clear):
            clear()
        elif hasattr(activity, "writes"):
            activity.writes = []
        for entry in entries:
            activity.write(_build_log_text(entry.message_text, timestamp=entry.timestamp))
        self._protocol_activity_log = list(entries)
        self._refresh_activity_title()

    @staticmethod
    def _activity_entry_key(entry: ActivityLogEntry) -> tuple[str, str, str]:
        return (entry.entry_id, entry.timestamp, entry.message_text)

    def _remember_activity_display_order(self, entry: ActivityLogEntry) -> None:
        key = self._activity_entry_key(entry)
        if key in self._activity_display_order:
            return
        self._activity_display_order[key] = self._next_activity_display_order
        self._next_activity_display_order += 1

    def _activity_entries_in_display_order(
        self,
        entries: list[ActivityLogEntry],
    ) -> list[ActivityLogEntry]:
        for entry in entries:
            self._remember_activity_display_order(entry)
        return sorted(
            entries,
            key=lambda entry: self._activity_display_order[self._activity_entry_key(entry)],
        )

    def _trim_activity_display_order(self, entries: list[ActivityLogEntry]) -> None:
        retained = {self._activity_entry_key(entry) for entry in entries}
        self._activity_display_order = {
            key: order for key, order in self._activity_display_order.items() if key in retained
        }

    def _is_active_operator(self) -> bool:
        return self._dependencies.data_source.current().session.client_role == "active_operator"

    def _check_routine_ready(self) -> bool:
        if self._backend.exit_detaches_remote_session():
            if not self._is_active_operator():
                self._log("[yellow]Observer session is read-only.[/]")
                return False
            if self._routine_active:
                self._log("[yellow]A routine is already running — wait for it to finish[/]")
                return False
            return True
        return _workers.check_routine_ready(self)

    def _refresh_command_input(self) -> None:
        try:
            command_input = self.query_one("#cmd", Input)
        except Exception:
            return
        if not self._is_active_operator():
            command_input.disabled = True
            command_input.placeholder = "observer mode - read only"
            return
        command_input.disabled = False
        if self._prompt_state.command_input_prefill_active:
            command_input.placeholder = self._prompt_state.command_input_placeholder
            if not command_input.value and self._prompt_state.command_input_value:
                command_input.value = self._prompt_state.command_input_value
                command_input.cursor_position = len(command_input.value)
            return
        command_input.placeholder = self._default_command_placeholder

    def _view_market_data(self) -> MarketData:
        return MarketData(
            station=self._presented_market.station,
            system=self._presented_market.system,
            timestamp=self._presented_market.timestamp,
            market_id=self._presented_market.market_id,
            items=list(self._presented_market.items),
            locked=self._presented_market.locked,
        )

    def _sync_presented_market_from_current_data(self, *, force: bool = False) -> None:
        market = self._dependencies.data_source.current().market
        if (
            not self._market.locked
            or force
            or self._market_identity(market) == self._market_identity(self._presented_market)
        ):
            self._presented_market = MarketData(
                station=market.station,
                system=market.system,
                timestamp=market.timestamp,
                market_id=market.market_id,
                items=list(market.items),
                locked=self._market.locked,
            )
            return
        self._presented_market.locked = True

    @staticmethod
    def _market_identity(market: MarketData) -> tuple[object, ...] | None:
        if market.market_id is not None:
            return ("market_id", market.market_id)
        station = market.station.strip().lower()
        system = market.system.strip().lower()
        if station and station != "?" and system and system != "?":
            return ("station_system", station, system)
        return None

    def _status_panel_view_model(self) -> _view_models.StatusPanelViewModel:
        return _view_models.status_panel_view_model(
            self._dependencies.data_source.current().ship
        )

    def _haul_panel_view_model(self) -> _view_models.HaulPanelViewModel:
        data = self._dependencies.data_source.current()
        return _view_models.haul_panel_view_model(
            data.haul_session,
            current_balance=data.ship.credits,
        )

    def _market_panel_view_model(self) -> _view_models.MarketPanelViewModel:
        return _view_models.market_panel_view_model(
            self._view_market_data(),
            market_filter=self._market_filter,
            side=self._runtime_state.market_panel_tab,
        )

    def _refresh_activity_title(self) -> None:
        title = "ACTIVITY"
        if self._activity_auto_follow_paused():
            title += " • AUTO-FOLLOW PAUSED"
        self.query_one("#activity", ActivityLog).border_title = title

    def _log(self, msg: str) -> None:
        activity = self.query_one("#activity", ActivityLog)
        entry = build_activity_log_entry(msg)
        self._remember_activity_display_order(entry)
        activity.write(_build_log_text(entry.message_text, timestamp=entry.timestamp))
        if self._backend.exit_detaches_remote_session():
            self._local_activity_log.append(entry)
            if len(self._local_activity_log) > self._activity_log_max_lines:
                self._local_activity_log = self._local_activity_log[
                    -self._activity_log_max_lines :
                ]
        self._protocol_activity_log.append(entry)
        if len(self._protocol_activity_log) > self._activity_log_max_lines:
            self._protocol_activity_log = self._protocol_activity_log[-self._activity_log_max_lines :]
        self._backend.publish_activity_log(entry)
        self._refresh_activity_title()

    def _start_haul_stats(
        self,
        *,
        station_1_buying: str,
        station_2_buying: str,
        station_1: str,
        station_2: str,
    ) -> None:
        _haul_tracking.start_haul_stats(
            self,
            station_1_buying=station_1_buying,
            station_2_buying=station_2_buying,
            station_1=station_1,
            station_2=station_2,
        )

    def _stop_haul_stats(self) -> None:
        _haul_tracking.stop_haul_stats(self)

    def _finalize_completed_haul_run(self) -> None:
        _haul_tracking.finalize_completed_haul_run(self)

    def _handle_haul_event(self, ev: dict[str, Any], *, station_before: str | None) -> None:
        _haul_tracking.handle_haul_event(self, ev, station_before=station_before)

    def _announce_tts(self, message_id: AnnouncementId, /, **values: object) -> None:
        render_announcement = getattr(self._tts, "render_announcement", None)
        rendered = (
            render_announcement(message_id, **values)
            if callable(render_announcement)
            else None
        )
        if rendered is not None:
            announcement = build_announcement_event(
                announcement_id=message_id.value,
                message_text=rendered,
                message_values=dict(values),
            )
            self._protocol_announcements.append(announcement)
            if len(self._protocol_announcements) > _PROTOCOL_ANNOUNCEMENT_CACHE_LIMIT:
                self._protocol_announcements = self._protocol_announcements[-_PROTOCOL_ANNOUNCEMENT_CACHE_LIMIT :]
            self._backend.publish_announcement(announcement)
        self._tts.announce(message_id, **values)

    def _announce_tts_for_event(self, ev: dict[str, Any], *, station_before: str | None) -> None:
        event = str(ev.get("event", ""))
        if event == "FSDTarget":
            system_name = str(ev.get("Name", "")).strip()
            if system_name:
                self._announce_tts(AnnouncementId.DESTINATION_SET, system_name=system_name)
        elif event == "Docked":
            self._announce_tts(AnnouncementId.DOCKING_COMPLETE)
        elif event == "Undocked" and station_before and self._haul_stats.active:
            self._announce_tts(AnnouncementId.UNDOCKING)
        elif event == "StartJump" and str(ev.get("JumpType", "")).lower() == "hyperspace":
            system_name = str(ev.get("StarSystem", "")).strip() or str(self._ship.target or "").strip()
            if system_name:
                self._announce_tts(AnnouncementId.JUMP_INITIATED, system_name=system_name)
        elif event == "FSDJump":
            system_name = str(ev.get("StarSystem", "")).strip()
            if system_name:
                self._announce_tts(AnnouncementId.ARRIVAL, system_name=system_name)
        elif event == "SupercruiseExit":
            station_name = (
                str(ev.get("StationName", "")).strip()
                or str(ev.get("Body", "")).strip()
                or str(ev.get("BodyName", "")).strip()
            )
            if station_name:
                self._announce_tts(AnnouncementId.APPROACHING_STATION, station_name=station_name)
        elif event == "MarketBuy":
            self._announce_tts(AnnouncementId.CARGO_LOADED)
        elif event == "MarketSell" and "TotalSale" in ev:
            self._announce_tts(
                AnnouncementId.SALE_PROFIT,
                revenue_short=format_credits_short(int(ev["TotalSale"])),
            )

    def _publish_protocol_data_refresh(self) -> None:
        sink = self._protocol_external_event_sink
        if sink is None:
            return
        sink.publish_data_refresh()

    def _default_haul_matches(self, entry: CommandHistoryEntry) -> bool:
        return _replay.default_haul_matches(self, entry)

    def _resume_label(self, entry: CommandHistoryEntry) -> str:
        return _history.resume_label(entry, self._saved_state.default_haul)

    def _filtered_resume_entries(self) -> list[ReplaySelection]:
        return _replay.filtered_resume_entries(self)

    def _refresh_resume_help(self) -> None:
        _replay.refresh_resume_help(self)

    def _selected_resume_entry(self) -> CommandHistoryEntry | None:
        return _replay.selected_resume_entry(self)

    def _show_resume_picker(self) -> None:
        _replay.show_resume_picker(self)

    def _refresh_resume_picker(self) -> None:
        _replay.refresh_resume_picker(self)

    def _close_resume_picker(self) -> None:
        _replay.close_resume_picker(self)

    def _resume_execute_selected(self) -> None:
        entry = self._selected_resume_entry()
        if entry is None:
            return
        self._close_resume_picker()
        _replay.replay_history_entry(self, entry, edit=False)

    def _resume_execute_selected_immediate(self) -> None:
        entry = self._selected_resume_entry()
        if entry is None:
            return
        self._close_resume_picker()
        _replay.replay_history_entry(self, entry, edit=False, skip_delay=True)

    def _resume_edit_selected(self) -> None:
        entry = self._selected_resume_entry()
        if entry is None:
            return
        self._close_resume_picker()
        _replay.replay_history_entry(self, entry, edit=True)

    def _resume_toggle_default_selected(self) -> None:
        entry = self._selected_resume_entry()
        if entry is None:
            return
        if entry.command != "haul" or _history.is_haul_search_entry(entry):
            self._log("[dim]Only two-station haul loop entries can be saved as the default.[/]")
            return
        if _replay.default_haul_matches(self, entry):
            self._saved_state.default_haul = {}
            self._log("[dim]Cleared saved default haul.[/]")
        else:
            self._saved_state.default_haul = {
                str(key): str(value) for key, value in entry.params.items()
            }
            cargo = self._saved_state.default_haul.get("station_1_buying", "haul")
            self._log(f"[dim]Saved default haul from history: {escape(cargo)}[/]")
        self._save_saved_state()
        self._refresh_resume_picker()

    def _close_trade_route_picker(self) -> None:
        self._view_actions.trade_routes.close()

    def _move_trade_route_selection(self, offset: int) -> None:
        self._view_actions.trade_routes.move_selection(offset)

    def _load_selected_trade_route(self) -> None:
        self._view_actions.trade_routes.load_selected()

    def _set_destination_for_selected_trade_route(self) -> None:
        self._view_actions.trade_routes.set_destination_for_selected()

    def _update_resume_detail(self) -> None:
        _replay.update_resume_detail(self)

    def _replay_history_entry(
        self,
        entry: CommandHistoryEntry,
        *,
        edit: bool,
        skip_delay: bool = False,
    ) -> None:
        _replay.replay_history_entry(self, entry, edit=edit, skip_delay=skip_delay)

    # ── Market JSON ────────────────────────────────────────────────────────────

    # ── Journal event processing ───────────────────────────────────────────────

    def _handle_event(self, ev: dict[str, Any]) -> None:
        self._append_journal_event(ev)
        event = ev.get("event", "")
        station_before = self._ship.station
        _events.apply_ship_event(self._ship, ev)
        self._tts.set_commander_name(self._ship.commander)
        self._sync_status_state()
        if event in {"Cargo", "MarketBuy", "MarketSell"}:
            _bootstrap.sync_cargo_manifest(self)

        if event == "Docked":
            self._load_market_json()

        msg = self._activity_line(ev)
        if msg:
            self._log(msg)

        self._refresh_status()
        self._handle_haul_event(ev, station_before=station_before)
        self._announce_tts_for_event(ev, station_before=station_before)
        self._publish_protocol_data_refresh()

    def _activity_line(self, ev: dict[str, Any]) -> str | None:
        return _rendering.activity_line(ev)

    # ── Background status watcher ──────────────────────────────────────────────

    @work(thread=True, group="watchers", exclusive=True)
    def _start_watcher(self) -> None:
        _workers.start_watcher_loop(self)

    @work(thread=True, group="watchers", exclusive=False)
    def _check_for_updates(self) -> None:
        release = self._version_source.fetch_latest_github_release()
        if release is None:
            self.call_from_thread(self._log_current_version, is_latest=None)
            return
        if not _version.is_newer_version(release.version, self._current_version):
            self.call_from_thread(self._log_current_version, is_latest=True)
            return
        self.call_from_thread(self._log_update_available, release)

    # ── Routine dispatch ───────────────────────────────────────────────────────

    @work(thread=True, group="routines", exclusive=True)
    def _run_in_thread(self, fn: Callable[[], RoutineResult | None]) -> None:
        _workers.run_routine_thread(self, fn)

    def _clear_routine(self) -> None:
        _workers.clear_routine(self)

    # ── Quit ───────────────────────────────────────────────────────────────────

    def action_request_interrupt(self) -> None:
        self._exit_requested_once = False
        self._handle_interrupt("Ctrl-C")

    def action_request_exit(self) -> None:
        if self._exit_prompt_active:
            return
        if not self._exit_requested_once:
            self._exit_requested_once = True
            self._log("[yellow]Ctrl-D received — press Ctrl-D again to exit control room.[/]")
            return
        self._exit_requested_once = False
        if self._should_prompt_remote_exit():
            self._start_remote_exit_prompt()
            return
        self._request_shutdown("Ctrl-D")

    def request_sigint(self) -> None:
        self._sigint_pending = True

    def _drain_pending_sigint(self) -> None:
        if not self._sigint_pending:
            return
        self._sigint_pending = False
        self.action_request_interrupt()

    def _cancel_prompt_flow(self, source: str) -> bool:
        return _prompts.cancel_prompt_flow(
            self,
            default_placeholder=self._default_command_placeholder,
            source=source,
        )

    def _handle_interrupt(self, source: str) -> None:
        if self._cancel_prompt_flow(source):
            return
        self._cancel_active_routine(source)

    def _cancel_active_routine(self, source: str) -> None:
        if self._routine_worker is None:
            if self._backend.exit_detaches_remote_session() and self._routine_active:
                self._dependencies.execution.cancel_active_routine()
                self._log(f"[yellow]{escape(source)} received — cancelling active routine.[/]")
                return
            self._routine_active = False
            self._active_routine_name = None
            self._clear_pending_haul_stop()
            self._log(f"[yellow]{escape(source)} received — no active routine to cancel.[/]")
            return
        if self._active_routine_name == "haul" and not self._haul_stop_requested:
            self._haul_stop_requested = True
            self._log(
                f"[yellow]{escape(source)} received — haul will stop after this run at station 1 before a new cycle.[/]"
            )
            self._announce_tts(AnnouncementId.HAUL_STOP_AFTER_RUN)
            return
        if self._active_routine_name == "multi_leg_haul" and not self._haul_stop_requested:
            self._haul_stop_requested = True
            self._log(
                f"[yellow]{escape(source)} received — multi-leg haul will stop at the next station boundary before departure.[/]"
            )
            return
        if self._active_routine_name == "haul" and self._haul_stop_requested:
            self._haul_stop_requested = False
            self._log(f"[yellow]{escape(source)} received again — cancelling haul immediately.[/]")
            self._announce_tts(AnnouncementId.HAUL_CANCELLED)
        elif self._active_routine_name == "multi_leg_haul" and self._haul_stop_requested:
            self._haul_stop_requested = False
            self._log(f"[yellow]{escape(source)} received again — cancelling multi-leg haul immediately.[/]")
            self._announce_tts(AnnouncementId.HAUL_CANCELLED)
        else:
            self._log(f"[yellow]{escape(source)} received — cancelling active routine.[/]")
            if self._active_routine_name in {"haul", "multi_leg_haul"}:
                self._announce_tts(AnnouncementId.HAUL_CANCELLED)
        self._routine_worker.cancel()

    def _clear_pending_haul_stop(self) -> None:
        self._haul_stop_requested = False

    def _should_prompt_remote_exit(self) -> bool:
        return (
            self._backend.exit_detaches_remote_session()
            and self._is_active_operator()
            and self._routine_active
        )

    def _start_remote_exit_prompt(self) -> None:
        self._exit_prompt_active = True
        self._log(
            "[yellow]Remote routine still running — Enter exits this client and leaves it running; "
            "type cancel to stop the routine and exit; type no to stay connected.[/]"
        )
        try:
            command_input = self.query_one("#cmd", Input)
        except Exception:
            return
        command_input.placeholder = "Enter = leave routine running | cancel = stop routine and exit | no = stay"

    def _handle_exit_prompt_input(self, raw: str) -> None:
        value = raw.strip().lower()
        self._exit_prompt_active = False
        try:
            command_input = self.query_one("#cmd", Input)
        except Exception:
            command_input = None
        if command_input is not None:
            command_input.placeholder = self._default_command_placeholder
        if value in {"", "enter", "default", "leave"}:
            self._request_shutdown("Ctrl-D")
            return
        if value in {"cancel", "stop", "yes", "y"}:
            self._backend.interrupt_active_routine()
            self._request_shutdown("Ctrl-D")
            return
        self._log("[yellow]Exit cancelled — staying connected.[/]")

    def _request_shutdown(self, source: str) -> None:
        if self._shutdown_requested:
            return
        self._exit_requested_once = False
        self._exit_prompt_active = False
        self._shutdown_requested = True
        self._log(f"[yellow]{escape(source)} received — exiting control room.[/]")
        self._finalize_shutdown()

    def _append_journal_event(self, ev: dict[str, Any]) -> None:
        handle = self._ensure_journal_artifact_log_handle()
        if handle is None:
            return
        handle.write(json.dumps(ev))
        handle.write("\n")
        self._journal_artifact_log_pending_writes += 1
        if self._journal_artifact_log_pending_writes >= _JOURNAL_ARTIFACT_LOG_FLUSH_EVERY:
            self._flush_journal_artifact_log()

    def _debug_log(self, event: str, /, **fields: object) -> None:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            **fields,
        }
        try:
            self._debug_artifact_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._debug_artifact_log_path.open("a", encoding="utf-8", buffering=1) as handle:
                handle.write(json.dumps(payload, ensure_ascii=True))
                handle.write("\n")
        except OSError:
            return

    def _ensure_journal_artifact_log_handle(self) -> IO[str] | None:
        if self._journal_artifact_log_handle is not None:
            return self._journal_artifact_log_handle
        try:
            self._journal_artifact_log_path.parent.mkdir(parents=True, exist_ok=True)
            self._journal_artifact_log_handle = self._journal_artifact_log_path.open(
                "a",
                encoding="utf-8",
                buffering=_JOURNAL_ARTIFACT_LOG_BUFFER_SIZE,
            )
        except OSError:
            return None
        return self._journal_artifact_log_handle

    def _flush_journal_artifact_log(self) -> None:
        handle = self._journal_artifact_log_handle
        if handle is None or self._journal_artifact_log_pending_writes == 0:
            return
        try:
            handle.flush()
        except OSError:
            return
        self._journal_artifact_log_pending_writes = 0

    def _finalize_shutdown(self) -> None:
        if self._shutdown_finalized:
            return
        self._shutdown_finalized = True
        if self._journal_artifact_log_handle is not None:
            self._flush_journal_artifact_log()
            try:
                self._journal_artifact_log_handle.close()
            except OSError:
                pass
            self._journal_artifact_log_handle = None
            self._journal_artifact_log_pending_writes = 0
        self._tts.close()
        self.workers.cancel_group(self, "watchers")
        self.workers.cancel_group(self, "routines")
        self.exit()

    def action_open_history(self) -> None:
        if self._haul_prompt_step or self._haul_confirm_buy_station or self._dest_prompt_destination:
            return
        if self._resume_open:
            self._close_resume_picker()
            return
        self._show_resume_picker()

    # ── Command input ──────────────────────────────────────────────────────────

    def on_key(self, event) -> None:
        """Handle up/down arrow keys for readline-style command history."""
        if event.key == "ctrl+r":
            event.prevent_default()
            self.action_open_history()
            return
        if event.key == "ctrl+d":
            event.prevent_default()
            self.action_request_exit()
            return
        if event.key == "ctrl+c":
            event.prevent_default()
            self.action_request_interrupt()
            return
        if self._trade_route_picker_open:
            if event.key == "escape" or event.key == "q":
                event.prevent_default()
                self._close_trade_route_picker()
            elif event.key == "up":
                event.prevent_default()
                self._move_trade_route_selection(-1)
            elif event.key == "down":
                event.prevent_default()
                self._move_trade_route_selection(1)
            elif event.key == "d":
                event.prevent_default()
                self._set_destination_for_selected_trade_route()
            elif event.key == "enter":
                event.prevent_default()
                self._load_selected_trade_route()
            return
        if self._resume_open:
            if event.key != "enter":
                self._suppress_replay_enter_until = 0.0
            if event.key == "escape" or (event.key == "q" and not self._resume_filter):
                event.prevent_default()
                self._close_resume_picker()
            elif event.key == "up":
                event.prevent_default()
                _replay.move_resume_selection(self, -1)
            elif event.key == "down":
                event.prevent_default()
                _replay.move_resume_selection(self, 1)
            elif event.key == "e" and not self._resume_filter:
                event.prevent_default()
                self._resume_edit_selected()
            elif event.character == "!":
                event.prevent_default()
                self._resume_execute_selected_immediate()
            elif event.character == "*":
                event.prevent_default()
                self._resume_toggle_default_selected()
            elif event.key == "enter":
                event.prevent_default()
                if self._time_fn() <= self._suppress_replay_enter_until:
                    self._suppress_replay_enter_until = 0.0
                    return
                self._resume_execute_selected()
            elif event.key == "backspace":
                event.prevent_default()
                if self._resume_filter:
                    self._resume_filter = self._resume_filter[:-1]
                    self._refresh_resume_picker()
            elif event.character and event.character.isprintable() and len(event.character) == 1:
                event.prevent_default()
                self._resume_filter = self._resume_filter + event.character
                self._refresh_resume_picker()
            return
        if self._exit_prompt_active:
            if event.key == "enter":
                event.prevent_default()
                cmd_input = self.query_one("#cmd", Input)
                raw = cmd_input.value
                cmd_input.value = ""
                self._handle_exit_prompt_input(raw)
            return
        if self._haul_prompt_step or self._haul_confirm_buy_station or self._dest_prompt_destination:
            if event.key == "enter":
                event.prevent_default()
                cmd_input = self.query_one("#cmd", Input)
                raw = cmd_input.value
                cmd_input.value = ""
                self._submit_prompt_input(raw)
            return  # don't interfere with multi-step haul prompts
        if event.key not in ("up", "down"):
            return
        event.prevent_default()
        cmd_input = self.query_one("#cmd", Input)
        if not self._history:
            return
        if event.key == "up":
            if self._history_pos == len(self._history):
                # entering history: save current draft
                self._history_draft = cmd_input.value
            if self._history_pos > 0:
                self._history_pos -= 1
                cmd_input.value = self._history[self._history_pos]
                cmd_input.cursor_position = len(cmd_input.value)
        else:  # down
            if self._history_pos < len(self._history):
                self._history_pos += 1
                if self._history_pos == len(self._history):
                    cmd_input.value = self._history_draft
                else:
                    cmd_input.value = self._history[self._history_pos]
                cmd_input.cursor_position = len(cmd_input.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if getattr(event.input, "id", None) not in {None, "cmd"}:
            return
        if self._prompt_state.command_input_prefill_active:
            self._prompt_state.command_input_value = event.input.value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value
        event.input.value = ""

        if self._exit_prompt_active:
            self._handle_exit_prompt_input(raw)
            return

        if self._haul_prompt_step or self._haul_confirm_buy_station or self._dest_prompt_destination:
            self._submit_prompt_input(raw)
            return

        raw = raw.strip()
        if not raw:
            return

        if raw.lower() in {"replay", "history"}:
            # Ignore the same Enter key if it also arrives after the replay browser opens.
            self._suppress_replay_enter_until = self._time_fn() + 0.1
        self._dispatch_command(raw)

    def _dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        self._dependencies.execution.submit_command(raw, skip_delay=skip_delay)

    def _submit_prompt_input(self, raw: str) -> None:
        if self._haul_prompt_step:
            self._handle_haul_prompt(raw)
            return
        if self._haul_confirm_buy_station:
            self._handle_haul_confirm_prompt(raw)
            return
        if self._dest_prompt_destination:
            dispatch = _prompts.resolve_destination_prompt_submission(
                self._prompt_state,
                raw,
                parse_optional_nonnegative_float=lambda value, default, label: (
                    self._parse_optional_nonnegative_float(
                        value,
                        default=default,
                        label=label,
                    )
                ),
            )
            if dispatch is None:
                return
            try:
                command_input = self.query_one("#cmd", Input)
                command_input.placeholder = self._default_command_placeholder
                command_input.value = ""
                command_input.cursor_position = 0
            except Exception:
                pass
            self._dispatch_dest(
                dispatch.destination,
                dispatch.galaxy_map_settle,
                skip_delay=dispatch.skip_delay,
                raw_command=dispatch.raw_command,
            )

    def _dispatch_dest(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._dependencies.execution.dispatch_destination(
            destination,
            galaxy_map_settle,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )

    def _dispatch_haul_loop(
        self,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._dependencies.execution.dispatch_haul_loop(
            params=dict(self._haul_params),
            skip_delay=skip_delay,
            raw_command=raw_command,
        )

    def _handle_haul_prompt(self, value: str) -> None:
        self._dependencies.execution.handle_haul_prompt(value)

    def _handle_haul_confirm_prompt(self, value: str) -> None:
        self._dependencies.execution.handle_haul_confirm_prompt(value)

    def _parse_optional_nonnegative_float(self, raw: str, *, default: float, label: str) -> float | None:
        return _prompts.parse_optional_nonnegative_float(
            self,
            raw,
            default=default,
            label=label,
        )


    def on_option_list_option_highlighted(self, message: OptionList.OptionHighlighted) -> None:
        if message.option_list.id == "resume-list":
            _replay.sync_selected_resume_entry_from_widget(self)
            self._update_resume_detail()
        elif message.option_list.id == "trade-route-list":
            highlighted = message.option_list.highlighted
            if highlighted is None or highlighted < 0 or highlighted >= len(self._trade_routes.routes):
                return
            route = self._trade_routes.routes[highlighted]
            self._selected_trade_route_index = route.index
            self._update_trade_route_detail(route)

    def on_option_list_option_selected(self, message: OptionList.OptionSelected) -> None:
        if message.option_list.id == "resume-list":
            self._resume_execute_selected()
        elif message.option_list.id == "trade-route-list":
            self._load_selected_trade_route()


# ── Entry point ────────────────────────────────────────────────────────────────


DEFAULT_OBSERVER_ACCESS_TOKEN = "edcr"


def _is_loopback_ipv4(host: str) -> bool:
    return host.startswith("127.")


def _detect_lan_host() -> str:
    candidates: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            candidates.append(probe.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM):
            candidates.append(info[4][0])
    except OSError:
        pass

    for host in candidates:
        if host and not _is_loopback_ipv4(host):
            return host

    raise RuntimeError("could not determine a LAN IPv4 address; use --host explicitly")


def main() -> None:
    parser = argparse.ArgumentParser(description="ED AutoPilot Control Room — live TUI")
    parser.add_argument("mode", nargs="?", choices=["serve", "connect"])
    parser.add_argument("target", nargs="?", help="server host[:port] for connect mode")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--market", metavar="FILTER", help="initial market filter (e.g. --market aluminium)")
    parser.add_argument("--host", help="serve bind host (default: 127.0.0.1)")
    parser.add_argument(
        "--lan",
        action="store_true",
        help="serve on the detected non-loopback LAN IPv4 address",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", help="shared access token for serve/connect observer mode")
    parser.add_argument("--client-name", help="observer client name for connect mode")
    parser.add_argument(
        "--claim-operator",
        action="store_true",
        help="request active-operator role after connecting",
    )
    args = parser.parse_args()

    if args.lan and args.mode != "serve":
        parser.error("--lan is only valid with serve")

    if args.mode == "serve":
        from edap.control_room.server.serve import serve_observer_mode

        if args.lan and args.host:
            parser.error("serve --lan cannot be combined with --host")
        access_token = args.token or DEFAULT_OBSERVER_ACCESS_TOKEN
        web_default_access_token = "" if args.token else DEFAULT_OBSERVER_ACCESS_TOKEN
        try:
            host = _detect_lan_host() if args.lan else args.host or "127.0.0.1"
        except RuntimeError as exc:
            parser.error(str(exc))
        serve_observer_mode(
            config_path=args.config,
            host=host,
            port=args.port,
            access_token=access_token,
            web_default_access_token=web_default_access_token,
        )
        return
    if args.mode == "connect":
        from edap.control_room.client import connect_observer_mode

        if not args.target:
            parser.error("connect requires a target like 192.168.1.50:8765")
        if not args.token:
            parser.error("connect requires --token")
        connect_observer_mode(
            config_path=args.config,
            target=args.target,
            access_token=args.token,
            client_name=args.client_name,
            claim_operator=args.claim_operator,
        )
        return

    loaded = load_config_with_fallback(args.config)
    ctx = build_runtime_context(
        loaded.config,
        config_path=loaded.config_path,
        used_example_config_fallback=loaded.used_example_config_fallback,
        actions=_ALL_ROUTINE_ACTIONS,
    )
    journal_dir = ctx.journal.effective_path

    if journal_dir is None:
        print(
            "ERROR: "
            + error_text.render(
                loaded.config,
                "journal_dir_not_found",
                source_status=ctx.journal.cli_source_status(),
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    app = ControlRoomApp(ctx, market_filter=args.market)
    previous_sigint = signal.getsignal(signal.SIGINT)

    def handle_sigint(signum, frame) -> None:  # type: ignore[no-untyped-def]
        del signum, frame
        app.request_sigint()

    signal.signal(signal.SIGINT, handle_sigint)
    try:
        app.run()
    finally:
        signal.signal(signal.SIGINT, previous_sigint)


if __name__ == "__main__":
    main()
