from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeAlias

from rich.markup import escape

from edap.control_room import history as _history
from edap.control_room import prompts as _prompts
from edap.control_room import replay as _replay
from edap.control_room.protocol import (
    ActivityLogAppendedEvent,
    AnnouncementEvent,
    ControlRoomEventSink,
    ControlRoomSnapshot,
    SnapshotUpdatedEvent,
    snapshot_from_app,
)
from edap.control_room.protocol.snapshot import ActivityLogEntry
from edap.control_room_state import CommandHistoryEntry
from edap.inara.trade_routes import TradeRoute


ControlRoomBackendEvent: TypeAlias = (
    ActivityLogAppendedEvent | AnnouncementEvent | SnapshotUpdatedEvent
)
ControlRoomBackendEventHandler: TypeAlias = Callable[[ControlRoomBackendEvent], None]


class ControlRoomBackend(ControlRoomEventSink, Protocol):
    def current_snapshot(self) -> ControlRoomSnapshot: ...

    def subscribe_events(
        self,
        handler: ControlRoomBackendEventHandler,
    ) -> Callable[[], None]: ...

    def submit_input(self, raw: str) -> None: ...

    def interrupt_active_routine(self) -> None: ...

    def exit_detaches_remote_session(self) -> bool: ...

    def dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None: ...

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...

    def load_trade_route(
        self,
        route: TradeRoute,
        *,
        raw_command: str | None = None,
    ) -> None: ...

    def handle_haul_prompt(self, value: str) -> None: ...

    def handle_haul_confirm_prompt(self, value: str) -> None: ...

    def open_replay_browser(self) -> None: ...

    def close_replay_browser(self) -> None: ...

    def refresh_replay_browser(self) -> None: ...

    def set_replay_filter(self, filter_text: str) -> None: ...

    def move_replay_selection(self, offset: int) -> None: ...

    def replay_history_entry(
        self,
        entry: CommandHistoryEntry,
        *,
        edit: bool,
        skip_delay: bool = False,
    ) -> None: ...

    def toggle_replay_default_haul(self, entry: CommandHistoryEntry) -> None: ...


class LocalBackendHost(Protocol):
    _facade: Any
    _config: Any
    _prompt_state: Any
    _saved_state: Any
    _protocol_external_event_sink: ControlRoomEventSink | None
    _resume_entries: list[Any]
    _resume_open: bool
    _resume_filter: str
    _haul_params: dict[str, str]
    _haul_prompt_step: str
    _haul_confirm_buy_station: str
    _dest_prompt_destination: str
    _dest_prompt_settle_default: float | None
    _dest_prompt_raw_command: str
    _dest_prompt_skip_delay: bool
    _default_command_placeholder: str
    dependencies: Any

    def _log(self, msg: str) -> None: ...
    def _save_saved_state(self) -> None: ...
    def _activity_auto_follow_paused(self) -> bool: ...
    def _handle_interrupt(self, source: str) -> None: ...
    def _dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None: ...
    def _dispatch_haul_loop(
        self,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def _dispatch_dest(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def _start_haul_prompt(
        self,
        *,
        commodity: str,
        prompt_for_commodity: bool,
        seed: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def _start_dest_prompt(
        self,
        destination: str,
        *,
        settle_default: float | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...

    def _parse_optional_nonnegative_float(
        self,
        raw: str,
        *,
        default: float,
        label: str,
    ) -> float | None: ...

    def set_focus(self, widget: object) -> None: ...
    def query_one(self, selector: str, widget_type: object | None = None) -> object: ...


class LocalControlRoomBackend(ControlRoomEventSink):
    def __init__(self, host: LocalBackendHost) -> None:
        self._host = host
        self._event_handlers: list[ControlRoomBackendEventHandler] = []

    def current_snapshot(self) -> ControlRoomSnapshot:
        return snapshot_from_app(self._host)

    def subscribe_events(
        self,
        handler: ControlRoomBackendEventHandler,
    ) -> Callable[[], None]:
        self._event_handlers.append(handler)

        def unsubscribe() -> None:
            try:
                self._event_handlers.remove(handler)
            except ValueError:
                return

        return unsubscribe

    def submit_input(self, raw: str) -> None:
        if self._host._haul_prompt_step:
            self.handle_haul_prompt(raw)
            return
        if self._host._haul_confirm_buy_station:
            self.handle_haul_confirm_prompt(raw)
            return
        if self._host._dest_prompt_destination:
            dispatch = _prompts.resolve_destination_prompt_submission(
                self._host._prompt_state,
                raw,
                parse_optional_nonnegative_float=lambda value, default, label: (
                    self._host._parse_optional_nonnegative_float(
                        value,
                        default=default,
                        label=label,
                    )
                ),
            )
            if dispatch is None:
                return
            command_input = self._host.query_one("#cmd")
            command_input.placeholder = self._host._default_command_placeholder
            self.dispatch_destination(
                dispatch.destination,
                dispatch.galaxy_map_settle,
                skip_delay=dispatch.skip_delay,
                raw_command=dispatch.raw_command,
            )
            return
        _prompts.clear_command_input_prefill(self._host._prompt_state)
        self.dispatch_command(raw)

    def interrupt_active_routine(self) -> None:
        self._host.dependencies.execution.cancel_active_routine()
        self.publish_snapshot(self.current_snapshot())

    def exit_detaches_remote_session(self) -> bool:
        return False

    def dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        self._host.dependencies.execution.submit_command(raw, skip_delay=skip_delay)

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._host.dependencies.execution.dispatch_destination(
            destination,
            galaxy_map_settle,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._host.dependencies.execution.dispatch_haul_loop(
            params=params,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )

    def load_trade_route(
        self,
        route: TradeRoute,
        *,
        raw_command: str | None = None,
    ) -> None:
        self._host.dependencies.execution.load_trade_route(
            route,
            raw_command=raw_command,
        )

    def handle_haul_prompt(self, value: str) -> None:
        self._host.dependencies.execution.handle_haul_prompt(value)

    def handle_haul_confirm_prompt(self, value: str) -> None:
        self._host.dependencies.execution.handle_haul_confirm_prompt(value)

    def open_replay_browser(self) -> None:
        _replay.show_resume_picker(self._host)

    def close_replay_browser(self) -> None:
        _replay.close_resume_picker(self._host)

    def refresh_replay_browser(self) -> None:
        _replay.refresh_resume_picker(self._host)

    def set_replay_filter(self, filter_text: str) -> None:
        self._host._resume_filter = filter_text
        self.refresh_replay_browser()

    def move_replay_selection(self, offset: int) -> None:
        _replay.move_resume_selection(self._host, offset)

    def replay_history_entry(
        self,
        entry: CommandHistoryEntry,
        *,
        edit: bool,
        skip_delay: bool = False,
    ) -> None:
        _replay.replay_history_entry(
            self._host,
            entry,
            edit=edit,
            skip_delay=skip_delay,
        )

    def toggle_replay_default_haul(self, entry: CommandHistoryEntry) -> None:
        if entry.command != "haul" or _history.is_haul_search_entry(entry):
            self._host._log("[dim]Only two-station haul loop entries can be saved as the default.[/]")
            return
        if _replay.default_haul_matches(self._host, entry):
            self._host._saved_state.default_haul = {}
            self._host._log("[dim]Cleared saved default haul.[/]")
        else:
            self._host._saved_state.default_haul = {
                str(key): str(value) for key, value in entry.params.items()
            }
            cargo = self._host._saved_state.default_haul.get("station_1_buying", "haul")
            self._host._log(f"[dim]Saved default haul from history: {escape(cargo)}[/]")
        self._host._save_saved_state()
        self.refresh_replay_browser()

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        event = ActivityLogAppendedEvent(entry=entry)
        self._emit(event)
        external_sink = self._host._protocol_external_event_sink
        if external_sink is not None:
            external_sink.publish_activity_log(entry)

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        self._emit(event)
        external_sink = self._host._protocol_external_event_sink
        if external_sink is not None:
            external_sink.publish_announcement(event)

    def publish_snapshot(self, snapshot: ControlRoomSnapshot) -> None:
        self._emit(SnapshotUpdatedEvent(snapshot=snapshot))
        external_sink = self._host._protocol_external_event_sink
        if external_sink is not None:
            external_sink.publish_snapshot(snapshot)

    def _emit(self, event: ControlRoomBackendEvent) -> None:
        for handler in list(self._event_handlers):
            handler(event)
