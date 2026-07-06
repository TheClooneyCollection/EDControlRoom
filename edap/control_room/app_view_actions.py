from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markup import escape

from edap.control_room.view_actions import (
    ControlRoomViewActions,
    MarketPanelViewActions,
    TradeRoutePickerViewActions,
)
from edap.inara.trade_routes import TradeRoute

if TYPE_CHECKING:
    from edap.control_room.app import ControlRoomApp


class ControlRoomAppMarketPanelActionDependencies:
    def __init__(self, app: ControlRoomApp) -> None:
        self._app = app

    def current_tab(self) -> str:
        return self._app._runtime_state.market_panel_tab

    def set_tab_state(self, side: str) -> None:
        self._app._runtime_state.market_panel_tab = side

    def set_display_locked(self, locked: bool) -> None:
        self._app._market.locked = locked

    def set_filter_state(self, value: str | None) -> None:
        self._app._market_filter = value

    def append_notice(self, message_text: str) -> None:
        self._app._log(f"[dim]{escape(message_text)}[/]")

    def market_changed(self) -> None:
        self._app._refresh_market()


class ControlRoomAppTradeRoutePickerActionDependencies:
    def __init__(self, app: ControlRoomApp) -> None:
        self._app = app

    def route_indices(self) -> tuple[int, ...]:
        return tuple(route.index for route in self._app._trade_routes.routes)

    def selected_route_index(self) -> int | None:
        return self._app._trade_route_picker_state.selected_route_index

    def set_selected_route_index(self, index: int | None) -> None:
        self._app._trade_route_picker_state.selected_route_index = index

    def selected_route(self) -> TradeRoute | None:
        selected_index = self.selected_route_index()
        if selected_index is None:
            return None
        return next(
            (route for route in self._app._trade_routes.routes if route.index == selected_index),
            None,
        )

    def set_picker_open(self, is_open: bool) -> None:
        self._app._trade_route_picker_state.open = is_open

    def persist_selected_route(self, route: TradeRoute) -> None:
        self._app._saved_state.selected_trade_route = route
        self._app._save_saved_state()
        self._app._publish_protocol_data_refresh()

    def submit_command(self, raw: str) -> None:
        self._app._dispatch_command(raw)

    def dispatch_travel(self, *, system: str, station: str) -> None:
        self._app._dispatch_travel(
            system=system,
            station=station,
            raw_command=f"travel {system} / {station}",
        )

    def picker_changed(self) -> None:
        self._app._refresh_trade_route_picker()

    def picker_closed(self) -> None:
        try:
            self._app.set_focus(self._app.query_one("#cmd"))
        except Exception:
            return


def build_control_room_app_view_actions(app: ControlRoomApp) -> ControlRoomViewActions:
    return ControlRoomViewActions(
        market=MarketPanelViewActions(ControlRoomAppMarketPanelActionDependencies(app)),
        trade_routes=TradeRoutePickerViewActions(ControlRoomAppTradeRoutePickerActionDependencies(app)),
    )
