"""Nearest service stations from hub observations and Spansh search results."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import closing
from dataclasses import asdict, dataclass, replace
import math
from pathlib import Path
import sqlite3
from typing import Any

from edcr.cheapest_markets import PAD_ORDER
from edcr.eddn.messages import is_carrier_station

SERVICE_LABELS = {
    "carriermanagement": "Fleet Carrier Administration",
    "carriervendor": "Fleet Carrier Vendor",
    "facilitator": "Interstellar Factors Contact",
    "materialtrader": "Material Trader",
    "techbroker": "Technology Broker",
    "shipyard": "Shipyard",
    "outfitting": "Outfitting",
    "blackmarket": "Black Market",
}
PAGE_SERVICES = tuple(SERVICE_LABELS)


@dataclass(frozen=True)
class ServiceQuery:
    service: str
    reference_system: str
    radius_ly: float | None
    pad: str
    include_carriers: bool
    use_spansh: bool
    limit: int


@dataclass(frozen=True)
class ServiceStation:
    source: str
    market_id: int
    system_name: str
    station_name: str
    station_type: str
    is_carrier: bool
    max_pad: str
    dist_ls: float | None
    distance_ly: float
    services_at: float


def parse_service_query(params: Mapping[str, str], *, current_system: str,
                        ship_pad: str) -> ServiceQuery:
    service = params.get("service", "").strip().lower()
    if not service:
        raise ValueError("service is required")
    system = params.get("system", current_system).strip()
    if not system:
        raise ValueError("system is required")
    pad = params.get("pad", ship_pad).strip().upper()
    if pad not in PAD_ORDER:
        raise ValueError("pad must be S, M or L")
    radius_text = params.get("radius_ly", "200").strip()
    radius = None
    if radius_text:
        try:
            radius = float(radius_text)
        except ValueError:
            raise ValueError("radius_ly must be a finite non-negative number") from None
        if not math.isfinite(radius) or radius < 0:
            raise ValueError("radius_ly must be a finite non-negative number")
    toggles = []
    for key, default in (("carriers", "0"), ("spansh", "1")):
        value = params.get(key, default).strip()
        if value not in ("0", "1"):
            raise ValueError(f"{key} must be 0 or 1")
        toggles.append(value == "1")
    return ServiceQuery(service, system, radius, pad, *toggles, 50)


def _order(station: ServiceStation) -> tuple[float, float, int]:
    return (station.distance_ly, station.dist_ls if station.dist_ls is not None else math.inf,
            station.market_id)


def _hidden_reason(station: ServiceStation, query: ServiceQuery) -> str:
    if station.is_carrier and not query.include_carriers:
        return "carrier"
    if station.max_pad and PAD_ORDER[station.max_pad] < PAD_ORDER[query.pad]:
        return "pad"
    if not math.isfinite(station.distance_ly):
        return "no_coords"
    if query.radius_ly is not None and station.distance_ly > query.radius_ly:
        return "radius"
    return ""


def query_hub_services(db: Path, query: ServiceQuery, origin: tuple[float, float, float] | None
                       ) -> tuple[list[ServiceStation], dict[str, int]]:
    """Count each exclusion once; retain all qualifying rows until merging."""
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        rows = connection.execute(
            "SELECT s.market_id, s.system_name, s.name, s.type, s.max_pad, s.dist_ls, "
            "seen.updated_at, y.x, y.y, y.z FROM station_service service "
            "JOIN station s USING (market_id) JOIN station_services_seen seen USING (market_id) "
            "LEFT JOIN system y ON y.address = s.system_address WHERE service.service = ?",
            (query.service,),
        ).fetchall()
    stations = []
    hidden = dict.fromkeys(("carrier", "pad", "radius", "no_coords"), 0)
    for mid, system, name, kind, pad, arrival, updated, x, y, z in rows:
        distance = (math.dist(origin, (x, y, z))
                    if origin is not None and all(value is not None for value in (x, y, z))
                    else math.inf)
        station = ServiceStation("hub", mid, system, name, kind, is_carrier_station(name, kind),
                                 pad, arrival, distance, updated)
        reason = _hidden_reason(station, query)
        if reason:
            hidden[reason] += 1
        else:
            stations.append(station)
    return sorted(stations, key=_order), hidden


def merge_stations(hub: list[ServiceStation], spansh: list[ServiceStation],
                   query: ServiceQuery) -> tuple[list[ServiceStation], dict[str, int], int]:
    """Return the limited rows, local exclusions and qualifying merged total.

    Newer service observations win; equal timestamps prefer the hub. Hub inputs
    are already filtered, so exclusions here count the surviving Spansh rows.
    """
    merged = {station.market_id: station for station in hub}
    for station in spansh:
        previous = merged.get(station.market_id)
        if previous is not None:
            if station.services_at <= previous.services_at:
                continue
            station = replace(station, max_pad=station.max_pad or previous.max_pad)
        merged[station.market_id] = station
    hidden = dict.fromkeys(("carrier", "pad", "radius", "no_coords"), 0)
    stations = []
    for station in merged.values():
        reason = _hidden_reason(station, query)
        if reason:
            hidden[reason] += 1
        else:
            stations.append(station)
    return sorted(stations, key=_order)[:query.limit], hidden, len(stations)


def services_payload(stations: list[ServiceStation], query: ServiceQuery,
                     hidden: Mapping[str, int], hub_known: int, *, total: int, spansh_asked: bool,
                     spansh_count: int | None, spansh_error: str, now: float) -> dict[str, Any]:
    return {
        "service": query.service,
        "label": SERVICE_LABELS.get(query.service, query.service),
        "query": asdict(query),
        "stations": [dict(asdict(station), age_s=max(0.0, now - station.services_at))
                     for station in stations],
        "total": total,
        "hidden": dict(hidden),
        "hub_known": hub_known,
        "spansh": {"asked": spansh_asked, "count": spansh_count, "error": spansh_error},
    }
