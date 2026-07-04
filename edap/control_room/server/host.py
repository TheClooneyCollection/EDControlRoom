from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from rich.markup import escape

from edap.control_room import bootstrap as _bootstrap
from edap.control_room.app import ControlRoomApp
from edap.control_room.history import now_iso
from edap.control_room.routine_stop import RoutineStopMode
from edap.control_room_state import CommandHistoryEntry
from edap.inara.trade_routes import TradeRoute
from edap.runtime import RuntimeContext
from edap.state import JournalWatcher
from edap.tts import NullSpeechBackend, TTSAnnouncer


_CLIENT_LOCAL_REMOTE_VERBS = {
    "?",
    "commands",
    "dest",
    "haul",
    "help",
    "history",
    "home",
    "market",
    "replay",
    "set_dest",
}


class _ActivityWidgetStub:
    def __init__(self) -> None:
        self.auto_scroll = True
        self.border_title = "ACTIVITY"
        self.writes: list[object] = []
        self.styles = _StylesStub()

    @property
    def auto_follow_paused(self) -> bool:
        return not self.auto_scroll

    def write(self, content: object, **kwargs: object) -> None:
        self.writes.append((content, kwargs))


class _CommandInputWidgetStub:
    def __init__(self) -> None:
        self.placeholder = ""
        self.value = ""
        self.cursor_position = 0
        self.disabled = False


class _StylesStub:
    def __init__(self) -> None:
        self.display = "block"


class _StaticWidgetStub:
    def __init__(self) -> None:
        self.updated: object | None = None
        self.styles = _StylesStub()

    def update(self, content: object) -> None:
        self.updated = content


class _OptionListWidgetStub:
    def __init__(self) -> None:
        self.highlighted: int | None = 0
        self.options: list[object] = []

    def clear_options(self) -> None:
        self.options = []

    def add_options(self, options: list[object]) -> None:
        self.options.extend(options)


class _ContainerWidgetStub:
    def __init__(self) -> None:
        self.border_title = ""
        self.styles = _StylesStub()


class HeadlessControlRoomHost(ControlRoomApp):
    def __init__(
        self,
        ctx: RuntimeContext,
        *,
        market_filter: str | None = None,
    ) -> None:
        self._activity_widget = _ActivityWidgetStub()
        self._command_input_widget = _CommandInputWidgetStub()
        self._resume_help_widget = _StaticWidgetStub()
        self._resume_detail_widget = _StaticWidgetStub()
        self._resume_list_widget = _OptionListWidgetStub()
        self._resume_browser_widget = _ContainerWidgetStub()
        self._trade_route_help_widget = _StaticWidgetStub()
        self._trade_route_detail_widget = _StaticWidgetStub()
        self._trade_route_list_widget = _OptionListWidgetStub()
        self._trade_route_picker_widget = _ContainerWidgetStub()
        self._main_widget = _ContainerWidgetStub()
        super().__init__(ctx, market_filter=market_filter)
        self._tts = TTSAnnouncer(
            self._config.tts,
            platform_name=self._config.runtime.platform,
            backend=NullSpeechBackend(),
        )
        self._watcher_stop = threading.Event()
        self._watcher_thread: threading.Thread | None = None

    def query_one(self, selector: str, widget_type=None):  # type: ignore[override]
        if selector == "#activity":
            return self._activity_widget
        if selector == "#cmd":
            return self._command_input_widget
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
        raise LookupError(selector)

    def set_focus(self, widget: object) -> None:  # type: ignore[override]
        return None

    def _refresh_status(self) -> None:  # type: ignore[override]
        return None

    def _refresh_market(self) -> None:  # type: ignore[override]
        return None

    def _refresh_haul_stats(self) -> None:  # type: ignore[override]
        self._publish_data_refresh()

    def _refresh_trade_routes(self) -> None:  # type: ignore[override]
        return None

    def _refresh_activity_title(self) -> None:  # type: ignore[override]
        return None

    def call_from_thread(self, callback, *args, **kwargs):  # type: ignore[override]
        return callback(*args, **kwargs)

    def start(self) -> None:
        self._build_controls()
        self._load_saved_state()
        self._log_startup_modes()
        self._bootstrap_ship_state()
        self._announce_startup_greeting()
        self._load_market_json()
        self._start_watcher_loop()

    def close(self) -> None:
        self._watcher_stop.set()
        if self._watcher_thread is not None:
            self._watcher_thread.join(timeout=1.0)
        self._tts.close()

    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None:
        resolved = raw_input
        if skip_delay is True and not raw_input.startswith("!"):
            resolved = f"!{raw_input}"
        if self._is_client_local_remote_command(resolved):
            self._record_unknown_remote_command(resolved)
            self._publish_data_refresh()
            return
        self._backend.submit_input(resolved)
        self._publish_data_refresh()

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._debug_log(
            "server_dispatch_destination_received",
            destination=destination,
            galaxy_map_settle=galaxy_map_settle,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )
        self._backend.dispatch_destination(
            destination,
            galaxy_map_settle,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )
        self._publish_data_refresh()

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._backend.dispatch_haul_loop(
            params=params,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )
        self._publish_data_refresh()

    def persist_trade_route_state(
        self,
        *,
        selected_trade_route: TradeRoute | None = None,
        running_trade_route: TradeRoute | None = None,
    ) -> None:
        if selected_trade_route is not None:
            self._saved_state.selected_trade_route = selected_trade_route
        if running_trade_route is not None:
            self._saved_state.running_trade_route = running_trade_route
        self._save_saved_state()

    def _publish_data_refresh(self) -> None:
        sink = self._protocol_event_sink
        if sink is not None:
            sink.publish_data_refresh()

    def handle_remote_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None:
        self.submit_input(raw_input, skip_delay=skip_delay)

    def cancel_active_routine(self, *, stop_mode: RoutineStopMode = "toggle") -> None:
        if stop_mode == "toggle":
            self._handle_interrupt("Remote Ctrl-C")
        else:
            self._handle_routine_stop_request("Remote Ctrl-C", stop_mode=stop_mode)
        sink = self._protocol_event_sink
        if sink is not None:
            sink.publish_data_refresh()

    def _is_client_local_remote_command(self, raw: str) -> bool:
        command_raw = raw[1:].lstrip() if raw.startswith("!") else raw
        parts = command_raw.split(None, 1)
        if not parts:
            return False
        return parts[0].lower() in _CLIENT_LOCAL_REMOTE_VERBS

    def _record_unknown_remote_command(self, raw: str) -> None:
        command_raw = raw[1:].lstrip() if raw.startswith("!") else raw
        parts = command_raw.split(None, 1)
        verb = parts[0].lower() if parts else ""
        rest = parts[1].strip() if len(parts) > 1 else ""
        self._log(f"[dim]Command: {escape(raw)}[/]")
        self._record_history_entry(
            CommandHistoryEntry(
                raw=raw,
                command=verb,
                params={"value": rest} if rest else {},
                timestamp=now_iso(),
            )
        )
        self._log(f"[dim]Unknown command: {escape(raw)}[/]")

    def _start_watcher_loop(self) -> None:
        if self._watcher_thread is not None:
            return
        self._watcher_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watcher_thread.start()

    def _watch_loop(self) -> None:
        watcher = JournalWatcher(self._journal_dir)
        refresh_interval_s = self._config.control_room.status_refresh_seconds
        last_market_check = 0.0
        while not self._watcher_stop.is_set():
            try:
                for ev in watcher.poll():
                    self._handle_event(ev)
                now = time.monotonic()
                if now - last_market_check > refresh_interval_s:
                    self._sync_status_state()
                    self._load_market_json()
                    self._refresh_haul_stats()
                    last_market_check = now
            except Exception:
                time.sleep(1.0)
            time.sleep(0.1)
