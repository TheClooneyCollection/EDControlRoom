"""Pure ranking of current market routes against a pilot's selected pair."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass(frozen=True)
class RouteRecommendSettings:
    enabled: bool = True
    check_every_s: float = 300
    max_route_ly: float = 100
    min_gain: float = 0.15
    min_gain_cr_h: float = 20_000_000
    list_cap: int = 10
    tts_gap_s: float = 300
    deliver_to_peers: bool = False


@dataclass(frozen=True)
class BaselineEstimate:
    cr_h: float | None
    source: str
    missing: tuple[str, ...]


@dataclass(frozen=True)
class RouteRecommendations:
    routes: list[dict[str, Any]]
    below_threshold: int
    name_unknown: int
    baseline_cr_h: float | None
    baseline_source: str
    generated_at: float
    baseline_missing: tuple[str, ...] = ()
    searched_limit: int = 200

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["baseline_missing"] = list(self.baseline_missing)
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> RouteRecommendations:
        return cls(
            routes=deepcopy(list(payload["routes"])),
            below_threshold=int(payload["below_threshold"]),
            name_unknown=int(payload["name_unknown"]),
            baseline_cr_h=payload["baseline_cr_h"],
            baseline_source=str(payload["baseline_source"]),
            generated_at=float(payload["generated_at"]),
            baseline_missing=tuple(payload.get("baseline_missing", ())),
            searched_limit=int(payload.get("searched_limit", 200)),
        )


def _name(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _pair(route: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(((_name(route[f"{end}_system"]), _name(route[f"{end}_station"]))
                         for end in ("from", "to"))))


def _row_pair(row: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((_name(row[end]["system"]), _name(row[end]["station"]))
                        for end in ("station_1", "station_2")))


def route_key(trade_route: Mapping[str, Any]) -> str:
    """Identify both trades, independent of display case or round-trip direction."""
    endpoints = [(_name(trade_route[f"{end}_system"]), _name(trade_route[f"{end}_station"]),
                  _name(trade_route.get(commodity)))
                 for end, commodity in (("from", "source_buy_commodity"), ("to", "target_buy_commodity"))]
    return json.dumps(sorted(endpoints), ensure_ascii=False, separators=(",", ":"))


def recommend(
    search_result: Mapping[str, Any], *, selected_route: Mapping[str, Any] | None,
    estimate_baseline: Callable[[Mapping[str, Any]], BaselineEstimate],
    settings: RouteRecommendSettings, generated_at: float,
) -> RouteRecommendations:
    rows = search_result["routes"]
    selected_pair = _pair(selected_route) if selected_route is not None else None
    baseline = BaselineEstimate(None, "none", ())
    if selected_route is not None:
        match = next((row for row in rows if _row_pair(row) == selected_pair), None)
        baseline = (BaselineEstimate(float(match["profit_per_hour"]), "search", ())
                    if match is not None else estimate_baseline(selected_route))

    qualifying = []
    below_threshold = name_unknown = 0
    for row in rows:
        if selected_pair is not None and _row_pair(row) == selected_pair:
            continue
        cr_h = row["profit_per_hour"]
        if baseline.cr_h is not None and (
            cr_h < baseline.cr_h * (1 + settings.min_gain)
            or cr_h - baseline.cr_h < settings.min_gain_cr_h
        ):
            below_threshold += 1
        elif row["trade_route"] is None:
            name_unknown += 1
        else:
            qualifying.append({**deepcopy(row), "key": route_key(row["trade_route"])})
    qualifying.sort(key=lambda row: row["profit_per_hour"], reverse=True)
    return RouteRecommendations(
        routes=qualifying[:settings.list_cap], below_threshold=below_threshold,
        name_unknown=name_unknown, baseline_cr_h=baseline.cr_h,
        baseline_source=baseline.source, generated_at=generated_at,
        baseline_missing=baseline.missing,
    )
