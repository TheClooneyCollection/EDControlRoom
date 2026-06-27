from __future__ import annotations

from typing import Any

_CARRIER_STATION_NAMES = {"fleet carrier", "stronghold carrier"}
_CARRIER_STATION_TYPES = {"fleetcarrier"}


def is_carrier_station(*, station_name: object = None, station_type: object = None) -> bool:
    normalized_name = str(station_name or "").strip().lower()
    normalized_type = str(station_type or "").strip().lower()
    return normalized_name in _CARRIER_STATION_NAMES or normalized_type in _CARRIER_STATION_TYPES


def is_manual_launch_control_resumed_event(
    event: dict[str, Any],
    *,
    station_name: object = None,
    station_type: object = None,
) -> bool:
    # Stronghold/Fleet Carrier launches can hand control back with Exploration
    # instead of the usual NoTrack station-clear cue after Undocked.
    return (
        event.get("event") == "Music"
        and event.get("MusicTrack") == "Exploration"
        and is_carrier_station(station_name=station_name, station_type=station_type)
    )
