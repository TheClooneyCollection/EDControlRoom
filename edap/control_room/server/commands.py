from __future__ import annotations

from typing import Any, Protocol

from edap.control_room_state import CommandHistoryEntry
from edap.inara.trade_routes import TradeRoute


class ObserverSessionCommandHandler(Protocol):
    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None: ...

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

    def load_trade_route(self, route: TradeRoute, *, raw_command: str | None = None) -> None: ...

    def cancel_active_routine(self) -> None: ...

    def open_replay_browser(self) -> None: ...

    def close_replay_browser(self) -> None: ...

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


def command_history_entry_from_payload(payload: dict[str, object]) -> CommandHistoryEntry | None:
    raw_command = payload.get("raw_command")
    command_name = payload.get("command_name")
    arguments_value = payload.get("arguments", {})
    timestamp = payload.get("timestamp", "")
    if not isinstance(raw_command, str) or not isinstance(command_name, str):
        return None
    if not isinstance(arguments_value, dict):
        return None
    if not isinstance(timestamp, str):
        timestamp = ""
    return CommandHistoryEntry(
        raw=raw_command,
        command=command_name,
        params={str(key): value for key, value in arguments_value.items()},
        timestamp=timestamp,
    )


def trade_route_from_payload(payload: object) -> TradeRoute | None:
    if not isinstance(payload, dict):
        return None
    try:
        index_value = payload.get("index", 0)
        index = int(index_value)
    except (TypeError, ValueError):
        return None
    from_station = payload.get("from_station")
    from_system = payload.get("from_system")
    to_station = payload.get("to_station")
    to_system = payload.get("to_system")
    if not all(isinstance(value, str) and value.strip() for value in (from_station, from_system, to_station, to_system)):
        return None
    url_links_value = payload.get("url_links", ())
    if isinstance(url_links_value, list):
        url_links = tuple(str(value) for value in url_links_value)
    elif isinstance(url_links_value, tuple):
        url_links = tuple(str(value) for value in url_links_value)
    else:
        url_links = ()
    return TradeRoute(
        index=index,
        from_station=from_station,
        from_system=from_system,
        to_station=to_station,
        to_system=to_system,
        source_buy_commodity=_optional_str(payload.get("source_buy_commodity")),
        target_buy_commodity=_optional_str(payload.get("target_buy_commodity")),
        from_station_distance=_optional_str(payload.get("from_station_distance")),
        to_station_distance=_optional_str(payload.get("to_station_distance")),
        distance_from_system=_optional_str(payload.get("distance_from_system")),
        route_distance=_optional_str(payload.get("route_distance")),
        profit_per_unit=_optional_str(payload.get("profit_per_unit")),
        profit_per_trip=_optional_str(payload.get("profit_per_trip")),
        profit_per_hour=_optional_str(payload.get("profit_per_hour")),
        updated=_optional_str(payload.get("updated")),
        raw_text=str(payload.get("raw_text", "")),
        url_links=url_links,
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return value or None
