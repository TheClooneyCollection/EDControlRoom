from __future__ import annotations

from typing import Literal


RoutineStopMode = Literal["toggle", "after_run", "now"]


def normalize_routine_stop_mode(value: object) -> RoutineStopMode:
    if value in {"after_run", "now"}:
        return value
    return "toggle"
