from edcr.routines._base import (
    RoutineResult,
    SupportsDockingControls,
    SupportsEscapeControls,
    SupportsGalaxyMapControls,
    SupportsRoutineControls,
    SupportsJumpControls,
    SupportsMarketControls,
    SupportsPollEvents,
    SupportsSetSpeedZero,
    SupportsStationMenuControls,
    SupportsUndockControls,
)
from edcr.routines.escape import escape_mass_lock
from edcr.routines.docking import (
    dock,
    docking_request_sequence,
    station_refuel_menu,
    station_refuel_menu_sequence,
    undock,
)
from edcr.routines.galaxy_map import set_gal_map_destination
from edcr.routines.haul_multi_leg import multi_leg_haul
from edcr.routines.haul_two_way import haul_loop_two_way
from edcr.routines.jump import jump
from edcr.routines.market import market_buy, market_sell
from edcr.routines.throttle import auto_zero_throttle_on_arrival, set_speed_zero_then_wait
from edcr.routines.travel import travel_to_station

haul_loop = haul_loop_two_way

__all__ = [
    "RoutineResult",
    "SupportsDockingControls",
    "SupportsEscapeControls",
    "SupportsGalaxyMapControls",
    "SupportsRoutineControls",
    "SupportsJumpControls",
    "SupportsMarketControls",
    "SupportsPollEvents",
    "SupportsSetSpeedZero",
    "SupportsStationMenuControls",
    "SupportsUndockControls",
    "auto_zero_throttle_on_arrival",
    "dock",
    "escape_mass_lock",
    "docking_request_sequence",
    "haul_loop",
    "multi_leg_haul",
    "haul_loop_two_way",
    "jump",
    "market_buy",
    "market_sell",
    "set_gal_map_destination",
    "set_speed_zero_then_wait",
    "station_refuel_menu",
    "station_refuel_menu_sequence",
    "undock",
    "travel_to_station",
]
