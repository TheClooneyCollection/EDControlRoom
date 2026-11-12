from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RouteWaypoint:
    system: str
    star_class: str | None
    neutron_boost: bool
    x: float
    y: float
    z: float
    ly_from_prev: float
    jumps_from_prev: int


@dataclass(frozen=True)
class InGameMetadata:
    timestamp: str


@dataclass(frozen=True)
class SpanshMetadata:
    efficiency: int
    supercharge_multiplier: int
    galaxy_map_visits: int


RouteMetadata = InGameMetadata | SpanshMetadata | None
RouteSource = Literal["in_game", "spansh", "user"]


@dataclass(frozen=True)
class Route:
    waypoints: tuple[RouteWaypoint, ...]
    total_ly: float
    total_jumps: int
    neutron_count: int
    source: RouteSource
    source_system: str
    destination_system: str
    metadata: RouteMetadata = None
