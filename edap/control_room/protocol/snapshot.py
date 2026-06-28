from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ClientRole = Literal["active_operator", "observer"]


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str
    client_role: ClientRole


@dataclass(frozen=True)
class ConnectedClientSnapshot:
    session_id: str
    client_name: str
    client_role: ClientRole


@dataclass(frozen=True)
class ActiveOperatorSnapshot:
    session_id: str
    client_name: str


@dataclass(frozen=True)
class ShipSnapshot:
    commander_name: str | None
    ship_type: str | None
    system_name: str | None
    station_name: str | None
    status: str | None
    fuel_level: float | None
    fuel_capacity: float | None
    credits: int | None
    cargo_count: int
    cargo_capacity: int | None
    cargo_inventory: list[dict[str, Any]] = field(default_factory=list)
    target_name: str | None = None
    destination_system: str | None = None
    destination_body: str | None = None
    destination_name: str | None = None


@dataclass(frozen=True)
class MarketSnapshot:
    station_name: str
    system_name: str
    market_timestamp: str
    market_filter_text: str | None
    locked: bool
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class HaulSessionSnapshot:
    station_1_buying: str
    station_2_buying: str
    station_1: str
    station_2: str
    session_started_at: float | None
    session_elapsed_seconds: float
    session_active: bool
    active: bool
    clean_run_active: bool
    waiting_for_station_1_departure: bool
    resumed_mid_run: bool
    docked_back_at_station_1: bool
    current_run_started_at: float | None
    current_run_elapsed_seconds: float | None
    current_run_profit: int
    completed_runs: int
    accumulated_profit: int
    last_run_profit: int | None
    last_run_elapsed_seconds: float | None
    total_run_elapsed_seconds: float


@dataclass(frozen=True)
class UiStateSnapshot:
    routine_active: bool
    active_routine_name: str | None
    haul_stop_requested: bool
    verbose_controls: bool
    instant_mode: bool
    activity_auto_follow_paused: bool
    replay_browser_open: bool
    shutdown_requested: bool
    shutdown_finalized: bool


@dataclass(frozen=True)
class CommandHistoryEntrySnapshot:
    raw_command: str
    command_name: str
    arguments: dict[str, Any]
    timestamp: str


@dataclass(frozen=True)
class CommandHistorySnapshot:
    default_haul: dict[str, str] = field(default_factory=dict)
    history_entries: list[CommandHistoryEntrySnapshot] = field(default_factory=list)
    history_limit: int = 1
    draft_command: str = ""
    replay_filter_text: str = ""


@dataclass(frozen=True)
class PromptStateSnapshot:
    haul_parameters: dict[str, str] = field(default_factory=dict)
    haul_search_parameters: dict[str, str] = field(default_factory=dict)
    haul_prompt_defaults: dict[str, str] = field(default_factory=dict)
    haul_search_prompt_defaults: dict[str, str] = field(default_factory=dict)
    haul_prompt_step: str = ""
    haul_prompt_mode: str = ""
    haul_confirm_buy_station: str = ""
    haul_prompt_raw_command: str = ""
    haul_prompt_skip_delay: bool = False
    destination_prompt_destination: str = ""
    destination_prompt_settle_default: float | None = None
    destination_prompt_raw_command: str = ""
    destination_prompt_skip_delay: bool = False
    command_input_prefill_active: bool = False
    command_input_placeholder: str = ""
    command_input_value: str = ""


@dataclass(frozen=True)
class TradeRouteSnapshot:
    index: int
    from_station: str
    from_system: str
    to_station: str
    to_system: str
    source_buy_commodity: str | None = None
    target_buy_commodity: str | None = None
    distance_from_system: str | None = None
    route_distance: str | None = None
    profit_per_unit: str | None = None
    profit_per_trip: str | None = None
    profit_per_hour: str | None = None
    updated: str | None = None
    raw_text: str = ""
    url_links: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TradeRoutesSnapshot:
    system_name: str = ""
    query_url: str = ""
    searched_at: str = ""
    loading: bool = False
    error: str | None = None
    routes: list[TradeRouteSnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class ReplayEntrySnapshot:
    label: str
    detail: str
    history_entry: CommandHistoryEntrySnapshot


@dataclass(frozen=True)
class ReplayBrowserSnapshot:
    open: bool
    filter_text: str
    visible_entries: list[ReplayEntrySnapshot] = field(default_factory=list)
    selected_history_entry: CommandHistoryEntrySnapshot | None = None


@dataclass(frozen=True)
class ActivityLogEntry:
    entry_id: str
    timestamp: str
    message_text: str
    severity: str | None = None


@dataclass(frozen=True)
class ServerStatusSnapshot:
    server_name: str
    server_version: str
    runtime_platform: str
    journal_source_status: str
    bindings_source_status: str
    bindings_loaded: bool
    capability_names: list[str] = field(default_factory=list)
    operator_mode: str | None = None


@dataclass(frozen=True)
class ControlRoomSnapshot:
    session: SessionSnapshot
    connected_clients: list[ConnectedClientSnapshot]
    active_operator: ActiveOperatorSnapshot | None
    ship: ShipSnapshot
    market: MarketSnapshot
    haul_session: HaulSessionSnapshot
    ui_state: UiStateSnapshot
    command_history: CommandHistorySnapshot
    prompt_state: PromptStateSnapshot
    replay_browser: ReplayBrowserSnapshot
    activity_log: list[ActivityLogEntry]
    server_status: ServerStatusSnapshot
    trade_routes: TradeRoutesSnapshot = field(default_factory=TradeRoutesSnapshot)
