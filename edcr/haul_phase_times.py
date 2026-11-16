"""Per-direction stage timings, measured on the haul's pause-aware session clock."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

PHASES = ('buy', 'undock', 'depart', 'transit', 'sell')


def session_seconds(stats: Any, now: float | None) -> float:
    if now is not None and stats.session_started_at is not None:
        return max(0.0, now - stats.session_started_at)
    return stats.session_elapsed_s


@dataclass
class PhaseTimes:
    route: tuple[str, ...] = ()
    phase: str | None = None
    direction: int | None = None  # destination station; departing phases name the source station
    started_s: float | None = None
    elapsed_s: float = 0.0
    running: bool = False
    complete_sample: bool = True
    current: dict[str, float] = field(default_factory=dict)
    # key is destination:phase, value is count, total seconds, minimum seconds.
    samples: dict[str, list[float]] = field(default_factory=dict)

    def elapsed(self, clock: float) -> float:
        return self.elapsed_s + (max(0.0, clock - self.started_s) if self.started_s is not None else 0.0)

    def transition(self, phase: str | None, station: int | None, clock: float) -> None:
        if phase not in PHASES or station not in (1, 2):
            if self.running:
                self.elapsed_s = self.elapsed(clock)
                self.started_s = None
                self.running = False
            return
        direction = 3 - station if phase in ('buy', 'undock', 'depart') else station
        if phase == self.phase and direction == self.direction:
            if not self.running:
                self.started_s, self.running = clock, True
            return
        if self.phase is not None:
            elapsed = self.elapsed(clock)
            self.current[self.phase] = elapsed
            if self.running and self.complete_sample:
                key = f'{self.direction}:{self.phase}'
                count, total, minimum = self.samples.get(key, [0, 0.0, elapsed])
                self.samples[key] = [count + 1, total + elapsed, min(minimum, elapsed)]
        if direction != self.direction:
            self.current.clear()
        self.phase, self.direction = phase, direction
        self.started_s, self.elapsed_s, self.running, self.complete_sample = clock, 0.0, True, True

    def snapshot(self, clock: float) -> dict[str, dict[str, float | int | None]]:
        if self.direction is None:
            return {}
        result = {}
        for phase in PHASES:
            count, total, minimum = self.samples.get(f'{self.direction}:{phase}', [0, 0.0, 0.0])
            result[phase] = dict(current_s=self.elapsed(clock) if phase == self.phase else self.current.get(phase),
                                 min_s=minimum if count else None, avg_s=total / count if count else None,
                                 samples=int(count))
        return result

    def reset_session(self) -> None:
        self.samples.clear()
        self.current.clear()
        self.elapsed_s = 0.0
        self.started_s = 0.0 if self.running else None
        # A new session in the middle of a stage is not a full sample.
        self.complete_sample = False

    def checkpoint(self, clock: float) -> dict[str, Any]:
        return dict(route=list(self.route), phase=self.phase, direction=self.direction,
                    elapsed_s=self.elapsed(clock), current=dict(self.current),
                    samples={key: list(value) for key, value in self.samples.items()})

    @classmethod
    def restore(cls, payload: Any) -> PhaseTimes:
        if not isinstance(payload, dict):
            return cls()
        def seconds(value):
            return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0
        route = payload.get('route')
        if not isinstance(route, list) or not all(isinstance(part, str) for part in route):
            return cls()
        result = cls(route=tuple(route), complete_sample=False)
        if payload.get('phase') in PHASES and payload.get('direction') in (1, 2):
            result.phase, result.direction = payload['phase'], payload['direction']
            result.elapsed_s = payload.get('elapsed_s', 0) if seconds(payload.get('elapsed_s')) else 0.0
        current = payload.get('current')
        if isinstance(current, dict):
            result.current = {key: value for key, value in current.items() if key in PHASES and seconds(value)}
        samples = payload.get('samples')
        if isinstance(samples, dict):
            allowed = {f'{direction}:{phase}' for direction in (1, 2) for phase in PHASES}
            for key, value in samples.items():
                if key in allowed and isinstance(value, list) and len(value) == 3 and all(seconds(n) for n in value):
                    count, total, minimum = value
                    if count > 0 and int(count) == count and minimum <= total / count:
                        result.samples[key] = list(value)
        return result
