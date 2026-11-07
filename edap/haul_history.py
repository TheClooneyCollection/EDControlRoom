"""Durable, append-only two-way haul history (schema 1).

Legs describe station visits, with individual buys/sells to preserve mixed cargo.
Raw events retain any additional journal fields. Duration follows the live haul
clock (excludes pauses); timestamps identify journal boundaries independently.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from edap.control_room.models import HaulStats
from edap.version import get_current_version

WARNING_IDS = frozenset({"haul_buy_still_short", "haul_top_up_unaffordable", "market_buy_none_available"})


def utc_timestamp(value: object) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    return datetime.now(timezone.utc).isoformat()


def append_run(path: Path, row: dict[str, Any], log: Callable[[str], None]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # A crashed previous append may have left a torn final line.
        prefix = ""
        if path.exists() and path.stat().st_size:
            with path.open("rb") as existing:
                existing.seek(-1, os.SEEK_END)
                if existing.read(1) != b"\n":
                    prefix = "\n"
        line = json.dumps(row, ensure_ascii=False, allow_nan=False)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(prefix + line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return True
    except (OSError, ValueError, TypeError) as exc:
        log(f"Warning: failed to append haul history to {path}: {exc}; retained for retry.")
        return False


def load_runs(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Return unique rows and the number of invalid/torn lines skipped."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    skipped = 0
    if not path.exists():
        return rows, skipped
    with path.open("rb") as handle:
        for line in handle:
            try:
                row = json.loads(line)
                if (not isinstance(row, dict) or row.get("schema") != 1
                        or row.get("kind") != "two_way"
                        or row.get("status") not in {"completed", "aborted"}):
                    raise ValueError("Invalid run")
                key = (row["started_at"], row["ended_at"], row["route"]["station_1"])
                if not all(isinstance(item, str) for item in key):
                    raise ValueError("Invalid run identity")
                if key not in seen:
                    rows.append(row)
                    seen.add(key)
            except (ValueError, KeyError, TypeError, UnicodeError):
                skipped += 1
    return rows, skipped


def record_event(stats: HaulStats, event: dict[str, Any], station: str, system: str) -> None:
    name = event.get("event")
    if stats.current_run is None:
        if name not in {"MarketBuy", "MarketSell"} and not (
            name == "Undocked" and station.casefold() == stats.station_1.casefold()
        ):
            return
        timestamp = utc_timestamp(event.get("timestamp"))
        stats.current_run = {
            "schema": 1, "kind": "two_way", "started_at": timestamp,
            "ended_at": timestamp, "duration_s": 0.0,
            "route": {"station_1": stats.station_1, "station_2": stats.station_2,
                      "system_1": None, "system_2": None},
            "legs": [], "events": [], "cost": 0, "revenue": 0, "profit": 0,
            "expected_profit": stats.expected_profit_per_trip, "profit_delta": None,
            "top_ups": 0, "warnings": [], "app_version": get_current_version(),
            "phase": None,
        }
    row = stats.current_run
    row["ended_at"] = utc_timestamp(event.get("timestamp"))
    for index in (1, 2):
        if station.casefold() == row["route"][f"station_{index}"].casefold() and system:
            row["route"][f"system_{index}"] = system
    if name not in {"MarketBuy", "MarketSell", "Docked", "Undocked"}:
        return
    row["events"].append(dict(event))
    legs = row["legs"]
    if not legs or legs[-1]["station"].casefold() != station.casefold() or legs[-1]["completed"]:
        legs.append({"station": station, "system": system or None, "buys": [], "sells": [],
                     "market_buy_events": 0, "completed": False})
    leg = legs[-1]
    if name == "Undocked":
        leg["completed"] = True
    elif name == "MarketBuy":
        if leg["market_buy_events"]:
            row["top_ups"] += 1
        leg["market_buy_events"] += 1
        cost = int(event.get("TotalCost", 0) or 0)
        leg["buys"].append({"commodity": event.get("Type"), "tons": event.get("Count"), "cost": cost})
        row["cost"] += cost
    elif name == "MarketSell":
        revenue = int(event.get("TotalSale", 0) or 0)
        leg["sells"].append({"commodity": event.get("Type"), "tons": event.get("Count"), "revenue": revenue})
        row["revenue"] += revenue
    row["profit"] = row["revenue"] - row["cost"]


def snapshot_duration(stats: HaulStats, now: float) -> None:
    if stats.current_run is None or not stats.active:
        return
    elapsed = stats.current_run_elapsed_s or 0.0
    if stats.current_run_started_at is not None and not stats.docked_back_at_station_1:
        elapsed = max(0.0, now - stats.current_run_started_at)
    stats.current_run["duration_s"] = elapsed


def close_run(stats: HaulStats, status: str, reason: str, ended_at: str | None, now: float) -> None:
    snapshot_duration(stats, now)
    row = stats.current_run
    if row is None:
        return
    row["status"] = status
    if ended_at is not None:
        row["ended_at"] = utc_timestamp(ended_at)
    expected = row["expected_profit"]
    row["profit_delta"] = row["profit"] - expected if expected is not None else None
    if status == "aborted":
        row["reason"] = reason
    else:
        row.pop("phase", None)
        if row["legs"]:
            row["legs"][-1]["completed"] = True
    stats.pending_runs.append(row)
    stats.current_run = None
