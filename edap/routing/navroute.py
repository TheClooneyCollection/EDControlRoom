import json
import math
from pathlib import Path

from edap.routing.types import InGameMetadata, Route, RouteWaypoint


def parse_navroute_json(text: str) -> Route:
    data = json.loads(text)
    if "Route" not in data:
        raise ValueError("missing top-level Route key")
    raw = data["Route"]
    if not raw:
        raise ValueError("Route is empty")

    waypoints: list[RouteWaypoint] = []
    for i, entry in enumerate(raw):
        if "StarPos" not in entry or len(entry["StarPos"]) != 3:
            raise ValueError(f"missing or invalid StarPos at index {i}")
        x, y, z = entry["StarPos"]
        star_class = entry.get("StarClass") or None
        neutron_boost = star_class == "N"
        if i == 0:
            ly = 0.0
            jumps = 0
        else:
            prev = waypoints[-1]
            ly = math.sqrt((x - prev.x) ** 2 + (y - prev.y) ** 2 + (z - prev.z) ** 2)
            jumps = 1
        waypoints.append(
            RouteWaypoint(
                system=entry["StarSystem"],
                star_class=star_class,
                neutron_boost=neutron_boost,
                x=x,
                y=y,
                z=z,
                ly_from_prev=ly,
                jumps_from_prev=jumps,
            )
        )

    total_ly = sum(w.ly_from_prev for w in waypoints)
    total_jumps = len(waypoints) - 1
    neutron_count = sum(1 for w in waypoints if w.star_class == "N")
    return Route(
        waypoints=tuple(waypoints),
        total_ly=total_ly,
        total_jumps=total_jumps,
        neutron_count=neutron_count,
        source="in_game",
        source_system=waypoints[0].system,
        destination_system=waypoints[-1].system,
        metadata=InGameMetadata(timestamp=data.get("timestamp", "")),
    )


def read_navroute(path: Path) -> Route:
    return parse_navroute_json(path.read_text(encoding="utf-8"))
