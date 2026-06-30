from __future__ import annotations

from datetime import datetime
import socket

from rich.markup import escape
from textual.widgets import Input

from edap.control_room.app import ActivityLog, ControlRoomApp, _ALL_ROUTINE_ACTIONS, _build_log_text
from edap.control_room import commands as _commands
from edap.control_room import prompts as _prompts
from edap.control_room import replay as _replay
from edap.control_room.backend import ControlRoomBackendEvent
from edap.control_room.client.backend import RemoteObserverBackend, fetch_remote_observer_snapshot
from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.history import now_iso
from edap.control_room.models import PromptState, TradeRoutePickerState, TradeRoutesData
from edap.control_room.protocol import (
    ActivityLogAppendedEvent,
    AnnouncementEvent,
    SnapshotUpdatedEvent,
    build_activity_log_entry,
    build_remote_observer_websocket_connect_info,
)
from edap.runtime import build_runtime_context, load_config_with_fallback
from edap.tts import parse_announcement_id
from edap.control_room.routines_haul import (
    _set_trade_routes_error,
    _set_trade_routes_loaded,
    _set_trade_routes_loading,
)
from edap.control_room_state import CommandHistoryEntry
from edap.inara.trade_routes import search_trade_routes


def _activity_log_entry_sort_key(entry: ActivityLogEntry) -> tuple[datetime, str]:
    return (
        datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00")),
        entry.entry_id,
    )


class ObserverControlRoomApp(ControlRoomApp):
    def __init__(
        self,
        ctx,
        *,
        backend: RemoteObserverBackend,
        server_target: ObserverServerTarget,
        client_name: str,
    ) -> None:
        super().__init__(ctx, backend=backend)
        self._observer_backend = backend
        self._server_target = server_target
        self._client_name = client_name
        self._local_trade_routes = TradeRoutesData()
        self._local_trade_route_picker = TradeRoutePickerState()
        self._local_prompt_state: PromptState | None = None
        self._local_command_input_value = ""
        self._local_command_input_cursor_position = 0
        self._local_prompt_prefill_signature = (False, "", "")
        self._local_activity_log: list[ActivityLogEntry] = []
        self._local_replay_filter = ""
        self._local_replay_open = False
        self._local_selected_resume_history_entry: CommandHistoryEntry | None = None

    def _check_routine_ready(self) -> bool:
        if self._view_snapshot.session.client_role != "active_operator":
            self._log("[yellow]Observer session is read-only.[/]")
            return False
        if self._routine_active:
            self._log("[yellow]A routine is already running — wait for it to finish[/]")
            return False
        return True

    def on_mount(self) -> None:
        self._configure_screen_widgets()
        self.title = (
            f"ED Control Room Observer - {self._server_target.host}:{self._server_target.port}"
        )
        self._backend_event_unsubscribe = self._backend.subscribe_events(self._handle_backend_event)
        self._observer_backend.start()
        self._apply_remote_snapshot(replace_activity=True)
        self._observer_backend.request_snapshot()
        self._refresh_remote_command_input()

    def on_unmount(self) -> None:
        super().on_unmount()
        self._observer_backend.close()

    def _handle_backend_event(self, event: ControlRoomBackendEvent) -> None:
        self.call_from_thread(self._apply_backend_event, event)

    def _apply_backend_event(self, event: ControlRoomBackendEvent) -> None:
        if isinstance(event, SnapshotUpdatedEvent):
            self._view_snapshot = event.snapshot
            self._apply_remote_snapshot(replace_activity=True)
            return
        if isinstance(event, ActivityLogAppendedEvent):
            self._protocol_activity_log.append(event.entry)
            if len(self._protocol_activity_log) > self._activity_log_max_lines:
                self._protocol_activity_log = self._protocol_activity_log[-self._activity_log_max_lines :]
            activity = self.query_one("#activity", ActivityLog)
            activity.write(_build_log_text(event.entry.message_text, timestamp=event.entry.timestamp))
            self._refresh_activity_title()
            return
        if isinstance(event, AnnouncementEvent):
            self._play_local_announcement(event)

    def _replace_activity_log(self, entries: list[ActivityLogEntry]) -> None:
        merged_entries = list(entries) + list(self._local_activity_log)
        merged_entries.sort(key=_activity_log_entry_sort_key)
        if len(merged_entries) > self._activity_log_max_lines:
            merged_entries = merged_entries[-self._activity_log_max_lines :]
        super()._replace_activity_log(merged_entries)

    def _log(self, msg: str) -> None:
        activity = self.query_one("#activity", ActivityLog)
        entry = self._build_local_activity_entry(msg)
        activity.write(_build_log_text(entry.message_text, timestamp=entry.timestamp))
        self._local_activity_log.append(entry)
        if len(self._local_activity_log) > self._activity_log_max_lines:
            self._local_activity_log = self._local_activity_log[-self._activity_log_max_lines :]
        self._protocol_activity_log.append(entry)
        if len(self._protocol_activity_log) > self._activity_log_max_lines:
            self._protocol_activity_log = self._protocol_activity_log[-self._activity_log_max_lines :]
        self._refresh_activity_title()

    def _build_local_activity_entry(self, msg: str) -> ActivityLogEntry:
        return build_activity_log_entry(msg)

    def _apply_remote_snapshot(self, *, replace_activity: bool) -> None:
        self._debug_log(
            "observer_remote_snapshot_apply_start",
            replace_activity=replace_activity,
            remote_trade_route_count=len(self._view_snapshot.trade_routes.routes),
            remote_trade_routes_loading=self._view_snapshot.trade_routes.loading,
            local_trade_route_count=len(self._local_trade_routes.routes),
            local_picker_open=self._local_trade_route_picker.open,
            local_selected_trade_route_index=self._local_trade_route_picker.selected_route_index,
            local_prompt_step=self._local_prompt_state.haul_prompt_step
            if self._local_prompt_state is not None
            else "",
        )
        self._sync_view_snapshot()
        self._tts.set_commander_name(self._view_snapshot.ship.commander_name)
        if replace_activity:
            self._replace_activity_log(self._view_snapshot.activity_log)
        self._refresh_status()
        self._refresh_haul_stats()
        self._refresh_market()
        self._refresh_trade_routes()
        self._update_resume_detail()
        self._refresh_remote_command_input()
        self._debug_log(
            "observer_remote_snapshot_apply_done",
            visible_trade_route_count=len(self._trade_routes.routes),
            visible_picker_open=self._trade_route_picker_open,
            visible_selected_trade_route_index=self._selected_trade_route_index,
            visible_prompt_step=self._prompt_state.haul_prompt_step,
        )

    def _publish_protocol_snapshot(self) -> None:
        # Observer-local haul search state should not be fed back through the
        # remote snapshot backend; it is rendered locally and the remote side
        # remains authoritative only for server-originated snapshots.
        return None

    def _apply_view_snapshot_state(self) -> None:
        super()._apply_view_snapshot_state()
        self._debug_log(
            "observer_apply_view_snapshot_state_after_super",
            remote_trade_route_count=len(self._trade_routes.routes),
            remote_picker_open=self._trade_route_picker_open,
            remote_selected_trade_route_index=self._selected_trade_route_index,
        )
        self._trade_routes = TradeRoutesData(
            system_name=self._local_trade_routes.system_name,
            query_url=self._local_trade_routes.query_url,
            searched_at=self._local_trade_routes.searched_at,
            loading=self._local_trade_routes.loading,
            error=self._local_trade_routes.error,
            routes=list(self._local_trade_routes.routes),
        )
        self._trade_route_picker_open = self._local_trade_route_picker.open
        self._selected_trade_route_index = self._local_trade_route_picker.selected_route_index
        self._presented_trade_route_query_url = self._local_trade_route_picker.presented_query_url
        self._presented_trade_route_searched_at = self._local_trade_route_picker.presented_searched_at
        if self._local_prompt_state is not None:
            self._prompt_state = PromptState(
                haul_params=dict(self._local_prompt_state.haul_params),
                haul_search_params=dict(self._local_prompt_state.haul_search_params),
                haul_prompt_defaults=dict(self._local_prompt_state.haul_prompt_defaults),
                haul_search_prompt_defaults=dict(
                    self._local_prompt_state.haul_search_prompt_defaults
                ),
                haul_prompt_step=self._local_prompt_state.haul_prompt_step,
                haul_prompt_mode=self._local_prompt_state.haul_prompt_mode,
                haul_confirm_buy_station=self._local_prompt_state.haul_confirm_buy_station,
                haul_prompt_raw_command=self._local_prompt_state.haul_prompt_raw_command,
                haul_prompt_skip_delay=self._local_prompt_state.haul_prompt_skip_delay,
                dest_prompt_destination=self._local_prompt_state.dest_prompt_destination,
                dest_prompt_settle_default=self._local_prompt_state.dest_prompt_settle_default,
                dest_prompt_raw_command=self._local_prompt_state.dest_prompt_raw_command,
                dest_prompt_skip_delay=self._local_prompt_state.dest_prompt_skip_delay,
                command_input_prefill_active=self._local_prompt_state.command_input_prefill_active,
                command_input_placeholder=self._local_prompt_state.command_input_placeholder,
                command_input_value=self._local_prompt_state.command_input_value,
            )
        else:
            self._prompt_state = PromptState()
        self._resume_filter = self._local_replay_filter
        self._resume_open = self._local_replay_open
        self._resume_entries = self._filtered_resume_entries()
        self._selected_resume_history_entry = self._resolve_local_selected_resume_entry()
        self._replay_state.filter_text = self._local_replay_filter
        self._replay_state.open = self._local_replay_open
        self._apply_replay_browser_visibility()
        self._debug_log(
            "observer_apply_view_snapshot_state_local_override",
            local_trade_route_count=len(self._trade_routes.routes),
            local_trade_routes_loading=self._trade_routes.loading,
            local_picker_open=self._trade_route_picker_open,
            local_selected_trade_route_index=self._selected_trade_route_index,
            local_prompt_step=self._prompt_state.haul_prompt_step,
            local_replay_open=self._resume_open,
            local_replay_filter=self._resume_filter,
        )
        self._refresh_trade_routes()
        if self._resume_open:
            self._refresh_resume_help()
            self._update_resume_detail()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value
        event.input.value = ""
        self._local_command_input_value = ""
        self._local_command_input_cursor_position = 0
        self._debug_log(
            "observer_input_submitted",
            raw=raw,
            has_local_prompt=self._local_prompt_state is not None,
            haul_prompt_step=self._haul_prompt_step,
            haul_confirm_buy_station=self._haul_confirm_buy_station,
            dest_prompt_destination=self._dest_prompt_destination,
        )

        if self._exit_prompt_active:
            self._debug_log("observer_input_branch_exit_prompt")
            self._handle_exit_prompt_input(raw)
            return

        if self._local_prompt_state is not None and self._haul_prompt_step:
            self._debug_log(
                "observer_input_branch_local_prompt",
                raw=raw,
                haul_prompt_step=self._haul_prompt_step,
            )
            self._handle_local_prompt(raw)
            return

        if self._haul_prompt_step or self._haul_confirm_buy_station or self._dest_prompt_destination:
            self._debug_log(
                "observer_input_branch_local_prompt_resume",
                raw=raw,
                haul_prompt_step=self._haul_prompt_step,
                haul_confirm_buy_station=self._haul_confirm_buy_station,
                dest_prompt_destination=self._dest_prompt_destination,
            )
            self._handle_local_prompt(raw)
            return

        raw = raw.strip()
        if not raw:
            self._debug_log("observer_input_branch_blank_after_strip")
            return

        if self._try_handle_local_client_command(raw):
            self._debug_log("observer_input_branch_local_client_command_handled", raw=raw)
            return

        if raw.lower() in {"replay", "history"}:
            self._suppress_replay_enter_until = self._time_fn() + 0.1
            self._debug_log("observer_input_branch_replay_history_submit", raw=raw)
        else:
            self._debug_log("observer_input_branch_remote_plain_submit", raw=raw)
        self._backend.submit_input(raw)

    def _dispatch_haul_search(
        self,
        *,
        system_name: str,
        query_params: dict[str, str],
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        query_url = self._build_local_query_url(system_name, query_params)
        self._clear_local_prompt_state()
        history_params = {
            "mode": "search",
            "near_system": system_name,
            **{str(key): str(value) for key, value in query_params.items()},
        }
        self._record_history_entry(
            CommandHistoryEntry(
                raw=raw_command or f"{'!' if skip_delay else ''}haul search {system_name}".strip(),
                command="haul",
                params=history_params,
                timestamp=now_iso(),
            )
        )

        def on_start() -> None:
            self._log(f"Searching Inara trade routes for [cyan]{system_name}[/]...")
            self._apply_local_trade_routes_loading(
                system_name=system_name,
                query_url=query_url,
            )

        def run_search() -> None:
            try:
                result = search_trade_routes(
                    system_name,
                    query_params=query_params,
                    debug_hook=getattr(self, "_debug_log", None),
                )
            except Exception as exc:
                self.call_from_thread(
                    self._apply_local_trade_routes_error,
                    system_name=system_name,
                    query_url=query_url,
                    message=str(exc),
                )
                self.call_from_thread(
                    self._log,
                    f"[red]Failed to load Inara routes for {system_name}: {exc}[/]",
                )
                return None
            self.call_from_thread(self._apply_local_trade_routes_loaded, result)
            self.call_from_thread(
                self._log,
                f"[green]Loaded {len(result.routes)} Inara route(s) for [cyan]{system_name}[/].[/]",
            )
            return None

        self._start_delayed_routine(
            description=f"haul search {system_name}",
            start_message="",
            skip_delay=skip_delay,
            fn=run_search,
            active_routine_name="haul_search",
            on_start=on_start,
        )

    def _load_selected_trade_route(self) -> None:
        route = self._selected_trade_route()
        if route is None:
            return
        self._close_trade_route_picker()
        _commands.dispatch(self, f"haul route {route.index}")
        self._sync_local_prompt_state()

    def _close_trade_route_picker(self) -> None:
        self._debug_log(
            "observer_close_trade_route_picker_start",
            local_picker_open=self._local_trade_route_picker.open,
            local_selected_trade_route_index=self._local_trade_route_picker.selected_route_index,
            visible_picker_open=self._trade_route_picker_open,
            visible_selected_trade_route_index=self._selected_trade_route_index,
        )
        self._trade_route_picker_open = False
        self._local_trade_route_picker = TradeRoutePickerState(
            open=False,
            selected_route_index=self._selected_trade_route_index,
            presented_query_url=self._presented_trade_route_query_url,
            presented_searched_at=self._presented_trade_route_searched_at,
        )
        self._refresh_trade_route_picker()
        self._debug_log(
            "observer_close_trade_route_picker_done",
            local_picker_open=self._local_trade_route_picker.open,
            local_selected_trade_route_index=self._local_trade_route_picker.selected_route_index,
            visible_picker_open=self._trade_route_picker_open,
            visible_selected_trade_route_index=self._selected_trade_route_index,
        )
        try:
            self.set_focus(self.query_one("#cmd", Input))
        except Exception:
            return

    def _handle_local_prompt(self, value: str) -> None:
        self._debug_log(
            "observer_handle_local_prompt_start",
            value=value,
            haul_prompt_step=self._haul_prompt_step,
            haul_confirm_buy_station=self._haul_confirm_buy_station,
            dest_prompt_destination=self._dest_prompt_destination,
        )
        if self._haul_prompt_step:
            _prompts.handle_haul_prompt(
                self,
                value,
                default_placeholder=self._default_command_placeholder,
            )
        elif self._haul_confirm_buy_station:
            _prompts.handle_haul_confirm_prompt(
                self,
                value,
                default_placeholder=self._default_command_placeholder,
            )
        elif self._dest_prompt_destination:
            dispatch = _prompts.resolve_destination_prompt_submission(
                self._prompt_state,
                value,
                parse_optional_nonnegative_float=lambda raw_value, default, label: (
                    self._parse_optional_nonnegative_float(
                        raw_value,
                        default=default,
                        label=label,
                    )
                ),
            )
            if dispatch is not None:
                self._debug_log(
                    "observer_dest_prompt_dispatch_resolved",
                    destination=dispatch.destination,
                    galaxy_map_settle=dispatch.galaxy_map_settle,
                    skip_delay=dispatch.skip_delay,
                    raw_command=dispatch.raw_command,
                )
                command_input = self.query_one("#cmd", Input)
                command_input.placeholder = self._default_command_placeholder
                command_input.value = ""
                command_input.cursor_position = 0
                self._dispatch_dest(
                    dispatch.destination,
                    dispatch.galaxy_map_settle,
                    skip_delay=dispatch.skip_delay,
                    raw_command=dispatch.raw_command,
                )
        self._sync_local_prompt_state()
        if self._local_prompt_state is not None and self._haul_prompt_step:
            self._debug_log(
                "observer_handle_local_prompt_continue",
                next_haul_prompt_step=self._haul_prompt_step,
                command_input_prefill_active=self._prompt_state.command_input_prefill_active,
            )
            return
        self._debug_log("observer_handle_local_prompt_done")

    def _try_handle_local_client_command(self, raw: str) -> bool:
        command_raw = raw[1:].lstrip() if raw.startswith("!") else raw
        lowered = command_raw.lower()
        self._debug_log(
            "observer_try_local_client_command",
            raw=raw,
            command_raw=command_raw,
            lowered=lowered,
        )
        parts = lowered.split(None, 1)
        verb = parts[0] if parts else ""
        if verb in {
            "haul",
            "dest",
            "set_dest",
            "home",
            "replay",
            "history",
            "commands",
            "help",
            "?",
            "market",
        }:
            self._sync_local_ship_context_from_snapshot()
            _commands.dispatch(self, raw)
            self._sync_local_prompt_state()
            self._sync_local_replay_state()
            return True
        self._debug_log("observer_try_local_client_command_not_matched", raw=raw)
        return False

    def _observer_ship_system(self) -> str:
        snapshot_system = getattr(self._view_snapshot.ship, "system_name", "") or ""
        return snapshot_system.strip() or (self._ship.system or "").strip()

    def _sync_local_ship_context_from_snapshot(self) -> None:
        ship = self._view_snapshot.ship
        self._ship.system = ship.system_name
        self._ship.station = ship.station_name
        self._ship.cargo_capacity = ship.cargo_capacity

    def _build_local_query_url(self, system_name: str, query_params: dict[str, str]) -> str:
        from edap.inara.trade_routes import build_trade_routes_url

        return build_trade_routes_url(system_name, query_params=query_params)

    def _capture_local_prompt_state(self) -> None:
        command_input_value = self._prompt_state.command_input_value
        if self._prompt_state.command_input_prefill_active:
            try:
                command_input = self.query_one("#cmd", Input)
            except Exception:
                command_input = None
            if command_input is not None:
                self._capture_local_command_input_widget_state(command_input)
                command_input_value = command_input.value
        self._local_prompt_state = PromptState(
            haul_params=dict(self._prompt_state.haul_params),
            haul_search_params=dict(self._prompt_state.haul_search_params),
            haul_prompt_defaults=dict(self._prompt_state.haul_prompt_defaults),
            haul_search_prompt_defaults=dict(self._prompt_state.haul_search_prompt_defaults),
            haul_prompt_step=self._prompt_state.haul_prompt_step,
            haul_prompt_mode=self._prompt_state.haul_prompt_mode,
            haul_confirm_buy_station=self._prompt_state.haul_confirm_buy_station,
            haul_prompt_raw_command=self._prompt_state.haul_prompt_raw_command,
            haul_prompt_skip_delay=self._prompt_state.haul_prompt_skip_delay,
            dest_prompt_destination=self._prompt_state.dest_prompt_destination,
            dest_prompt_settle_default=self._prompt_state.dest_prompt_settle_default,
            dest_prompt_raw_command=self._prompt_state.dest_prompt_raw_command,
            dest_prompt_skip_delay=self._prompt_state.dest_prompt_skip_delay,
            command_input_prefill_active=self._prompt_state.command_input_prefill_active,
            command_input_placeholder=self._prompt_state.command_input_placeholder,
            command_input_value=command_input_value,
        )

    def _clear_local_prompt_state(self) -> None:
        self._local_prompt_state = None
        self._local_prompt_prefill_signature = (False, "", "")
        _prompts.clear_haul_prompt(self._prompt_state)
        _prompts.clear_destination_prompt(self._prompt_state)
        try:
            command_input = self.query_one("#cmd", Input)
        except Exception:
            return
        command_input.placeholder = self._default_command_placeholder
        command_input.value = ""
        command_input.cursor_position = 0
        self._local_command_input_value = ""
        self._local_command_input_cursor_position = 0

    def _sync_local_prompt_state(self) -> None:
        if (
            self._prompt_state.haul_prompt_step
            or self._prompt_state.haul_confirm_buy_station
            or self._prompt_state.dest_prompt_destination
            or self._prompt_state.command_input_prefill_active
        ):
            self._capture_local_prompt_state()
            return
        self._clear_local_prompt_state()

    def _sync_local_replay_state(self) -> None:
        self._local_replay_filter = self._resume_filter
        self._local_replay_open = self._resume_open
        self._local_selected_resume_history_entry = self._selected_resume_history_entry

    def _resolve_local_selected_resume_entry(self) -> CommandHistoryEntry | None:
        if not self._resume_entries:
            return None
        selected = self._local_selected_resume_history_entry
        if selected is None:
            return self._resume_entries[0].entry
        for replay_entry in self._resume_entries:
            if replay_entry.entry == selected:
                return replay_entry.entry
        return self._resume_entries[0].entry

    def _show_resume_picker(self) -> None:
        _replay.show_resume_picker(self)
        self._sync_local_replay_state()

    def _refresh_resume_picker(self) -> None:
        _replay.refresh_resume_picker(self)
        self._sync_local_replay_state()

    def _close_resume_picker(self) -> None:
        _replay.close_resume_picker(self)
        self._sync_local_replay_state()

    def _resume_execute_selected(self) -> None:
        _replay.resume_execute_selected(self)
        self._sync_local_replay_state()
        self._sync_local_prompt_state()

    def _resume_execute_selected_immediate(self) -> None:
        _replay.resume_execute_selected_immediate(self)
        self._sync_local_replay_state()
        self._sync_local_prompt_state()

    def _resume_edit_selected(self) -> None:
        _replay.resume_edit_selected(self)
        self._sync_local_replay_state()
        self._sync_local_prompt_state()

    def _resume_toggle_default_selected(self) -> None:
        _replay.resume_toggle_default_selected(self)
        self._sync_local_replay_state()

    def _capture_local_trade_route_state(self) -> None:
        self._local_trade_routes = TradeRoutesData(
            system_name=self._trade_routes.system_name,
            query_url=self._trade_routes.query_url,
            searched_at=self._trade_routes.searched_at,
            loading=self._trade_routes.loading,
            error=self._trade_routes.error,
            routes=list(self._trade_routes.routes),
        )
        self._local_trade_route_picker = TradeRoutePickerState(
            open=self._trade_route_picker_open,
            selected_route_index=self._selected_trade_route_index,
            presented_query_url=self._presented_trade_route_query_url,
            presented_searched_at=self._presented_trade_route_searched_at,
        )
        self._debug_log(
            "observer_capture_local_trade_route_state",
            local_trade_route_count=len(self._local_trade_routes.routes),
            local_trade_routes_loading=self._local_trade_routes.loading,
            local_trade_routes_error=self._local_trade_routes.error,
            local_picker_open=self._local_trade_route_picker.open,
            local_selected_trade_route_index=self._local_trade_route_picker.selected_route_index,
            local_presented_query_url=self._local_trade_route_picker.presented_query_url,
            local_presented_searched_at=self._local_trade_route_picker.presented_searched_at,
        )

    def _apply_local_trade_routes_loading(self, *, system_name: str, query_url: str) -> None:
        self._debug_log(
            "observer_local_trade_routes_loading_start",
            system_name=system_name,
            query_url=query_url,
        )
        _set_trade_routes_loading(self, system_name=system_name, query_url=query_url)
        self._capture_local_trade_route_state()

    def _apply_local_trade_routes_loaded(self, result) -> None:
        self._debug_log(
            "observer_local_trade_routes_loaded_start",
            system_name=result.system_name,
            query_url=result.query_url,
            route_count=len(result.routes),
            first_route_index=result.routes[0].index if result.routes else None,
        )
        _set_trade_routes_loaded(self, result)
        self._capture_local_trade_route_state()

    def _apply_local_trade_routes_error(
        self,
        *,
        system_name: str,
        query_url: str,
        message: str,
    ) -> None:
        self._debug_log(
            "observer_local_trade_routes_error_start",
            system_name=system_name,
            query_url=query_url,
            message=message,
        )
        _set_trade_routes_error(
            self,
            system_name=system_name,
            query_url=query_url,
            message=message,
        )
        self._capture_local_trade_route_state()

    def _play_local_announcement(self, event: AnnouncementEvent) -> None:
        parsed_id = parse_announcement_id(event.announcement_id)
        if parsed_id is None:
            return
        self._tts.announce(parsed_id, **event.message_values)

    def on_input_changed(self, event: Input.Changed) -> None:
        if getattr(event.input, "id", None) not in {None, "cmd"}:
            return
        self._capture_local_command_input_widget_state(event.input)

    def _capture_local_command_input_widget_state(self, command_input: Input) -> None:
        self._local_command_input_value = command_input.value
        self._local_command_input_cursor_position = min(
            getattr(command_input, "cursor_position", len(command_input.value)),
            len(command_input.value),
        )
        if self._prompt_state.command_input_prefill_active:
            self._prompt_state.command_input_value = command_input.value
            if self._local_prompt_state is not None:
                self._local_prompt_state.command_input_value = command_input.value

    def _prompt_prefill_signature(self) -> tuple[object, ...]:
        if (
            self._prompt_state.haul_prompt_step
            or self._prompt_state.haul_confirm_buy_station
            or self._prompt_state.dest_prompt_destination
        ):
            return (
                self._prompt_state.command_input_prefill_active,
                self._prompt_state.command_input_placeholder,
                self._prompt_state.haul_prompt_step,
                self._prompt_state.haul_confirm_buy_station,
                self._prompt_state.dest_prompt_destination,
            )
        return (
            self._prompt_state.command_input_prefill_active,
            self._prompt_state.command_input_placeholder,
            self._prompt_state.command_input_value,
        )

    def _refresh_remote_command_input(self) -> None:
        command_input = self.query_one("#cmd", Input)
        if command_input.value == self._local_command_input_value:
            self._capture_local_command_input_widget_state(command_input)
        is_active_operator = self._view_snapshot.session.client_role == "active_operator"
        command_input.disabled = not is_active_operator
        if not is_active_operator:
            command_input.placeholder = "observer mode - read only"
            return
        prompt_prefill_signature = self._prompt_prefill_signature()
        if self._prompt_state.command_input_prefill_active:
            command_input.placeholder = self._prompt_state.command_input_placeholder
            if prompt_prefill_signature != self._local_prompt_prefill_signature:
                command_input.value = self._prompt_state.command_input_value
                command_input.cursor_position = len(command_input.value)
                self._local_command_input_value = command_input.value
                self._local_command_input_cursor_position = command_input.cursor_position
            elif command_input.value != self._local_command_input_value:
                command_input.value = self._local_command_input_value
                command_input.cursor_position = min(
                    self._local_command_input_cursor_position,
                    len(command_input.value),
                )
            self._local_prompt_prefill_signature = prompt_prefill_signature
            return
        self._local_prompt_prefill_signature = prompt_prefill_signature
        command_input.placeholder = self._default_command_placeholder
        if command_input.value != self._local_command_input_value:
            command_input.value = self._local_command_input_value
            command_input.cursor_position = min(
                self._local_command_input_cursor_position,
                len(command_input.value),
            )

    def on_key(self, event) -> None:
        if self._resume_open:
            if event.key != "enter":
                self._suppress_replay_enter_until = 0.0
            if event.key == "escape" or (event.key == "q" and not self._resume_filter):
                event.prevent_default()
                self._close_resume_picker()
            elif event.key == "up":
                event.prevent_default()
                _replay.move_resume_selection(self, -1)
                self._sync_local_replay_state()
            elif event.key == "down":
                event.prevent_default()
                _replay.move_resume_selection(self, 1)
                self._sync_local_replay_state()
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
        if self._exit_prompt_active and event.key == "enter":
            event.prevent_default()
            cmd_input = self.query_one("#cmd", Input)
            raw = cmd_input.value
            cmd_input.value = ""
            self._local_command_input_value = ""
            self._local_command_input_cursor_position = 0
            self._handle_exit_prompt_input(raw)
            return
        if (
            self._haul_prompt_step
            or self._haul_confirm_buy_station
            or self._dest_prompt_destination
        ) and event.key == "enter":
            event.prevent_default()
            cmd_input = self.query_one("#cmd", Input)
            raw = cmd_input.value
            cmd_input.value = ""
            self._local_command_input_value = ""
            self._local_command_input_cursor_position = 0
            self._handle_local_prompt(raw)
            return
        super().on_key(event)
        try:
            focused_input = self.query_one("#cmd", Input)
        except Exception:
            return
        self._capture_local_command_input_widget_state(focused_input)


def connect_observer_mode(
    *,
    config_path: str,
    target: str,
    access_token: str,
    client_name: str | None = None,
    claim_operator: bool = False,
) -> None:
    loaded = load_config_with_fallback(config_path)
    server_target = parse_observer_server_target(target)
    resolved_client_name = (client_name or socket.gethostname()).strip() or "observer-client"
    capabilities, snapshot = fetch_remote_observer_snapshot(
        server_target=server_target,
        access_token=access_token,
    )
    ctx = build_runtime_context(
        loaded.config,
        config_path=loaded.config_path,
        used_example_config_fallback=loaded.used_example_config_fallback,
        actions=_ALL_ROUTINE_ACTIONS,
    )
    backend = RemoteObserverBackend(
        server_target=server_target,
        access_token=access_token,
        client_name=resolved_client_name,
        initial_snapshot=snapshot,
        websocket_connect_info=build_remote_observer_websocket_connect_info(
            websocket_url=server_target.websocket_url,
            access_token=access_token,
            client_name=resolved_client_name,
            capabilities=capabilities,
            prefer_authorization_header=True,
        ),
    )
    app = ObserverControlRoomApp(
        ctx,
        backend=backend,
        server_target=server_target,
        client_name=resolved_client_name,
    )
    if claim_operator:
        backend.request_active_operator()
    app.run()
