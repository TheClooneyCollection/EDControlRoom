"""Two-station round-trip routes from the EDDN price table, ranked by profit per hour.

A route is A -> B -> A: the best commodity bought at A and sold at B, then the best
commodity bought at B and sold at A (either side may be empty). Holds are capped by
cargo capacity and the seller's stock. Demand is ignored: a station buys anything it
lists a sell price for, even its own exports showing a demand of 1.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from typing import Iterable

PAD_ORDER = {"S": 1, "M": 2, "L": 3}
# Pad size by station type when no Docked event reported the pads yet.
_TYPE_PADS = {
    "Coriolis": "L", "Orbis": "L", "Ocellus": "L", "Dodec": "L", "Bernal": "L",
    "AsteroidBase": "L", "CraterPort": "L", "CraterOutpost": "L", "MegaShip": "L",
    "Outpost": "M",
}
SURFACE_TYPES = frozenset({"CraterOutpost", "CraterPort", "SurfaceStation", "OnFootSettlement"})


@dataclass(frozen=True)
class RouteMarket:
    market_id: int
    station: str
    system: str
    x: float
    y: float
    z: float
    station_type: str
    dist_ls: float | None
    is_surface: bool
    updated_at: float
    # commodity -> (buy price, supply) where the station sells to us
    exports: dict[str, tuple[int, int]] = field(default_factory=dict)
    # commodity -> (sell price, demand) where the station buys from us
    imports: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteFilters:
    min_pad: str = "L"
    include_surface: bool = False
    include_carriers: bool = False
    max_station_distance_ls: float | None = 5000.0
    min_supply: int = 0
    max_age_s: float = 2 * 86400


@dataclass(frozen=True)
class TimeModel:
    """Seconds per leg: trading while docked, then undock, jumps, supercruise and docking.

    Fitted on 2026-11 journals (125 Undocked -> Docked legs): one jump at 56 Ls took 330s and
    at 337 Ls 373s, docked time was ~90s, and later jumps added ~65s each. Flying to the
    Crater Outpost Chauhan Dock (292 Ls) took ~390s against 366s for an orbital station,
    so a surface station adds ~30s for the planetary approach and landing.
    """
    docked_s: float = 90.0
    travel_base_s: float = 110.0
    first_jump_s: float = 170.0
    per_extra_jump_s: float = 65.0
    supercruise_coeff: float = 13.0
    unknown_dist_ls: float = 1000.0
    surface_extra_s: float = 30.0

    def supercruise_s(self, dist_ls: float | None) -> float:
        distance = self.unknown_dist_ls if dist_ls is None else max(0.0, dist_ls)
        # Supercruise accelerates with distance, so time grows roughly with its cube root.
        return self.supercruise_coeff * distance ** (1 / 3)

    def leg_s(self, jumps: int, dist_ls: float | None, *, surface: bool) -> float:
        """One leg ending at a station `dist_ls` from the star; `surface` when it is on a planet."""
        jump_s = self.first_jump_s + (jumps - 1) * self.per_extra_jump_s if jumps > 0 else 0.0
        landing_s = self.surface_extra_s if surface else 0.0
        return self.docked_s + self.travel_base_s + jump_s + self.supercruise_s(dist_ls) + landing_s


def jump_count(system_a: str, system_b: str, distance_ly: float, laden_jump_range_ly: float) -> int:
    """Jumps per leg: none inside one system, else the laden range covers the distance."""
    if system_a.casefold() == system_b.casefold():
        return 0
    return max(1, math.ceil(distance_ly / laden_jump_range_ly - 1e-9))


def round_trip_s(
    time_model: TimeModel,
    jumps: int,
    *,
    a_dist_ls: float | None,
    a_surface: bool,
    b_dist_ls: float | None,
    b_surface: bool,
) -> float:
    """A -> B -> A: one leg ending at each station, both with the same jump count."""
    return time_model.leg_s(jumps, b_dist_ls, surface=b_surface) + time_model.leg_s(jumps, a_dist_ls, surface=a_surface)


@dataclass(frozen=True)
class RouteLeg:
    commodity: str
    buy_price: int
    sell_price: int
    supply: int
    demand: int
    tons: int
    profit_per_ton: int
    profit: int


@dataclass(frozen=True)
class FoundRoute:
    station_1: RouteMarket
    station_2: RouteMarket
    distance_ly: float
    jumps: int
    outbound: RouteLeg | None
    inbound: RouteLeg | None
    profit_per_trip: int
    trip_s: float
    profit_per_hour: int
    data_updated_at: float


def load_route_markets(db: sqlite3.Connection, filters: RouteFilters, *, now: float) -> list[RouteMarket]:
    rows = db.execute(
        """
        SELECT m.market_id, m.station_name, m.system_name, m.is_carrier, m.updated_at,
               st.type, st.dist_ls, st.max_pad,
               COALESCE(sa.x, sn.x), COALESCE(sa.y, sn.y), COALESCE(sa.z, sn.z)
        FROM market m
        LEFT JOIN station st ON st.market_id = m.market_id
        LEFT JOIN system sa ON sa.address = st.system_address
        LEFT JOIN system sn ON sn.name = m.system_name COLLATE NOCASE
        WHERE m.updated_at >= ?
        """,
        (now - filters.max_age_s,),
    ).fetchall()
    markets: dict[int, RouteMarket] = {}
    for (market_id, station, system, is_carrier, updated_at, station_type, dist_ls, max_pad, x, y, z) in rows:
        station_type = station_type or ""
        # A newer commodity message rewrites market.is_carrier from the name alone, so a
        # named carrier ("VAON") loses the flag; its station type still says FleetCarrier.
        is_carrier = is_carrier or station_type == "FleetCarrier"
        if x is None or (is_carrier and not filters.include_carriers) or "ConstructionDepot" in station_type:
            continue
        pad = max_pad or _TYPE_PADS.get(station_type, "")
        if PAD_ORDER.get(pad, 0) < PAD_ORDER[filters.min_pad]:
            continue
        is_surface = station_type in SURFACE_TYPES
        if is_surface and not filters.include_surface:
            continue
        if filters.max_station_distance_ls is not None and dist_ls is not None and dist_ls > filters.max_station_distance_ls:
            continue
        markets[market_id] = RouteMarket(
            market_id=market_id, station=station, system=system, x=x, y=y, z=z,
            station_type=station_type, dist_ls=dist_ls, is_surface=is_surface, updated_at=updated_at,
        )
    for market_id, commodity, buy, sell, supply, demand in db.execute(
        "SELECT market_id, commodity, buy, sell, supply, demand FROM price"
    ):
        market = markets.get(market_id)
        if market is None:
            continue
        if buy > 0 and supply > 0 and supply >= filters.min_supply:
            market.exports[commodity] = (buy, supply)
        if sell > 0:
            market.imports[commodity] = (sell, demand)
    return [market for market in markets.values() if market.exports or market.imports]


def best_leg(source: RouteMarket, target: RouteMarket, capacity: int) -> RouteLeg | None:
    best: RouteLeg | None = None
    for commodity, (buy, supply) in source.exports.items():
        offer = target.imports.get(commodity)
        if offer is None or offer[0] <= buy:
            continue
        sell, demand = offer
        tons = min(capacity, supply)
        leg = RouteLeg(commodity, buy, sell, supply, demand, tons, sell - buy, (sell - buy) * tons)
        if best is None or (leg.profit, leg.profit_per_ton) > (best.profit, best.profit_per_ton):
            best = leg
    return best


def _distance(a: RouteMarket, b: RouteMarket) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def find_routes(
    markets: Iterable[RouteMarket],
    *,
    capacity: int,
    max_route_ly: float,
    laden_jump_range_ly: float,
    time_model: TimeModel,
    origin: tuple[float, float, float] | None = None,
    origin_radius_ly: float | None = None,
    limit: int = 50,
) -> list[FoundRoute]:
    """Rank round trips with both stations at most `max_route_ly` apart.

    With `origin`, station 1 must lie within `origin_radius_ly` of it (the near view).
    """
    markets = list(markets)
    cell = max(max_route_ly, 1.0)
    grid: dict[tuple[int, int, int], list[RouteMarket]] = {}
    for market in markets:
        grid.setdefault(_cell(market, cell), []).append(market)
    starts = markets
    if origin is not None and origin_radius_ly is not None:
        starts = [m for m in markets if math.dist(origin, (m.x, m.y, m.z)) <= origin_radius_ly]
    start_ids = {m.market_id for m in starts}

    found: list[FoundRoute] = []
    for a in starts:
        cx, cy, cz = _cell(a, cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for b in grid.get((cx + dx, cy + dy, cz + dz), ()):
                        # Each unordered pair once; a pair of two start stations is seen from the lower id.
                        if b.market_id == a.market_id or (b.market_id in start_ids and b.market_id < a.market_id):
                            continue
                        distance = _distance(a, b)
                        if distance > max_route_ly:
                            continue
                        route = _route(a, b, distance, capacity, laden_jump_range_ly, time_model)
                        if route is not None:
                            found.append(route)
    found.sort(key=lambda route: (route.profit_per_hour, route.profit_per_trip), reverse=True)
    return found[:limit]


def _cell(market: RouteMarket, size: float) -> tuple[int, int, int]:
    return (math.floor(market.x / size), math.floor(market.y / size), math.floor(market.z / size))


def _route(
    a: RouteMarket, b: RouteMarket, distance: float, capacity: int, jump_range: float, time_model: TimeModel
) -> FoundRoute | None:
    outbound = best_leg(a, b, capacity)
    inbound = best_leg(b, a, capacity)
    profit = (outbound.profit if outbound else 0) + (inbound.profit if inbound else 0)
    if profit <= 0:
        return None
    # Station 1 is where the bigger hold is bought, so a one-sided route starts at its buy.
    if (inbound.profit if inbound else 0) > (outbound.profit if outbound else 0):
        a, b, outbound, inbound = b, a, inbound, outbound
    jumps = jump_count(a.system, b.system, distance, jump_range)
    trip_s = round_trip_s(
        time_model, jumps, a_dist_ls=a.dist_ls, a_surface=a.is_surface, b_dist_ls=b.dist_ls, b_surface=b.is_surface
    )
    return FoundRoute(
        station_1=a, station_2=b, distance_ly=distance, jumps=jumps, outbound=outbound, inbound=inbound,
        profit_per_trip=profit, trip_s=trip_s, profit_per_hour=round(profit * 3600 / trip_s),
        data_updated_at=min(a.updated_at, b.updated_at),
    )
