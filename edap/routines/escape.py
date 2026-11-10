from __future__ import annotations

from pathlib import Path
from time import sleep
from typing import Callable

from edap.actions import ActionDispatchResult
from edap.routines._base import RoutineResult, SupportsEscapeControls
from edap.routines.callbacks import ProgressCallback
from edap.status import read_status

MASS_LOCK_POLL_S = 0.25
MASS_LOCK_STATUS_READ_ATTEMPTS = 8
MASS_LOCK_CLEAR_CONFIRMATIONS = 2


def read_mass_locked(journal_dir: Path) -> bool | None:
    try:
        status = read_status(journal_dir, require_flags=True)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
        # Status.json may be briefly empty or incomplete while Elite writes it.
        return None
    return None if status is None else status.flags.fsd_mass_locked


def _read_mass_locked(journal_dir: Path, *, sleeper: Callable[[float], None]) -> bool | None:
    for attempt in range(MASS_LOCK_STATUS_READ_ATTEMPTS):
        mass_locked = read_mass_locked(journal_dir)
        if mass_locked is not None:
            return mass_locked
        if attempt + 1 < MASS_LOCK_STATUS_READ_ATTEMPTS:
            sleeper(MASS_LOCK_POLL_S)
    return None


def escape_mass_lock(
    controls: SupportsEscapeControls,
    *,
    journal_dir: Path,
    boost_delay_s: float = 5.0,
    step_delay_s: float = 0.3,
    sleeper: Callable[[float], None] = sleep,
    progress_fn: ProgressCallback,
) -> RoutineResult:
    if boost_delay_s < 0:
        raise ValueError("boost_delay_s must be non-negative")
    if step_delay_s < 0:
        raise ValueError("step_delay_s must be non-negative")

    progress_fn("Setting speed 100 to break auto-undock...")
    speed_result = controls.set_speed_full()
    if speed_result.status != "ok":
        progress_fn(f"Warning: SetSpeed100 dispatch failed: {speed_result.reason}")
    if step_delay_s > 0:
        sleeper(step_delay_s)

    boost_count = 0
    last_boost: ActionDispatchResult | None = None
    clear_reads = 0

    while True:
        mass_locked = _read_mass_locked(journal_dir, sleeper=sleeper)
        if mass_locked is None:
            progress_fn("Warning: cannot read mass lock from Status.json; continuing without confirmation.")
            break
        if not mass_locked:
            # A single clear read once let the FSD engage while still mass locked, so confirm it.
            clear_reads += 1
            if clear_reads >= MASS_LOCK_CLEAR_CONFIRMATIONS:
                break
            sleeper(MASS_LOCK_POLL_S)
            continue
        clear_reads = 0
        progress_fn("FSD mass locked -- boosting away...")
        last_boost = controls.boost()
        if last_boost.status != "ok":
            progress_fn(f"Warning: UseBoostJuice dispatch failed: {last_boost.reason}")
        boost_count += 1
        if boost_delay_s > 0:
            sleeper(boost_delay_s)

    dispatch = last_boost or ActionDispatchResult(
        action="EscapeMassLock",
        status="ok",
        reason="not mass locked",
    )
    return RoutineResult(
        action="EscapeMassLock",
        dispatch=dispatch,
        details={"boost_count": boost_count},
    )
