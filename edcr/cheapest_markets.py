"""Cheapest markets for a commodity: hub store query merged with Spansh rows."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import closing
from dataclasses import asdict, dataclass, replace
import math
from pathlib import Path
import sqlite3
import statistics
import time
from typing import Any

from edcr.recent_markets import commodity_key

PAD_ORDER = {"S": 1, "M": 2, "L": 3}


@dataclass(frozen=True)
class CheapestQuery:
    commodity: str  # EDDN symbol, lower case: "tritium"
    reference_system: str  # "" = no distance column and no radius
    radius_ly: float | None  # None = galaxy-wide
    min_supply: int
    pad: str  # "S" | "M" | "L": the smallest pad the ship can use
    max_age_hours: float
    include_carriers: bool
    use_spansh: bool
    limit: int  # 50


@dataclass(frozen=True)
class MarketOffer:
    source: str  # "hub" | "spansh"
    market_id: int
    system_name: str
    station_name: str
    station_type: str  # "" when unknown
    is_carrier: bool
    max_pad: str  # "S" | "M" | "L" | "" unknown
    dist_ls: float | None
    distance_ly: float | None  # None when no reference system
    buy_price: int
    supply: int
    updated_at: float  # epoch seconds
    suspect_price: bool  # carrier price under 10% of the station median


@dataclass(frozen=True)
class CheapestResult:
    offers: list[MarketOffer]
    hidden: dict[str, int]
    spansh_count: int | None
    spansh_error: str


class UnknownSystemError(ValueError):
    """An unknown reference with Spansh disabled; HTTP callers map this to 404."""


def parse_cheapest_query(params: Mapping[str, str], *, current_system: str,
                         cargo_capacity: int, ship_pad: str) -> CheapestQuery:
    """Resolve URL parameters against the viewed ship; reject malformed filters."""
    commodity = commodity_key(params.get("commodity", "").strip())
    if not commodity:
        raise ValueError("commodity is required")
    system = params.get("system", current_system).strip()
    pad = params.get("pad", ship_pad).strip().upper()
    if pad not in PAD_ORDER:
        raise ValueError("pad must be S, M or L")
    radius_text = params.get("radius_ly", "100").strip()
    radius = _number("radius_ly", radius_text) if radius_text else None
    age = _number("max_age_hours", params.get("max_age_hours", "168"))
    try:
        supply = int(params.get("min_supply", str(cargo_capacity)))
    except ValueError:
        raise ValueError("min_supply must be a non-negative integer") from None
    if supply < 0:
        raise ValueError("min_supply must be a non-negative integer")
    return CheapestQuery(commodity, system, radius if system else None, supply, pad, age,
                         _toggle(params, "carriers", "0"), _toggle(params, "spansh", "1"), 50)


def _number(name: str, value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise ValueError(f"{name} must be a finite non-negative number") from None
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return number


def _toggle(params: Mapping[str, str], name: str, default: str) -> bool:
    value = params.get(name, default).strip()
    if value not in {"0", "1"}:
        raise ValueError(f"{name} must be 0 or 1")
    return value == "1"


def query_hub_store(db: Path, query: CheapestQuery, *, now: float) -> tuple[list[MarketOffer], dict[str, int]]:
    """Read all selling rows before filtering so each exclusion has one reason.

    UnknownSystemError maps to HTTP 404. With Spansh enabled an unknown reference
    leaves hub distances unknown and disables its radius filter. Missing destination
    coordinates fail an active radius filter. No limit is applied before merging.
    """
    hidden = dict.fromkeys(("carrier", "pad", "supply", "age", "radius"), 0)
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        reference = None
        if query.reference_system:
            reference = connection.execute(
                "SELECT x, y, z FROM system WHERE name = ? COLLATE NOCASE "
                "ORDER BY updated_at DESC LIMIT 1", (query.reference_system,),
            ).fetchone()
            if reference is None and not query.use_spansh:
                raise UnknownSystemError(f"Unknown system: {query.reference_system}")
        rows = connection.execute(
            "SELECT m.market_id, m.system_name, m.station_name, m.is_carrier, m.updated_at, "
            "p.buy, p.supply, COALESCE(s.type, ''), COALESCE(s.max_pad, ''), s.dist_ls, "
            "y.x, y.y, y.z FROM price p JOIN market m USING (market_id) "
            "LEFT JOIN station s USING (market_id) "
            "LEFT JOIN system y ON y.address = (SELECT address FROM system "
            "WHERE name = m.system_name COLLATE NOCASE ORDER BY updated_at DESC LIMIT 1) "
            "WHERE p.commodity = ? AND p.supply > 0", (query.commodity,),
        ).fetchall()
    candidates = []
    for mid, system, station, carrier, updated, buy, supply, kind, pad, arrival, x, y, z in rows:
        distance = math.dist(reference, (x, y, z)) if reference is not None and x is not None else None
        candidates.append(MarketOffer("hub", mid, system, station, kind, bool(carrier), pad,
                                      arrival, distance, buy, supply, updated, False))
    offers = []
    for offer in _flag_prices(candidates):
        reason = ""
        if offer.is_carrier and not query.include_carriers:
            reason = "carrier"
        elif offer.max_pad and PAD_ORDER[offer.max_pad] < PAD_ORDER[query.pad]:
            reason = "pad"
        elif offer.supply < query.min_supply:
            reason = "supply"
        elif offer.updated_at < now - query.max_age_hours * 3600:
            reason = "age"
        elif reference is not None and query.radius_ly is not None and (
            offer.distance_ly is None or offer.distance_ly > query.radius_ly
        ):
            reason = "radius"
        if reason:
            hidden[reason] += 1
        else:
            offers.append(offer)
    return sorted(offers, key=_offer_order), hidden


def _offer_order(offer: MarketOffer) -> tuple[int, float, int]:
    return (offer.buy_price, offer.distance_ly if offer.distance_ly is not None else math.inf, offer.market_id)


def _flag_prices(offers: list[MarketOffer]) -> list[MarketOffer]:
    prices = [offer.buy_price for offer in offers if not offer.is_carrier]
    threshold = statistics.median(prices) * 0.1 if prices else 0
    return [replace(offer, suspect_price=offer.is_carrier and
                    (offer.suspect_price or offer.buy_price < threshold)) for offer in offers]


def merge_offers(hub: list[MarketOffer], spansh: list[MarketOffer], query: CheapestQuery) -> list[MarketOffer]:
    """Newest market snapshot wins; hub wins ties and supplies missing pad facts."""
    merged = {offer.market_id: offer for offer in hub}
    hub_pads = {offer.market_id: offer.max_pad for offer in hub}
    for offer in spansh:
        previous = merged.get(offer.market_id)
        if previous is None or offer.updated_at > previous.updated_at:
            merged[offer.market_id] = replace(offer, max_pad=offer.max_pad or hub_pads.get(offer.market_id, ""))
    return sorted(_flag_prices(list(merged.values())), key=_offer_order)[:query.limit]


def cheapest_payload(result: CheapestResult, query: CheapestQuery, display_name: str) -> dict[str, Any]:
    now = time.time()
    return {
        "commodity": query.commodity,
        "name": display_name,
        "query": asdict(query),
        "offers": [dict(asdict(offer), age_s=max(0.0, now - offer.updated_at)) for offer in result.offers],
        "hidden": dict(result.hidden),
        "spansh": {"asked": query.use_spansh, "count": result.spansh_count, "error": result.spansh_error},
    }
