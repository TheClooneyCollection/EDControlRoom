"""Durable, append-only two-way haul history (schema 1).

Legs describe station visits, with individual buys/sells to preserve mixed cargo.
Raw events retain any additional journal fields. Since plan 0015 step 3 a row also carries
the ship it was flown in (`ship`: id, type, name, ident, cargo capacity, max and laden jump
range); older rows have no `ship` and stay valid. Duration follows the live haul
clock (excludes pauses); timestamps identify journal boundaries independently.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable

if TYPE_CHECKING:
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
            "partial_start": not (stats.clean_run_active or (
                station.casefold() == stats.station_1.casefold()
                and (name == "Undocked" or (name == "MarketBuy" and stats.waiting_for_station_1_departure))
            )),
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



def abort_run(stats: HaulStats, reason: str, ended_at: str | None, now: float) -> None:
    """Close the in-progress run as aborted, keeping its realized trades in the session profit.

    A clean run tracks its trades in `current_run_profit`; a partial (resumed mid-run) row
    does not, so its recorded profit is added instead.
    """
    row = stats.current_run
    if row is not None and row.get("partial_start"):
        stats.accumulated_profit += row["profit"]
    else:
        stats.accumulated_profit += stats.current_run_profit
        stats.current_run_profit = 0
    close_run(stats, "aborted", reason, ended_at, now)

# Query records are immutable and can be serialized with dataclasses.asdict.
@dataclass(frozen=True)
class RunTotals:
    count: int
    cost: int
    revenue: int
    profit: int
    # Haul clock time of these runs (pauses excluded), so a route's profit per hour can be measured.
    duration_s: float


@dataclass(frozen=True)
class CompletedSummary:
    count: int
    cost: int
    revenue: int
    profit: int
    duration_s: float
    profit_per_hour: float | None
    mean_profit: float | None
    best_profit: int | None
    expected_count: int
    expected_profit: int | None
    expected_actual_profit: int | None
    profit_delta: int | None


@dataclass(frozen=True)
class RouteSummary:
    station_1: str
    system_1: str | None
    station_2: str
    system_2: str | None
    completed: RunTotals
    aborted: RunTotals
    all_in: RunTotals


@dataclass(frozen=True)
class TradeTotals:
    tons_bought: int
    tons_sold: int
    cost: int
    revenue: int


@dataclass(frozen=True)
class CommoditySummary:
    commodity: str
    completed: TradeTotals
    aborted: TradeTotals
    all_in: TradeTotals


@dataclass(frozen=True)
class HaulSummary:
    completed: CompletedSummary
    aborted: RunTotals
    all_in: RunTotals
    # A stop, pause or relaunch splits a run into aborted halves, so only all-in is the real total.
    all_in_duration_s: float
    all_in_profit_per_hour: float | None
    routes: tuple[RouteSummary, ...]
    commodities: tuple[CommoditySummary, ...]
    skipped_lines: int


WINDOW_USAGE = "Usage: stats [today | 48h | 7d | 30d | week | month | all | since YYYY-MM-DD]"
# Elapsed windows, like 48h; Best deal picks between 48h, 7d, 30d and all.
_ELAPSED_WINDOWS = {"48h": timedelta(hours=48), "7d": timedelta(days=7), "30d": timedelta(days=30)}


def parse_window(text: str, now: datetime) -> tuple[datetime | None, datetime, str]:
    """Use now's local timezone for calendar windows; 48h is elapsed time.

    Endpoints are inclusive, with `all` having no lower bound. Callers supply
    an aware local datetime (ZoneInfo retains calendar offsets across DST).
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError(f"{WINDOW_USAGE}; now must include a timezone")
    label = " ".join(text.lower().split()) or "today"
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if label == "today":
        since = midnight
    elif label in _ELAPSED_WINDOWS:
        since = (now.astimezone(timezone.utc) - _ELAPSED_WINDOWS[label]).astimezone(now.tzinfo)
    elif label == "week":
        since = midnight - timedelta(days=now.weekday())
    elif label == "month":
        since = midnight.replace(day=1)
    elif label == "all":
        since = None
    elif re.fullmatch(r"since \d{4}-\d{2}-\d{2}", label):
        try:
            day = date.fromisoformat(label[6:])
        except ValueError as exc:
            raise ValueError(WINDOW_USAGE) from exc
        since = datetime.combine(day, datetime.min.time(), tzinfo=now.tzinfo)
        if since > now:
            raise ValueError(f"{WINDOW_USAGE}; since date cannot be in the future")
    else:
        raise ValueError(WINDOW_USAGE)
    return since, now, label


def _run_totals(rows: list[dict[str, Any]]) -> RunTotals:
    cost = sum(row["cost"] for row in rows)
    revenue = sum(row["revenue"] for row in rows)
    duration = sum(float(row.get("duration_s", 0) or 0) for row in rows)
    return RunTotals(len(rows), cost, revenue, revenue - cost, duration)


def _trade_totals(trades: list[tuple[str, dict[str, Any]]]) -> TradeTotals:
    return TradeTotals(
        tons_bought=sum(int(trade.get("tons") or 0) for side, trade in trades if side == "buys"),
        tons_sold=sum(int(trade.get("tons") or 0) for side, trade in trades if side == "sells"),
        cost=sum(int(trade.get("cost") or 0) for side, trade in trades if side == "buys"),
        revenue=sum(int(trade.get("revenue") or 0) for side, trade in trades if side == "sells"),
    )


def summarize(
    rows: Iterable[dict[str, Any]], since: datetime | None, until: datetime,
    *, skipped_lines: int = 0,
) -> HaulSummary:
    """Summarize schema-1 rows by ended_at, keeping aborted money separate.

    `skipped_lines` is the reader's file-wide invalid-line count. Unknown
    expectations never enter the expected/actual comparison. Invalid end
    timestamps are counted as additional skipped rows rather than guessed.
    """
    if until.utcoffset() is None or (since is not None and since.utcoffset() is None):
        raise ValueError("Summary window boundaries must include a timezone")
    selected = []
    for row in rows:
        try:
            ended = datetime.fromisoformat(row["ended_at"].replace("Z", "+00:00"))
            if ended.utcoffset() is None:
                raise ValueError("Missing timezone")
        except (ValueError, KeyError, TypeError, AttributeError):
            skipped_lines += 1
            continue
        if (since is None or ended >= since) and ended <= until:
            selected.append(row)
    completed = [row for row in selected if row["status"] == "completed"]
    aborted = [row for row in selected if row["status"] == "aborted"]
    totals = _run_totals(completed)
    duration = sum(float(row.get("duration_s", 0)) for row in completed)
    all_in = _run_totals(selected)
    all_in_duration = sum(float(row.get("duration_s", 0)) for row in selected)
    profits = [row["revenue"] - row["cost"] for row in completed]
    expected = [row for row in completed if row.get("expected_profit") is not None]
    expected_profit = sum(row["expected_profit"] for row in expected) if expected else None
    actual_profit = _run_totals(expected).profit if expected else None
    route_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    commodity_groups: dict[str, dict[str, list[tuple[str, dict[str, Any]]]]] = {}
    for row in selected:
        route = row["route"]
        key = tuple(str(route.get(field) or "") for field in ("station_1", "system_1", "station_2", "system_2"))
        route_groups.setdefault(key, []).append(row)
        for leg in row.get("legs", []):
            for side in ("buys", "sells"):
                for trade in leg.get(side, []):
                    commodity = str(trade.get("commodity") or "unknown")
                    group = commodity_groups.setdefault(commodity, {"completed": [], "aborted": []})
                    group[row["status"]].append((side, trade))
    routes = tuple(
        RouteSummary(key[0], key[1] or None, key[2], key[3] or None,
                     _run_totals([row for row in group if row["status"] == "completed"]),
                     _run_totals([row for row in group if row["status"] == "aborted"]),
                     _run_totals(group))
        for key, group in sorted(route_groups.items())
    )
    commodities = tuple(
        CommoditySummary(name, _trade_totals(group["completed"]), _trade_totals(group["aborted"]),
                         _trade_totals(group["completed"] + group["aborted"]))
        for name, group in sorted(commodity_groups.items())
    )
    return HaulSummary(
        completed=CompletedSummary(
            totals.count, totals.cost, totals.revenue, totals.profit, duration,
            totals.profit * 3600 / duration if duration > 0 else None,
            totals.profit / totals.count if totals.count else None,
            max(profits) if profits else None, len(expected), expected_profit, actual_profit,
            actual_profit - expected_profit if expected else None,
        ),
        aborted=_run_totals(aborted), all_in=all_in, all_in_duration_s=all_in_duration,
        all_in_profit_per_hour=all_in.profit * 3600 / all_in_duration if all_in_duration > 0 else None,
        routes=routes,
        commodities=commodities, skipped_lines=skipped_lines,
    )
