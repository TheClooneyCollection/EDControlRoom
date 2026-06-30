from __future__ import annotations

from dataclasses import dataclass

from edap.control_room.models import HaulStats, MarketData, ShipState


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
