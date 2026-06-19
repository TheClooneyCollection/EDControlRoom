from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from edap.control_room import bootstrap as _bootstrap
from edap.control_room.app import ControlRoomApp
from edap.control_room.protocol import snapshot_from_app
from edap.control_room.protocol.snapshot import ControlRoomSnapshot
from edap.runtime import RuntimeContext
from edap.state import JournalWatcher
from edap.tts import NullSpeechBackend, TTSAnnouncer


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
        self.styles = _StylesStub()


class HeadlessControlRoomHost(ControlRoomApp):
    def __init__(self, ctx: RuntimeContext, *, market_filter: str | None = None) -> None:
        self._activity_widget = _ActivityWidgetStub()
        self._command_input_widget = _CommandInputWidgetStub()
        self._resume_help_widget = _StaticWidgetStub()
        self._resume_detail_widget = _StaticWidgetStub()
        self._resume_list_widget = _OptionListWidgetStub()
        self._resume_browser_widget = _ContainerWidgetStub()
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
        raise LookupError(selector)

    def set_focus(self, widget: object) -> None:  # type: ignore[override]
        return None

    def _refresh_status(self) -> None:  # type: ignore[override]
        return None

    def _refresh_market(self) -> None:  # type: ignore[override]
        return None

    def _refresh_haul_stats(self) -> None:  # type: ignore[override]
        return None

    def _refresh_activity_title(self) -> None:  # type: ignore[override]
        return None

    def call_from_thread(self, callback, *args, **kwargs):  # type: ignore[override]
        return callback(*args, **kwargs)

    def start(self) -> None:
        self._build_controls()
        self._load_saved_state()
        self._log_startup_modes()
        self._announce_startup_greeting()
        self._bootstrap_ship_state()
        self._load_market_json()
        self._start_watcher_loop()

    def close(self) -> None:
        self._watcher_stop.set()
        if self._watcher_thread is not None:
            self._watcher_thread.join(timeout=1.0)
        self._tts.close()

    def snapshot(self) -> ControlRoomSnapshot:
        return snapshot_from_app(
            self,
            session_id="local-server",
            client_role="active_operator",
            client_name="local-server",
            capability_names=["observer_http", "observer_websocket", "announcement_stream"],
            operator_mode="observer_only",
        )

    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None:
        resolved = raw_input
        if skip_delay is True and not raw_input.startswith("!"):
            resolved = f"!{raw_input}"
        self._backend.submit_input(resolved)
        self._publish_snapshot()

    def open_replay_browser(self) -> None:
        self._backend.open_replay_browser()
        self._publish_snapshot()

    def close_replay_browser(self) -> None:
        self._backend.close_replay_browser()
        self._publish_snapshot()

    def set_replay_filter(self, filter_text: str) -> None:
        self._backend.set_replay_filter(filter_text)
        self._publish_snapshot()

    def replay_history_entry(
        self,
        entry,
        *,
        edit: bool,
        skip_delay: bool = False,
    ) -> None:
        self._backend.replay_history_entry(entry, edit=edit, skip_delay=skip_delay)
        self._publish_snapshot()

    def toggle_replay_default_haul(self, entry) -> None:
        self._backend.toggle_replay_default_haul(entry)
        self._publish_snapshot()

    def _publish_snapshot(self) -> None:
        sink = self._protocol_event_sink
        if sink is not None:
            sink.publish_snapshot(self.snapshot())

    def handle_remote_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None:
        self.submit_input(raw_input, skip_delay=skip_delay)

    def cancel_active_routine(self) -> None:
        self._cancel_active_routine("Remote Ctrl-C")
        sink = self._protocol_event_sink
        if sink is not None:
            sink.publish_snapshot(self.snapshot())

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
                    self._sync_status_snapshot()
                    self._load_market_json()
                    self._refresh_haul_stats()
                    last_market_check = now
            except Exception:
                time.sleep(1.0)
            time.sleep(0.1)
