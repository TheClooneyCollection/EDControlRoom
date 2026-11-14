"""Best commodity deals between two station markets."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from edcr.market_db import StoredPrices
from edcr.recent_markets import MarketItem, MarketSnapshot, market_items

# Where a market's prices came from: our own Market.json, or the EDDN store.
SOURCE_VISIT = "visit"
SOURCE_EDDN = "eddn"


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


@dataclass(frozen=True)
class PricedMarket:
    """A market's prices for the comparison, from whichever source is newer."""

    market_id: int
    items: tuple[MarketItem, ...]
    source: str
    # ISO 8601 UTC, like a Market.json timestamp.
    prices_at: str


def snapshot_epoch(timestamp: str) -> float:
    """A Market.json timestamp (`2026-11-14T19:29:00Z`) as epoch seconds; 0 when blank or malformed."""
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def pick_prices(snapshot: MarketSnapshot, stored: StoredPrices | None) -> PricedMarket:
    """The newer of our own visit and the EDDN store, so a visit from yesterday does not hide a
    discount EDDN saw today. The store's items take their names from our visit where it has them.

    A store row at the same instant as the visit is that visit, imported into the store, so the visit wins.
    """
    if stored is None or stored.updated_at <= snapshot_epoch(snapshot.timestamp):
        return PricedMarket(snapshot.market_id, market_items(snapshot), SOURCE_VISIT, snapshot.timestamp)
    names = {item.commodity: item.name for item in market_items(snapshot)}
    items = tuple(replace(item, name=names.get(item.commodity, item.name)) for item in stored.items)
    prices_at = datetime.fromtimestamp(stored.updated_at, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return PricedMarket(snapshot.market_id, items, SOURCE_EDDN, prices_at)


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
