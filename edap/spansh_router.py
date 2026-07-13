from __future__ import annotations

import time

import httpx

from edap.routing.types import Route, RouteWaypoint, SpanshMetadata


def parse_spansh_result(payload: dict) -> Route:
    """Parse a completed Spansh /api/results/<job> response into a Route."""
    if payload.get("state") != "completed":
        raise ValueError(f"payload state is not completed: {payload.get('state')!r}")
    try:
        result = payload["result"]
        params = payload["parameters"]
        system_jumps = result["system_jumps"]
    except KeyError as exc:
        raise ValueError(f"malformed Spansh payload: missing key {exc}") from exc

    waypoints = tuple(
        RouteWaypoint(
            system=hop["system"],
            star_class=None,
            neutron_boost=hop["neutron_star"],
            x=hop["x"],
            y=hop["y"],
            z=hop["z"],
            ly_from_prev=hop["distance_jumped"],
            jumps_from_prev=hop["jumps"],
        )
        for hop in system_jumps
    )

    total_ly = sum(hop["distance_jumped"] for hop in system_jumps)
    total_jumps = sum(hop["jumps"] for hop in system_jumps)
    neutron_count = sum(1 for hop in system_jumps if hop["neutron_star"])
    galaxy_map_visits = len(system_jumps) - 1

    return Route(
        waypoints=waypoints,
        total_ly=total_ly,
        total_jumps=total_jumps,
        neutron_count=neutron_count,
        source="spansh",
        source_system=result["source_system"],
        destination_system=result["destination_system"],
        metadata=SpanshMetadata(
            efficiency=int(result["efficiency"]),
            supercharge_multiplier=int(params["supercharge_multiplier"]),
            galaxy_map_visits=galaxy_map_visits,
        ),
    )


def plot_route(
    *,
    source_system: str,
    destination_system: str,
    range_ly: float,
    efficiency: int = 60,
    supercharge_multiplier: int = 4,
    base_url: str = "https://spansh.co.uk",
    poll_interval_s: float = 1.0,
    timeout_s: float = 60.0,
    client: httpx.Client | None = None,
) -> Route:
    """Submit a route to Spansh, poll until completed, and return a Route."""
    owned = client is None
    if owned:
        client = httpx.Client()
    try:
        response = client.post(
            f"{base_url}/api/route",
            data={
                "from": source_system,
                "to": destination_system,
                "range": str(range_ly),
                "efficiency": str(efficiency),
                "supercharge_multiplier": str(supercharge_multiplier),
            },
        )
        response.raise_for_status()
        job = response.json()["job"]

        deadline = time.monotonic() + timeout_s
        while True:
            result_response = client.get(f"{base_url}/api/results/{job}")
            result_response.raise_for_status()
            payload = result_response.json()
            state = payload.get("state")
            if state == "completed":
                return parse_spansh_result(payload)
            if state not in ("started", "queued"):
                raise RuntimeError(f"Spansh returned unexpected state: {state!r}")
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Spansh route did not complete within {timeout_s}s")
            time.sleep(poll_interval_s)
    finally:
        if owned:
            client.close()
