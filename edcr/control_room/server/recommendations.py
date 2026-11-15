"""Read-only market queries and ship inputs for route recommendations."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import sqlite3
from typing import Any, Mapping
from collections.abc import Callable

from edcr.control_room.server.route_inputs import with_ship_laden_range
from edcr.eddn.route_query import parse_route_query, run_route_query
from edcr.eddn.routes import TimeModel
from edcr.recent_markets import commodity_key
from edcr.route_recommend import BaselineEstimate, RouteRecommendations, RouteRecommendSettings, recommend
from edcr.route_recommend_service import RecommendationInputs
from edcr.trade_trip import estimate_trip, gather_facts, route_profit_per_hour, store_lookup


def recommendation_inputs(node_id: str, data: object, *, selected_route: object,
                          search_defaults: dict[str, str], time_model: TimeModel, connection: str) -> RecommendationInputs | None:
    ship = getattr(data, "ship", None)
    capacity = getattr(ship, "cargo_capacity", None)
    if not isinstance(capacity, int) or capacity <= 0:
        return None
    route = asdict(selected_route) if is_dataclass(selected_route) else selected_route
    return RecommendationInputs(node_id, getattr(ship, "system", None) or "", getattr(ship, "ship_id", None),
                                capacity, getattr(ship, "laden_jump_range_ly", None), route,
                                search_defaults, time_model, connection)


def estimate_selected_route(db: sqlite3.Connection, route: Mapping[str, Any], *, capacity: int,
                            laden_range: float, time_model: TimeModel) -> BaselineEstimate:
    """Price the selected commodities today, even if this pair was outside the top 200."""
    facts = [gather_facts(0, route[f"{end}_station"], route[f"{end}_system"], [("store", store_lookup(db))])
             for end in ("from", "to")]
    trip = estimate_trip(*facts, laden_jump_range_ly=laden_range, time_model=time_model)
    missing = list(trip.missing)
    prices = []
    for end in ("from", "to"):
        market = db.execute("SELECT market_id FROM market WHERE station_name=? COLLATE NOCASE AND system_name=? COLLATE NOCASE ORDER BY updated_at DESC LIMIT 1",
                            (route[f"{end}_station"], route[f"{end}_system"])).fetchone()
        prices.append({commodity_key(name): (buy, sell, supply) for name, buy, sell, supply in db.execute(
            "SELECT commodity,buy,sell,supply FROM price WHERE market_id=?", (market[0],))} if market else {})
    profit = 0
    for source, target, field in ((0, 1, "source_buy_commodity"), (1, 0, "target_buy_commodity")):
        name = route.get(field)
        if not name:
            continue
        key = commodity_key(name)
        buy = prices[source].get(key)
        sell = prices[target].get(key)
        if buy is None or sell is None or buy[0] <= 0 or sell[1] <= 0:
            missing.append(f"{name} buy/sell prices")
        else:
            profit += min(capacity, max(0, buy[2])) * (sell[1] - buy[0])
    rate = route_profit_per_hour(profit, trip.trip_s) if not missing else None
    return BaselineEstimate(rate, "store" if rate is not None else "unpriced", tuple(missing))


def query_recommendations(node: RecommendationInputs, *, settings: RouteRecommendSettings,
                          database_file: Path, display_names: dict[str, str], now: float) -> RouteRecommendations:
    params = with_ship_laden_range({"view": "global", "max_route_ly": str(settings.max_route_ly), "limit": "200"}, node)
    query = parse_route_query(params, search_defaults=node.search_defaults, current_system=node.current_system,
                              cargo_capacity=node.capacity)
    result = run_route_query(database_file, query, time_model=node.time_model, display_names=display_names, now=now)
    def baseline(route):
        db = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)
        try:
            return estimate_selected_route(db, route, capacity=query.capacity,
                                           laden_range=query.laden_jump_range_ly, time_model=node.time_model)
        finally:
            db.close()
    return recommend(result, selected_route=node.selected_route, estimate_baseline=baseline,
                     settings=settings, generated_at=now)


class PeerRecommendationInputs:
    """Hub-owned snapshots; missing ship state is logged once until it recovers."""
    def __init__(self, *, nodes: Callable[[], list[dict[str, Any]]],
                 time_model: Callable[[int | None], TimeModel], log: Callable[[str], None]) -> None:
        self._nodes, self._model, self._log = nodes, time_model, log
        self._missing: set[str] = set()

    def collect(self, search_defaults: dict[str, str]) -> list[RecommendationInputs]:
        result = []
        for node in self._nodes():
            if node["local"] or not node["connected"]:
                continue
            state = node.get("state") or {}
            ship = state.get("ship") or {}
            capacity = ship.get("cargo_capacity")
            node_id = node["node_id"]
            if not isinstance(capacity, int) or capacity <= 0:
                if node_id not in self._missing:
                    self._log(f"Route recommendations skip {node_id}: ship hold not available")
                    self._missing.add(node_id)
                continue
            self._missing.discard(node_id)
            result.append(RecommendationInputs(node_id, state.get("current_system") or "", ship.get("id"),
                capacity, ship.get("laden_jump_range_ly"), state.get("selected_route"), search_defaults,
                self._model(ship.get("id")), node.get("connected_since") or ""))
        return result
