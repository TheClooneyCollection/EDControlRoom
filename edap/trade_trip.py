"""Trip time and measured profit per hour for a Best deal station pair.

The estimate uses the same time model and jump count as `/routes`, so both pages agree.
Each station needs its system coordinates, distance from the star and station type; these
come from the market store (EDDN, our journal and Market.json), then Ardent for what is still missing.
Nothing is guessed: a missing input leaves the trip time unknown and names what is missing.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from edap.eddn.routes import SURFACE_TYPES, TimeModel, jump_count, round_trip_s
from edap.haul_history import RouteSummary
from edap.recent_markets import MarketSnapshot

Coords = tuple[float, float, float]


@dataclass(frozen=True)
class PartialFacts:
    coords: Coords | None = None
    dist_ls: float | None = None
    station_type: str | None = None


@dataclass(frozen=True)
class StationFacts:
    station: str
    system: str
    coords: Coords | None
    coords_source: str | None
    dist_ls: float | None
    dist_ls_source: str | None
    station_type: str | None
    station_type_source: str | None


# Looks up what one source knows about a station: (market id, station name, system name).
FactLookup = Callable[[int, str, str], PartialFacts]


@dataclass(frozen=True)
class TripEstimate:
    laden_jump_range_ly: float
    distance_ly: float | None
    jumps: int | None
    trip_s: float | None
    missing: tuple[str, ...]


@dataclass(frozen=True)
class MeasuredRoute:
    runs: int
    profit: int
    duration_s: float
    profit_per_hour: int


def gather_facts(
    market_id: int, station: str, system: str, sources: Sequence[tuple[str, FactLookup]]
) -> StationFacts:
    """Fill each input from the first source that has it; later sources are asked only while one is missing."""
    found: dict[str, tuple[object, str]] = {}
    for name, lookup in sources:
        if len(found) == 3:
            break
        facts = lookup(market_id, station, system)
        for field in ("coords", "dist_ls", "station_type"):
            value = getattr(facts, field)
            if field not in found and value is not None and value != "":
                found[field] = (value, name)

    def pick(field: str) -> tuple[object, str | None]:
        return found.get(field, (None, None))

    coords, coords_source = pick("coords")
    dist_ls, dist_source = pick("dist_ls")
    station_type, type_source = pick("station_type")
    return StationFacts(
        station=station, system=system,
        coords=coords, coords_source=coords_source,  # type: ignore[arg-type]
        dist_ls=dist_ls, dist_ls_source=dist_source,  # type: ignore[arg-type]
        station_type=station_type, station_type_source=type_source,  # type: ignore[arg-type]
    )


def estimate_trip(
    x: StationFacts, y: StationFacts, *, laden_jump_range_ly: float, time_model: TimeModel
) -> TripEstimate:
    """Round trip X -> Y -> X; `trip_s` is None while any input is missing."""
    same_system = x.system.casefold() == y.system.casefold()
    missing: list[str] = []
    for facts in (x, y) if not same_system else ():
        if facts.coords is None:
            missing.append(f"{facts.system} coordinates")
    for facts in (x, y):
        if facts.dist_ls is None:
            missing.append(f"{facts.station} distance from star")
        if not facts.station_type:
            missing.append(f"{facts.station} station type")
    distance: float | None = 0.0 if same_system else None
    if x.coords is not None and y.coords is not None and not same_system:
        distance = math.dist(x.coords, y.coords)
    jumps = jump_count(x.system, y.system, distance, laden_jump_range_ly) if distance is not None else None
    trip_s = None
    if not missing and jumps is not None:
        trip_s = round_trip_s(
            time_model, jumps,
            a_dist_ls=x.dist_ls, a_surface=x.station_type in SURFACE_TYPES,
            b_dist_ls=y.dist_ls, b_surface=y.station_type in SURFACE_TYPES,
        )
    return TripEstimate(
        laden_jump_range_ly=laden_jump_range_ly,
        distance_ly=round(distance, 2) if distance is not None else None,
        jumps=jumps, trip_s=round(trip_s) if trip_s is not None else None, missing=tuple(missing),
    )


def measured_route(
    routes: Iterable[RouteSummary], x: MarketSnapshot, y: MarketSnapshot
) -> MeasuredRoute | None:
    """Completed haul runs between the two stations, either direction; None without any timed run."""
    runs = profit = 0
    duration = 0.0
    pair = {x.station.casefold(), y.station.casefold()}
    if len(pair) != 2:
        return None
    systems = {x.station.casefold(): x.system.casefold(), y.station.casefold(): y.system.casefold()}
    for route in routes:
        ends = ((route.station_1, route.system_1), (route.station_2, route.system_2))
        if {station.casefold() for station, _ in ends} != pair:
            continue
        # A recorded system must match too, so two same-named stations in different systems stay apart.
        if any(system is not None and system.casefold() != systems[station.casefold()] for station, system in ends):
            continue
        runs += route.completed.count
        profit += route.completed.profit
        duration += route.completed.duration_s
    if not runs or duration <= 0:
        return None
    return MeasuredRoute(runs=runs, profit=profit, duration_s=duration, profit_per_hour=round(profit * 3600 / duration))


def store_lookup(db: sqlite3.Connection) -> FactLookup:
    """The market store's station row (by market id) and system coordinates (by address, else name).

    An unreadable store (such as one mid-migration) knows nothing, so the next source answers.
    """

    def lookup(market_id: int, station: str, system: str) -> PartialFacts:
        try:
            row = query(market_id, system)
        except sqlite3.Error:
            return PartialFacts()
        station_type, dist_ls, x, y, z = row
        return PartialFacts(
            coords=(x, y, z) if x is not None else None,
            dist_ls=dist_ls,
            station_type=station_type or None,
        )

    def query(market_id: int, system: str) -> tuple:
        return db.execute(
            "SELECT st.type, st.dist_ls, COALESCE(sa.x, sn.x), COALESCE(sa.y, sn.y), COALESCE(sa.z, sn.z)"
            " FROM (SELECT ? AS market_id, ? AS system_name) q"
            " LEFT JOIN station st ON st.market_id = q.market_id"
            " LEFT JOIN system sa ON sa.address = st.system_address"
            " LEFT JOIN system sn ON sn.name = q.system_name COLLATE NOCASE"
            " ORDER BY sn.updated_at DESC LIMIT 1",
            (market_id, system),
        ).fetchone()

    return lookup
