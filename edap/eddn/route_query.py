"""Turn `/api/eddn-routes` query parameters into a route search and a JSON payload."""
from __future__ import annotations

import math
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from edap.eddn.routes import FoundRoute, RouteFilters, RouteLeg, TimeModel, find_routes, load_route_markets

DEFAULT_ROUTE_JUMPS = 4
DEFAULT_LADEN_JUMP_RANGE_LY = 17.2


@dataclass(frozen=True)
class RouteQuery:
    view: str
    system: str
    jumps: int
    laden_jump_range_ly: float
    max_route_ly: float
    origin_radius_ly: float
    capacity: int
    filters: RouteFilters
    limit: int


def parse_route_query(
    params: Mapping[str, str], *, search_defaults: Mapping[str, str], current_system: str, cargo_capacity: int
) -> RouteQuery:
    """Build a query; missing parameters fall back to `haul_search.toml` and the current ship."""

    def value(key: str, default_key: str | None = None) -> str:
        raw = (params.get(key) or "").strip()
        return raw or (search_defaults.get(default_key or key) or "").strip()

    def number(key: str, fallback: float, default_key: str | None = None) -> float:
        raw = value(key, default_key)
        if not raw or raw.lower() == "any":
            return fallback
        parsed = float(raw)
        if not math.isfinite(parsed) or parsed < 0:
            raise ValueError(f"{key} must be a non-negative number")
        return parsed

    view = value("view") or "near"
    if view not in {"near", "global"}:
        raise ValueError("view must be near or global")
    laden = number("laden_jump_range_ly", DEFAULT_LADEN_JUMP_RANGE_LY, "max_route_distance_ly")
    if laden <= 0:
        raise ValueError("laden_jump_range_ly must be positive")
    jumps = int(number("jumps", DEFAULT_ROUTE_JUMPS))
    # An explicit ly range (the 100 ly+ presets) overrides the jump count.
    max_route_ly = number("max_route_ly", jumps * laden) or jumps * laden
    max_station_ls = number("max_station_distance_ls", 0.0)
    pad = value("pad", "min_landing_pad").lower()[:1].upper() or "L"
    if pad not in {"S", "M", "L"}:
        raise ValueError("pad must be S, M or L")
    return RouteQuery(
        view=view,
        system=value("system") or current_system,
        jumps=jumps,
        laden_jump_range_ly=laden,
        max_route_ly=max_route_ly,
        origin_radius_ly=number("radius_ly", max_route_ly),
        capacity=int(number("capacity", cargo_capacity)),
        filters=RouteFilters(
            min_pad=pad,
            include_surface=_flag(value("surface", "use_surface_stations")),
            include_carriers=_flag(value("carriers")),
            max_station_distance_ls=max_station_ls or None,
            min_supply=int(number("min_supply", 0)),
            max_age_s=number("max_age_hours", 48.0, "max_price_age_hours") * 3600 or 48 * 3600,
        ),
        limit=min(200, max(1, int(number("limit", 50)))),
    )


def _flag(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


class RouteQueryError(LookupError):
    """The query is valid but cannot run, such as an unknown origin system."""


def run_route_query(
    database_file: Path,
    query: RouteQuery,
    *,
    time_model: TimeModel,
    display_names: Mapping[str, str],
    now: float,
) -> dict[str, Any]:
    """Search and build the payload; `display_names` maps EDDN keys to in-game names for haul."""
    db = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)
    try:
        origin = None
        if query.view == "near":
            if not query.system:
                raise RouteQueryError("No current system; pass system= or use the global view.")
            origin = db.execute(
                "SELECT x, y, z FROM system WHERE name = ? COLLATE NOCASE ORDER BY updated_at DESC LIMIT 1",
                (query.system,),
            ).fetchone()
            if origin is None:
                raise RouteQueryError(f"{query.system} has no coordinates in the EDDN database yet.")
        markets = load_route_markets(db, query.filters, now=now)
    finally:
        db.close()
    routes = find_routes(
        markets,
        capacity=query.capacity,
        max_route_ly=query.max_route_ly,
        laden_jump_range_ly=query.laden_jump_range_ly,
        time_model=time_model,
        origin=origin,
        origin_radius_ly=query.origin_radius_ly if origin is not None else None,
        limit=query.limit,
    )
    return {
        "query": asdict(query),
        "generated_at": now,
        "markets_considered": len(markets),
        "routes": [route_payload(route, display_names=display_names, now=now) for route in routes],
    }


def route_payload(route: FoundRoute, *, display_names: Mapping[str, str], now: float) -> dict[str, Any]:
    def station(market) -> dict[str, Any]:
        return {
            "market_id": market.market_id, "station": market.station, "system": market.system,
            "type": market.station_type, "dist_ls": market.dist_ls, "is_surface": market.is_surface,
            "age_s": max(0.0, now - market.updated_at),
        }

    def leg(trade: RouteLeg | None) -> dict[str, Any] | None:
        if trade is None:
            return None
        return {**asdict(trade), "name": display_names.get(trade.commodity, trade.commodity),
                "name_known": trade.commodity in display_names}

    outbound, inbound = leg(route.outbound), leg(route.inbound)
    return {
        "station_1": station(route.station_1),
        "station_2": station(route.station_2),
        "distance_ly": round(route.distance_ly, 2),
        "jumps": route.jumps,
        "outbound": outbound,
        "inbound": inbound,
        "profit_per_trip": route.profit_per_trip,
        "trip_s": round(route.trip_s),
        "profit_per_hour": route.profit_per_hour,
        # Haul buys by in-game name, so only fully named routes can be pasted into /haul.
        "trade_route": _trade_route(route, outbound, inbound)
        if all(trade is None or trade["name_known"] for trade in (outbound, inbound))
        else None,
    }


def _trade_route(route: FoundRoute, outbound: dict[str, Any] | None, inbound: dict[str, Any] | None) -> dict[str, Any]:
    a, b = route.station_1, route.station_2

    def ls(market) -> str | None:
        return f"{round(market.dist_ls):,} Ls" if market.dist_ls is not None else None

    return {
        "index": 0,
        "from_station": a.station, "from_system": a.system,
        "to_station": b.station, "to_system": b.system,
        "source_buy_commodity": outbound["name"] if outbound else None,
        "target_buy_commodity": inbound["name"] if inbound else None,
        "from_station_distance": ls(a), "to_station_distance": ls(b),
        "route_distance": f"{route.distance_ly:.2f} Ly",
        "profit_per_trip": f"{route.profit_per_trip:,} Cr",
        "profit_per_hour": f"{route.profit_per_hour:,} Cr",
        "from_supply": f"{outbound['supply']:,}" if outbound else None,
        "to_demand": f"{outbound['demand']:,}" if outbound else None,
        "to_supply": f"{inbound['supply']:,}" if inbound else None,
        "from_demand": f"{inbound['demand']:,}" if inbound else None,
        # Planetary ports usually dock like orbital ones; manual landing is the pilot's call.
        "from_manual_landing": False, "to_manual_landing": False,
    }
