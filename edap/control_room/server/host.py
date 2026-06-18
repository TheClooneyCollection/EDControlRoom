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


class _ActivityWidgetStub:
    def __init__(self) -> None:
        self.auto_scroll = True
        self.border_title = "ACTIVITY"
        self.writes: list[object] = []

    @property
    def auto_follow_paused(self) -> bool:
        return not self.auto_scroll

    def write(self, content: object, **kwargs: object) -> None:
        self.writes.append((content, kwargs))


class HeadlessControlRoomHost(ControlRoomApp):
    def __init__(self, ctx: RuntimeContext, *, market_filter: str | None = None) -> None:
        super().__init__(ctx, market_filter=market_filter)
        self._activity_widget = _ActivityWidgetStub()
        self._watcher_stop = threading.Event()
        self._watcher_thread: threading.Thread | None = None

    def query_one(self, selector: str, widget_type=None):  # type: ignore[override]
        if selector == "#activity":
            return self._activity_widget
        raise LookupError(selector)

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
