"""Changed-input scheduling for the hub-owned recommendation search."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from edcr.eddn.routes import TimeModel
from edcr.eddn.store import EddnStoreCounts
from edcr.route_recommend import RouteRecommendations, RouteRecommendSettings


@dataclass(frozen=True)
class RecommendationInputs:
    node_id: str
    current_system: str
    ship_id: int | None
    capacity: int
    laden_jump_range_ly: float | None
    selected_route: dict[str, Any] | None
    search_defaults: dict[str, str]
    time_model: TimeModel
    connection: str


class RecommendationLoop:
    def __init__(self, *, settings: RouteRecommendSettings, time_fn: Callable[[], float],
                 store_counts: Callable[[], EddnStoreCounts],
                 node_inputs: Callable[[], list[RecommendationInputs]],
                 run_query: Callable[[RecommendationInputs, float], RouteRecommendations],
                 deliver: Callable[[str, RouteRecommendations], bool], log: Callable[[str], None]) -> None:
        self._settings, self._time, self._counts = settings, time_fn, store_counts
        self._inputs, self._query, self._deliver, self._log = node_inputs, run_query, deliver, log
        self._last_check: float | None = None
        self._done: dict[str, tuple[float | None, RecommendationInputs]] = {}

    def check(self) -> None:
        now = self._time()
        if not self._settings.enabled or (self._last_check is not None and now - self._last_check < self._settings.check_every_s):
            return
        self._last_check = now
        newest = self._counts().newest_market_at
        nodes = self._inputs()
        active = {node.node_id for node in nodes}
        self._done = {key: value for key, value in self._done.items() if key in active}
        for node in nodes:
            stamp = (newest, node)
            if self._done.get(node.node_id) == stamp:
                continue
            try:
                result = self._query(node, now)
                # Input may change while an expensive query runs. Do not deliver gains against an old selection.
                current = next((item for item in self._inputs() if item.node_id == node.node_id), None)
                if current != node:
                    continue
                if self._deliver(node.node_id, result):
                    self._done[node.node_id] = deepcopy(stamp)
            except Exception as exc:
                self._log(f"Route recommendations for {node.node_id} failed: {exc}")
