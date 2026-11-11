"""The current ship's laden jump range from its journal `Loadout` (plan 0014 section 5).

`MaxJumpRange` is the unladen range with fuel for one jump. Range scales with 1 / mass, so a full hold
and full tank give `MaxJumpRange × (UnladenMass + one-jump fuel) / (UnladenMass + FuelCapacity.Main + CargoCapacity)`.
`Loadout` has no FSD max fuel per jump, so it comes from the FSD's size and class (standard FSD figures; an SCO
drive of the same size and class is taken to match). An unknown drive uses 0 t, which reads up to ~0.1 Ly short
for a large ship. Every page that wants the current ship's laden range uses `loadout_laden_jump_range`.
"""
from __future__ import annotations

import re
from typing import Any

# FSD max fuel per jump (t) by size, for classes E, D, C, B, A.
_MAX_FUEL_PER_JUMP_T: dict[int, tuple[float, float, float, float, float]] = {
    2: (0.6, 0.6, 0.6, 0.8, 0.9),
    3: (1.2, 1.2, 1.2, 1.5, 1.8),
    4: (2.0, 2.0, 2.0, 2.5, 3.0),
    5: (3.3, 3.3, 3.3, 4.1, 5.0),
    6: (5.3, 5.3, 5.3, 6.6, 8.0),
    7: (8.5, 8.5, 8.5, 10.6, 12.8),
}
_FSD_ITEM = re.compile(r"int_hyperdrive(?:_overcharge)?_size(\d+)_class([1-5])", re.IGNORECASE)


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def fsd_max_fuel_per_jump(item: str) -> float:
    """Max fuel per jump for an FSD module item name; 0 when the drive is not in the table."""
    match = _FSD_ITEM.search(item)
    if match is None:
        return 0.0
    fuel = _MAX_FUEL_PER_JUMP_T.get(int(match.group(1)))
    # The item's class 1..5 is rating E..A.
    return fuel[int(match.group(2)) - 1] if fuel is not None else 0.0


def loadout_laden_jump_range(loadout: dict[str, Any]) -> float | None:
    """Laden range (full hold, full main tank) in Ly, rounded to 2 places; None when an input is missing."""
    max_range = _number(loadout.get("MaxJumpRange"))
    unladen = _number(loadout.get("UnladenMass"))
    cargo = _number(loadout.get("CargoCapacity"))
    fuel_capacity = loadout.get("FuelCapacity")
    tank = _number(fuel_capacity.get("Main")) if isinstance(fuel_capacity, dict) else None
    if max_range is None or unladen is None or cargo is None or tank is None or max_range <= 0 or unladen <= 0:
        return None
    fsd = next((str(module.get("Item", "")) for module in loadout.get("Modules", [])
                if isinstance(module, dict) and module.get("Slot") == "FrameShiftDrive"), "")
    one_jump_fuel = min(tank, fsd_max_fuel_per_jump(fsd))
    return round(max_range * (unladen + one_jump_fuel) / (unladen + tank + cargo), 2)
