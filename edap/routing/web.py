from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from edap.routing.comparison import RouteComparison, compare
from edap.routing.navroute import read_navroute
from edap.routing.types import InGameRoute
from edap.spansh_router import SpanshRoute, parse_spansh_result, plot_route

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "routing"

_FIXTURE_PAIRS: dict[str, tuple[str, str]] = {
    "hd232819_xinca_normal": (
        "navroute_hd232819_xinca.json",
        "spansh_hd232819_xinca_normal_completed.json",
    ),
    "hd232819_xinca_overcharge": (
        "navroute_hd232819_xinca.json",
        "spansh_hd232819_xinca_overcharge_completed.json",
    ),
}


def available_fixtures() -> tuple[str, ...]:
    return tuple(_FIXTURE_PAIRS.keys())


def load_fixture_comparison(name: str, *, title: str = "Commander") -> RouteComparison:
    if name not in _FIXTURE_PAIRS:
        raise ValueError(f"unknown fixture: {name}")
    navroute_file, spansh_file = _FIXTURE_PAIRS[name]
    in_game = read_navroute(_FIXTURES_DIR / navroute_file)
    spansh = _load_spansh_fixture(_FIXTURES_DIR / spansh_file)
    return compare(in_game, spansh, title=title)


def _load_spansh_fixture(path: Path) -> SpanshRoute:
    with path.open() as fh:
        return parse_spansh_result(json.load(fh))


def build_live_comparison(
    *,
    journal_dir: Path,
    source_system: str,
    destination_system: str,
    range_ly: float,
    efficiency: int = 60,
    supercharge_multiplier: int = 4,
    title: str = "Commander",
    plot_route_fn: Callable[..., SpanshRoute] = plot_route,
    read_navroute_fn: Callable[[Path], InGameRoute] = read_navroute,
) -> RouteComparison:
    in_game = read_navroute_fn(journal_dir / "NavRoute.json")
    spansh = plot_route_fn(
        source_system=source_system,
        destination_system=destination_system,
        range_ly=range_ly,
        efficiency=efficiency,
        supercharge_multiplier=supercharge_multiplier,
    )
    return compare(in_game, spansh, title=title)


def comparison_to_payload(comparison: RouteComparison) -> dict:
    return {
        "verdict": comparison.verdict,
        "jumps_delta": comparison.jumps_delta,
        "neutron_delta": comparison.neutron_delta,
        "tts_phrase": comparison.tts_phrase,
        "in_game": _in_game_payload(comparison.in_game),
        "spansh": _spansh_payload(comparison.spansh),
    }


def _in_game_payload(route: InGameRoute) -> dict:
    return {
        "total_ly": route.total_ly,
        "total_jumps": route.total_jumps,
        "neutron_count": route.neutron_count,
        "timestamp": route.timestamp,
        "waypoints": [asdict(w) for w in route.waypoints],
    }


def _spansh_payload(route: SpanshRoute) -> dict:
    return {
        "total_ly": route.total_ly,
        "total_jumps": route.total_jumps,
        "neutron_count": route.neutron_count,
        "galaxy_map_visits": route.galaxy_map_visits,
        "source_system": route.source_system,
        "destination_system": route.destination_system,
        "efficiency": route.efficiency,
        "supercharge_multiplier": route.supercharge_multiplier,
        "waypoints": [asdict(w) for w in route.waypoints],
    }
