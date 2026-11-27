"""One price-sorted Spansh station search, with an injectable HTTP boundary."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import math
from typing import Any

import httpx

from edcr.cheapest_markets import CheapestQuery, MarketOffer

PostJson = Callable[[str, dict[str, Any], float], object]
SEARCH_URL = "https://spansh.co.uk/api/stations/search"
NON_CARRIER_TYPES = (
    "Asteroid base", "Coriolis Starport", "Ocellus Starport", "Orbis Starport",
    "Outpost", "Planetary Outpost", "Planetary Port", "Settlement", "Mega ship",
)


def post_json(url: str, body: dict[str, Any], timeout: float) -> object:
    """Production transport; the search supplies a ten-second timeout."""
    response = httpx.post(url, json=body, timeout=timeout)
    response.raise_for_status()
    return response.json()


def spansh_search_body(query: CheapestQuery, commodity_name: str) -> dict[str, Any]:
    """Build static search filters; search_cheapest resolves the age against now."""
    filters: dict[str, Any] = {
        "market": [{"name": commodity_name, "supply": {"comparison": ">=", "value": query.min_supply}}],
    }
    if query.pad == "L":
        filters["has_large_pad"] = {"value": True}
    if not query.include_carriers:
        filters["type"] = {"value": list(NON_CARRIER_TYPES)}
    body: dict[str, Any] = {
        "filters": filters,
        "sort": [{"market_buy_price": [{"name": commodity_name, "direction": "asc"}]}],
        "size": query.limit,
        "page": 0,
    }
    if query.reference_system:
        body["reference_system"] = query.reference_system
        if query.radius_ly is not None:
            filters["distance"] = {"min": 0, "max": query.radius_ly}
    return body


def _number(value: object, field: str, *, integer: bool = False) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Spansh response: {field} must be a number")
    if not math.isfinite(value) or value < 0 or (integer and int(value) != value):
        raise ValueError(f"Spansh response: invalid {field}")
    return int(value) if integer else float(value)


def _text(row: dict[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Spansh response: missing or invalid {field}")
    return value


def _timestamp(value: object) -> float:
    if not isinstance(value, str):
        raise ValueError("Spansh response: invalid market_updated_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError as exc:
        raise ValueError("Spansh response: invalid market_updated_at") from exc


def _offer(row: object, query: CheapestQuery, commodity_name: str) -> MarketOffer:
    if not isinstance(row, dict):
        raise ValueError("Spansh response: station row must be an object")
    market = row.get("market")
    if not isinstance(market, list) or any(not isinstance(item, dict) for item in market):
        raise ValueError("Spansh response: market must be a list of objects")
    matches = [item for item in market if item.get("commodity") == commodity_name]
    if len(matches) != 1:
        raise ValueError(f"Spansh response: expected one market entry for {commodity_name}")
    item = matches[0]
    station_type = _text(row, "type")
    large_pad = row.get("has_large_pad")
    if not isinstance(large_pad, bool):
        raise ValueError("Spansh response: invalid has_large_pad")
    return MarketOffer(
        source="spansh",
        market_id=_number(row.get("market_id"), "market_id", integer=True),
        system_name=_text(row, "system_name"),
        station_name=_text(row, "name"),
        station_type=station_type,
        is_carrier="Carrier" in station_type,
        max_pad="L" if large_pad else "",
        dist_ls=(None if row.get("distance_to_arrival") is None else
                 _number(row["distance_to_arrival"], "distance_to_arrival")),
        distance_ly=(_number(row.get("distance"), "distance") if query.reference_system else None),
        buy_price=_number(item.get("buy_price"), "buy_price", integer=True),
        supply=_number(item.get("supply"), "supply", integer=True),
        updated_at=_timestamp(row.get("market_updated_at")),
        suspect_price=False,
    )


def search_cheapest(query: CheapestQuery, commodity_name: str, post: PostJson,
                    *, now: float) -> tuple[list[MarketOffer], int, int]:
    body = spansh_search_body(query, commodity_name)
    body["filters"]["market_updated_at"] = {
        "comparison": "<=>",
        "value": [datetime.fromtimestamp(now - query.max_age_hours * 3600, timezone.utc).isoformat(),
                  datetime.fromtimestamp(now, timezone.utc).isoformat()],
    }
    response = post(SEARCH_URL, body, 10.0)
    if not isinstance(response, dict):
        raise ValueError("Spansh response: expected an object")
    if "error" in response:
        raise ValueError(f"Spansh error: {response['error']}")
    rows = response.get("results")
    if not isinstance(rows, list):
        raise ValueError("Spansh response: results must be a list")
    count = _number(response.get("count"), "count", integer=True)
    if count < len(rows):
        raise ValueError("Spansh response: count is smaller than the result list")
    offers = []
    skipped = 0
    for row in rows:
        try:
            offers.append(_offer(row, query, commodity_name))
        except (ValueError, OverflowError, OSError):
            skipped += 1
    return offers, int(count), skipped
