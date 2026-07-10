from dataclasses import dataclass


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
class InGameRoute:
    waypoints: tuple[RouteWaypoint, ...]
    total_ly: float
    total_jumps: int
    neutron_count: int
    timestamp: str
