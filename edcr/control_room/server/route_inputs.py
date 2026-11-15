"""Use the viewed ship's laden range when a route consumer explicitly requests it."""
from __future__ import annotations

import math
from typing import Any, Mapping


def with_ship_laden_range(params: Mapping[str, str], ship: object) -> dict[str, str]:
    """Explicit query range wins; missing ship data keeps the normal config fallback.

    The caller chooses whether to use ship range. `/routes` does not opt in;
    `/haul` does, and the recommendation runner always calls this helper.
    """
    resolved = dict(params)
    if (resolved.get("laden_jump_range_ly") or "").strip():
        return resolved
    value: Any = ship.get("laden_jump_range_ly") if isinstance(ship, Mapping) else getattr(ship, "laden_jump_range_ly", None)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0:
        resolved["laden_jump_range_ly"] = str(value)
    return resolved
