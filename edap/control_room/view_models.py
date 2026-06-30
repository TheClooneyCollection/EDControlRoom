from __future__ import annotations

from dataclasses import dataclass

from edap.control_room.models import (
    HaulStats,
    MarketData,
    ShipState,
    TradeRoutePickerState,
    TradeRoutesData,
)
from edap.inara.trade_routes import TradeRoute


@dataclass(frozen=True)
class StatusPanelViewModel:
    ship: ShipState


@dataclass(frozen=True)
class HaulPanelViewModel:
    stats: HaulStats
    current_balance: int | None


@dataclass(frozen=True)
class MarketPanelViewModel:
    market: MarketData
    market_filter: str | None
    side: str


@dataclass(frozen=True)
class TradeRoutePickerViewModel:
    routes: tuple[TradeRoute, ...]
    selected_route: TradeRoute | None
    highlighted_index: int | None
    visible: bool
    system_name: str
    searched_at: str


def status_panel_view_model(ship: ShipState) -> StatusPanelViewModel:
    return StatusPanelViewModel(ship=ship)


def haul_panel_view_model(
    stats: HaulStats,
    *,
    current_balance: int | None,
) -> HaulPanelViewModel:
    return HaulPanelViewModel(stats=stats, current_balance=current_balance)


def market_panel_view_model(
    market: MarketData,
    *,
    market_filter: str | None,
    side: str,
) -> MarketPanelViewModel:
    return MarketPanelViewModel(
        market=market,
        market_filter=market_filter,
        side=side,
    )


def trade_route_picker_view_model(
    trade_routes: TradeRoutesData,
    picker_state: TradeRoutePickerState,
) -> TradeRoutePickerViewModel:
    routes = tuple(trade_routes.routes)
    selected_route = None
    highlighted_index = None
    if routes:
        selected_route = next(
            (route for route in routes if route.index == picker_state.selected_route_index),
            routes[0],
        )
        highlighted_index = next(
            (index for index, route in enumerate(routes) if route.index == selected_route.index),
            0,
        )
    return TradeRoutePickerViewModel(
        routes=routes,
        selected_route=selected_route,
        highlighted_index=highlighted_index,
        visible=picker_state.open and bool(routes),
        system_name=trade_routes.system_name,
        searched_at=trade_routes.searched_at,
    )
