"""Small local-day cache for the TUI's persisted haul history line."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from edap.haul_history import RunTotals, load_runs, parse_window, summarize


class TodayHaulCache:
    def __init__(self) -> None:
        self._date: str | None = None
        self._totals: RunTotals | None = None

    def invalidate(self) -> None:
        self._date = None

    def current(self, path: Path, *, now: datetime) -> RunTotals | None:
        day = now.date().isoformat()
        if day != self._date:
            self._date = day
            try:
                rows, skipped = load_runs(path)
                since, until, _ = parse_window("today", now)
                self._totals = summarize(rows, since, until, skipped_lines=skipped).all_in
            except (OSError, ValueError):
                self._totals = None
        return self._totals
