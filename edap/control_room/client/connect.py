from __future__ import annotations

import socket

from textual.widgets import Input

from edap.control_room.app import ActivityLog, ControlRoomApp, _ALL_ROUTINE_ACTIONS, _build_log_text
from edap.control_room import commands as _commands
from edap.control_room import prompts as _prompts
from edap.control_room.backend import ControlRoomBackendEvent
from edap.control_room.client.backend import RemoteObserverBackend, fetch_remote_observer_snapshot
from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.models import PromptState, TradeRoutePickerState, TradeRoutesData
from edap.control_room.protocol import (
    ActivityLogAppendedEvent,
    AnnouncementEvent,
    SnapshotUpdatedEvent,
    build_remote_observer_websocket_connect_info,
)
from edap.runtime import build_runtime_context, load_config_with_fallback
from edap.tts import parse_announcement_id
from edap.control_room.routines_haul import (
    _set_trade_routes_error,
    _set_trade_routes_loaded,
    _set_trade_routes_loading,
)
from edap.inara.trade_routes import search_trade_routes


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
        self._local_search_prompt_state: PromptState | None = None

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
            activity.write(_build_log_text(event.entry.message_text))
            self._refresh_activity_title()
            return
        if isinstance(event, AnnouncementEvent):
            self._play_local_announcement(event)

    def _apply_remote_snapshot(self, *, replace_activity: bool) -> None:
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

    def _apply_view_snapshot_state(self) -> None:
        super()._apply_view_snapshot_state()
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
        if self._local_search_prompt_state is not None:
            self._prompt_state = PromptState(
                haul_params=dict(self._local_search_prompt_state.haul_params),
                haul_search_params=dict(self._local_search_prompt_state.haul_search_params),
                haul_prompt_defaults=dict(self._local_search_prompt_state.haul_prompt_defaults),
                haul_search_prompt_defaults=dict(
                    self._local_search_prompt_state.haul_search_prompt_defaults
                ),
                haul_prompt_step=self._local_search_prompt_state.haul_prompt_step,
                haul_prompt_mode=self._local_search_prompt_state.haul_prompt_mode,
                haul_confirm_buy_station=self._local_search_prompt_state.haul_confirm_buy_station,
                haul_prompt_raw_command=self._local_search_prompt_state.haul_prompt_raw_command,
                haul_prompt_skip_delay=self._local_search_prompt_state.haul_prompt_skip_delay,
                dest_prompt_destination=self._local_search_prompt_state.dest_prompt_destination,
                dest_prompt_settle_default=self._local_search_prompt_state.dest_prompt_settle_default,
                dest_prompt_raw_command=self._local_search_prompt_state.dest_prompt_raw_command,
                dest_prompt_skip_delay=self._local_search_prompt_state.dest_prompt_skip_delay,
                command_input_prefill_active=self._local_search_prompt_state.command_input_prefill_active,
                command_input_placeholder=self._local_search_prompt_state.command_input_placeholder,
                command_input_value=self._local_search_prompt_state.command_input_value,
            )
        self._refresh_trade_routes()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value
        event.input.value = ""

        if self._exit_prompt_active:
            self._handle_exit_prompt_input(raw)
            return

        if self._local_search_prompt_state is not None and self._haul_prompt_step:
            self._handle_local_haul_search_prompt(raw)
            return

        if self._haul_prompt_step or self._haul_confirm_buy_station or self._dest_prompt_destination:
            self._backend.submit_input(raw)
            return

        raw = raw.strip()
        if not raw:
            return

        if self._try_handle_local_haul_search_command(raw):
            return

        if raw.lower() in {"replay", "history"}:
            self._suppress_replay_enter_until = self._time_fn() + 0.1
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
        self._local_search_prompt_state = None

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
        self._backend.load_trade_route(
            route,
            raw_command=f"haul route {route.from_station} -> {route.to_station}",
        )

    def _handle_local_haul_search_prompt(self, value: str) -> None:
        _prompts.handle_haul_prompt(
            self,
            value,
            default_placeholder=self._default_command_placeholder,
        )
        if self._haul_prompt_step:
            self._capture_local_search_prompt_state()

    def _try_handle_local_haul_search_command(self, raw: str) -> bool:
        command_raw = raw[1:].lstrip() if raw.startswith("!") else raw
        lowered = command_raw.lower()
        if lowered == "haul search" or lowered.startswith("haul search "):
            _commands.dispatch(self, raw)
            if self._prompt_state.haul_prompt_mode == "search" and self._haul_prompt_step:
                self._capture_local_search_prompt_state()
            return True
        return False

    def _build_local_query_url(self, system_name: str, query_params: dict[str, str]) -> str:
        from edap.inara.trade_routes import build_trade_routes_url

        return build_trade_routes_url(system_name, query_params=query_params)

    def _capture_local_search_prompt_state(self) -> None:
        self._local_search_prompt_state = PromptState(
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
            command_input_value=self._prompt_state.command_input_value,
        )

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

    def _apply_local_trade_routes_loading(self, *, system_name: str, query_url: str) -> None:
        _set_trade_routes_loading(self, system_name=system_name, query_url=query_url)
        self._capture_local_trade_route_state()

    def _apply_local_trade_routes_loaded(self, result) -> None:
        _set_trade_routes_loaded(self, result)
        self._capture_local_trade_route_state()

    def _apply_local_trade_routes_error(
        self,
        *,
        system_name: str,
        query_url: str,
        message: str,
    ) -> None:
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

    def _refresh_remote_command_input(self) -> None:
        command_input = self.query_one("#cmd", Input)
        is_active_operator = self._view_snapshot.session.client_role == "active_operator"
        command_input.disabled = not is_active_operator
        if not is_active_operator:
            command_input.placeholder = "observer mode - read only"
            return
        if self._prompt_state.command_input_prefill_active:
            command_input.placeholder = self._prompt_state.command_input_placeholder
            command_input.value = self._prompt_state.command_input_value
            command_input.cursor_position = len(command_input.value)
            return
        command_input.placeholder = self._default_command_placeholder


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
