"""Best commodity deals between two station markets."""

from __future__ import annotations

from dataclasses import dataclass

from edap.recent_markets import MarketItem


@dataclass(frozen=True)
class TradeDeal:
    commodity: str
    name: str
    buy_price: int
    stock: int
    sell_price: int
    demand: int
    profit_per_ton: int
    hold_tons: int
    hold_profit: int


@dataclass(frozen=True)
class RoundTrip:
    outbound: TradeDeal | None
    inbound: TradeDeal | None
    profit_per_ton: int
    hold_profit: int


@dataclass(frozen=True)
class MarketComparison:
    cargo_capacity: int
    outbound: tuple[TradeDeal, ...]
    inbound: tuple[TradeDeal, ...]
    round_trip: RoundTrip


def trade_deals(
    source: tuple[MarketItem, ...],
    destination: tuple[MarketItem, ...],
    cargo_capacity: int,
) -> tuple[TradeDeal, ...]:
    """Commodities bought at source and sold at destination at a profit, best full hold first.

    A full hold is capped by the source stock, so a thin market ranks below a deeper one
    that earns less per ton but fills the hold.
    """
    sell_by_commodity = {item.commodity: item for item in destination if item.sell_price > 0}
    deals = []
    for bought in source:
        sold = sell_by_commodity.get(bought.commodity)
        if sold is None or bought.buy_price <= 0 or bought.stock <= 0:
            continue
        profit = sold.sell_price - bought.buy_price
        if profit <= 0:
            continue
        hold_tons = max(0, min(cargo_capacity, bought.stock))
        deals.append(
            TradeDeal(
                commodity=bought.commodity,
                name=bought.name,
                buy_price=bought.buy_price,
                stock=bought.stock,
                sell_price=sold.sell_price,
                demand=sold.demand,
                profit_per_ton=profit,
                hold_tons=hold_tons,
                hold_profit=profit * hold_tons,
            )
        )
    deals.sort(key=lambda deal: (-deal.hold_profit, -deal.profit_per_ton, deal.name))
    return tuple(deals)


def compare_markets(
    market_x: tuple[MarketItem, ...],
    market_y: tuple[MarketItem, ...],
    cargo_capacity: int,
) -> MarketComparison:
    outbound = trade_deals(market_x, market_y, cargo_capacity)
    inbound = trade_deals(market_y, market_x, cargo_capacity)
    best_out = outbound[0] if outbound else None
    best_in = inbound[0] if inbound else None
    legs = [deal for deal in (best_out, best_in) if deal is not None]
    return MarketComparison(
        cargo_capacity=cargo_capacity,
        outbound=outbound,
        inbound=inbound,
        round_trip=RoundTrip(
            outbound=best_out,
            inbound=best_in,
            profit_per_ton=sum(deal.profit_per_ton for deal in legs),
            hold_profit=sum(deal.hold_profit for deal in legs),
        ),
    )
