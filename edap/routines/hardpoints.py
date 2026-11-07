"""Shared hardpoint interlock for routine-driven FSD engagement."""
from __future__ import annotations

import math
from typing import Callable

from edap.actions import ActionDispatchResult
from edap.routines._base import RoutineResult
from edap.routines.callbacks import ProgressCallback
from edap.status import ShipStatus


def retract_hardpoints_before_jump(
    *,
    read_status_fn: Callable[[], ShipStatus | None],
    toggle_fn: Callable[[], ActionDispatchResult],
    timeout_s: float,
    time_fn: Callable[[], float],
    sleeper: Callable[[float], None],
    progress_fn: ProgressCallback,
) -> RoutineResult | None:
    """Retract known deployed hardpoints; warn and continue if status is unavailable."""
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("hardpoints timeout must be positive and finite")

    def snapshot() -> ShipStatus | None:
        try:
            return read_status_fn()
        except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
            # Status.json may be briefly empty or incomplete while Elite writes it.
            return None

    def failure(reason: str) -> RoutineResult:
        return RoutineResult(
            action="RetractHardpoints",
            dispatch=ActionDispatchResult(action="DeployHardpointToggle", status="error", reason=reason),
        )

    status = snapshot()
    if status is not None and not status.flags.hardpoints_deployed:
        return None
    deadline = time_fn() + timeout_s
    toggles = 0
    dispatch_reason = ""
    while True:
        if status is not None and not status.flags.hardpoints_deployed:
            return None
        now = time_fn()
        if status is not None and (toggles == 0 or (now >= deadline and toggles < 2)):
            progress_fn(f"Retracting hardpoints before FSD engage (attempt {toggles + 1}/2)...")
            dispatch = toggle_fn()
            if dispatch.status != "ok":
                dispatch_reason = dispatch.reason or dispatch.status
                progress_fn(f"Warning: hardpoint retraction dispatch failed: {dispatch_reason}")
            toggles += 1
            deadline = time_fn() + timeout_s
        elif now >= deadline:
            if status is None:
                progress_fn("Warning: cannot read hardpoint state from Status.json; continuing FSD engage without confirmation.")
                return None
            reason = "Hardpoints remain deployed after two retraction attempts"
            if dispatch_reason:
                reason += f" ({dispatch_reason})"
            return failure(reason)
        sleeper(min(0.1, max(0.0, deadline - time_fn())))
        status = snapshot()
