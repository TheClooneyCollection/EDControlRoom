from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from edap.inara.trade_routes import TradeRoute


class MarketPanelActions(Protocol):
    def set_tab(self, side: str) -> None: ...

    def lock_display(self) -> None: ...

    def unlock_display(self) -> None: ...

    def set_filter(self, value: str) -> None: ...

    def clear_filter(self) -> None: ...


class TradeRoutePickerActions(Protocol):
    def close(self) -> None: ...

    def move_selection(self, offset: int) -> None: ...

    def load_selected(self) -> None: ...

    def set_destination_for_selected(self) -> None: ...

    def travel_to_selected(self) -> None: ...


class MarketPanelActionDependencies(Protocol):
    def current_tab(self) -> str: ...

    def set_tab_state(self, side: str) -> None: ...

    def set_display_locked(self, locked: bool) -> None: ...

    def set_filter_state(self, value: str | None) -> None: ...

    def append_notice(self, message_text: str) -> None: ...

    def market_changed(self) -> None: ...


class TradeRoutePickerActionDependencies(Protocol):
    def route_indices(self) -> tuple[int, ...]: ...

    def selected_route_index(self) -> int | None: ...

    def set_selected_route_index(self, index: int | None) -> None: ...

    def selected_route(self) -> TradeRoute | None: ...

    def set_picker_open(self, is_open: bool) -> None: ...

    def persist_selected_route(self, route: TradeRoute) -> None: ...

    def submit_command(self, raw: str) -> None: ...

    def dispatch_travel(self, *, system: str, station: str) -> None: ...

    def picker_changed(self) -> None: ...

    def picker_closed(self) -> None: ...


@dataclass(frozen=True)
class ControlRoomViewActions:
    market: MarketPanelActions
    trade_routes: TradeRoutePickerActions


class MarketPanelViewActions:
    def __init__(self, dependencies: MarketPanelActionDependencies) -> None:
        self._dependencies = dependencies

    def set_tab(self, side: str) -> None:
        if side not in {"buy", "sell"} or self._dependencies.current_tab() == side:
            return
        self._dependencies.set_tab_state(side)
        self._dependencies.market_changed()

    def lock_display(self) -> None:
        self._dependencies.set_display_locked(True)
        self._dependencies.append_notice("Market panel pinned.")
        self._dependencies.market_changed()

    def unlock_display(self) -> None:
        self._dependencies.set_display_locked(False)
        self._dependencies.append_notice("Market panel following latest market.")
        self._dependencies.market_changed()

    def set_filter(self, value: str) -> None:
        market_filter = value.title()
        self._dependencies.set_filter_state(market_filter)
        self._dependencies.append_notice(f"Market filter: {market_filter}")
        self._dependencies.market_changed()

    def clear_filter(self) -> None:
        self._dependencies.set_filter_state(None)
        self._dependencies.append_notice("Market filter cleared.")
        self._dependencies.market_changed()


class TradeRoutePickerViewActions:
    def __init__(self, dependencies: TradeRoutePickerActionDependencies) -> None:
        self._dependencies = dependencies

    def close(self) -> None:
        self._dependencies.set_picker_open(False)
        self._dependencies.picker_changed()
        self._dependencies.picker_closed()

    def move_selection(self, offset: int) -> None:
        route_indices = self._dependencies.route_indices()
        if not route_indices or offset == 0:
            return
        selected_index = self._dependencies.selected_route_index()
        current_position = route_indices.index(selected_index) if selected_index in route_indices else 0
        next_position = max(0, min(len(route_indices) - 1, current_position + offset))
        self._dependencies.set_selected_route_index(route_indices[next_position])
        self._dependencies.picker_changed()

    def load_selected(self) -> None:
        route = self._dependencies.selected_route()
        if route is None:
            return
        self._dependencies.persist_selected_route(route)
        self.close()
        self._dependencies.submit_command(f"haul route {route.index}")

    def set_destination_for_selected(self) -> None:
        route = self._dependencies.selected_route()
        if route is None or not route.from_system:
            return
        self._dependencies.persist_selected_route(route)
        self.close()
        self._dependencies.submit_command(f"dest {route.from_system}")

    def travel_to_selected(self) -> None:
        route = self._dependencies.selected_route()
        if route is None or not route.from_system or not route.from_station:
            return
        self._dependencies.persist_selected_route(route)
        self.close()
        self._dependencies.dispatch_travel(
            system=route.from_system,
            station=route.from_station,
        )
