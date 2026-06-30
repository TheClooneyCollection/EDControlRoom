from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from rich.markup import escape

if TYPE_CHECKING:
    from edap.control_room.app import ControlRoomApp


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


@dataclass(frozen=True)
class ControlRoomViewActions:
    market: MarketPanelActions
    trade_routes: TradeRoutePickerActions


class LocalMarketPanelActions:
    def __init__(self, app: ControlRoomApp) -> None:
        self._app = app

    def set_tab(self, side: str) -> None:
        if side not in {"buy", "sell"} or self._app._runtime_state.market_panel_tab == side:
            return
        self._app._runtime_state.market_panel_tab = side
        self._app._refresh_market()

    def lock_display(self) -> None:
        self._app._market.locked = True
        self._app._log("[dim]Market panel locked.[/]")
        self._app._refresh_market()

    def unlock_display(self) -> None:
        self._app._market.locked = False
        self._app._log("[dim]Market panel unlocked.[/]")
        self._app._refresh_market()

    def set_filter(self, value: str) -> None:
        self._app._market_filter = value.title()
        self._app._log(f"[dim]Market filter: {escape(self._app._market_filter)}[/]")
        self._app._refresh_market()

    def clear_filter(self) -> None:
        self._app._market_filter = None
        self._app._log("[dim]Market filter cleared.[/]")
        self._app._refresh_market()


class LocalTradeRoutePickerActions:
    def __init__(self, app: ControlRoomApp) -> None:
        self._app = app

    def close(self) -> None:
        self._app._trade_route_picker_state.open = False
        self._app._refresh_trade_route_picker()
        try:
            self._app.set_focus(self._app.query_one("#cmd"))
        except Exception:
            return

    def move_selection(self, offset: int) -> None:
        if not self._app._trade_routes.routes or offset == 0:
            return
        route_indices = [route.index for route in self._app._trade_routes.routes]
        selected_index = self._app._trade_route_picker_state.selected_route_index
        current_position = route_indices.index(selected_index) if selected_index in route_indices else 0
        next_position = max(0, min(len(route_indices) - 1, current_position + offset))
        self._app._trade_route_picker_state.selected_route_index = route_indices[next_position]
        self._app._refresh_trade_route_picker()

    def load_selected(self) -> None:
        route = self._app._selected_trade_route()
        if route is None:
            return
        self.close()
        self._app._dispatch_command(f"haul route {route.index}")

    def set_destination_for_selected(self) -> None:
        route = self._app._selected_trade_route()
        if route is None or not route.from_system:
            return
        self.close()
        self._app._dispatch_command(f"dest {route.from_system}")


def build_local_control_room_view_actions(app: ControlRoomApp) -> ControlRoomViewActions:
    return ControlRoomViewActions(
        market=LocalMarketPanelActions(app),
        trade_routes=LocalTradeRoutePickerActions(app),
    )
