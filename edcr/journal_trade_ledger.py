"""Read-only journal ledger. No inferred haul runs or application state."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

_JOURNAL_NAME = re.compile(r"Journal\.(\d{4}-\d{2}-\d{2}T\d{6})\.\d+\.log$")
_OTHER_FLOWS = {
    "ModuleBuy": ("BuyPrice", -1), "ModuleSell": ("SellPrice", 1),
    "Repair": ("Cost", -1), "RepairAll": ("Cost", -1),
    "RefuelAll": ("Cost", -1), "RefuelPartial": ("Cost", -1),
    "MissionCompleted": ("Reward", 1), "RedeemVoucher": ("Amount", 1),
    "PayFines": ("Amount", -1), "PayBounties": ("Amount", -1), "Resurrect": ("Cost", -1),
}


@dataclass(frozen=True)
class LedgerCommodity:
    commodity: str
    tons_bought: int
    tons_sold: int
    cost: int
    revenue: int
    sell_margin: int | None


@dataclass(frozen=True)
class LedgerStation:
    station: str
    cost: int
    revenue: int


@dataclass(frozen=True)
class LedgerCoverage:
    first_event_at: str | None
    last_event_at: str | None
    files: int
    window_start_before_oldest_journal: bool
    skipped_lines: int
    unreadable_files: int


@dataclass(frozen=True)
class JournalTradeLedger:
    available: bool
    reason: str | None
    buys: int
    sells: int
    cost: int
    revenue: int
    profit: int
    sell_margin: int | None
    commodities: tuple[LedgerCommodity, ...]
    stations: tuple[LedgerStation, ...]
    start_balance: int | None
    start_balance_at: str | None
    end_balance: int | None
    end_balance_at: str | None
    net_balance_change: int | None
    coverage: LedgerCoverage
    other_flows: dict[str, int]


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Missing timestamp timezone")
    return result.astimezone(timezone.utc)


def _amount(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def journal_trade_ledger(journal_dir: Path | None, since: datetime | None, until: datetime) -> JournalTradeLedger:
    """Scan overlapping files and filter transactions by inclusive UTC instants.

    One preceding file-start group is scanned for continuing sessions/context.
    Coverage describes all timestamped events seen in the selected files, not
    just trades in the window. Balance change compares observed snapshots, not
    an inferred balance at the exact boundaries. A timestamped Status.json is
    eligible only at/before until, so a present-day snapshot cannot leak into a
    historical query. Missing purchase basis makes sell_margin unknown.
    """
    if until.utcoffset() is None or (since is not None and since.utcoffset() is None):
        raise ValueError("Journal window boundaries must include a timezone")
    candidates: list[tuple[datetime, Path]] = []
    reason = None
    try:
        if journal_dir is None:
            raise FileNotFoundError("journal directory is not configured")
        for path in journal_dir.iterdir():
            match = _JOURNAL_NAME.fullmatch(path.name)
            if match:
                try:
                    stamp = datetime.strptime(match[1], "%Y-%m-%dT%H%M%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                candidates.append((stamp, path))
    except OSError as exc:
        reason = str(exc)
    candidates.sort()
    oldest = candidates[0][0] if candidates else None
    preceding = max((stamp for stamp, _ in candidates if since is not None and stamp < since), default=None)
    selected = [(stamp, path) for stamp, path in candidates if stamp <= until and (
        since is None or stamp >= since or stamp == preceding
    )]
    cost = revenue = buys = sells = margin = files = skipped = unreadable = 0
    margin_known = True
    first_event = last_event = None
    station = "unknown"
    markets: dict[object, str] = {}
    commodities: dict[str, dict[str, Any]] = {}
    stations: dict[str, list[int]] = {}
    other_flows: dict[str, int] = {}
    load_balances: list[tuple[datetime, int]] = []
    balances: list[tuple[datetime, int]] = []
    for _, path in selected:
        try:
            with path.open("rb") as handle:
                files += 1
                for line in handle:
                    try:
                        event = json.loads(line)
                        when = _timestamp(event["timestamp"])
                        name = event["event"]
                        if not isinstance(name, str):
                            raise ValueError("Missing event name")
                    except (ValueError, TypeError, KeyError, UnicodeError):
                        skipped += 1
                        continue
                    first_event = min(first_event, when) if first_event else when
                    last_event = max(last_event, when) if last_event else when
                    if when > until:
                        continue
                    if name in {"Docked", "Location"}:
                        station = str(event.get("StationName") or "unknown")
                        market_id = event.get("MarketID")
                        if isinstance(market_id, (int, str)) and station != "unknown":
                            markets[market_id] = station
                    elif name == "Undocked":
                        station = "unknown"
                    balance = _amount(event.get("Credits" if name == "LoadGame" else "Balance"))
                    if name in {"LoadGame", "Status"} and balance is not None:
                        balances.append((when, balance))
                        if name == "LoadGame":
                            load_balances.append((when, balance))
                    if since is not None and when < since:
                        continue
                    if name in {"MarketBuy", "MarketSell"}:
                        buying = name == "MarketBuy"
                        total = _amount(event.get("TotalCost" if buying else "TotalSale"))
                        tons = _amount(event.get("Count"))
                        if total is None or tons is None:
                            skipped += 1
                            continue
                        commodity = str(event.get("Type") or "unknown")
                        group = commodities.setdefault(commodity, dict(tons_bought=0, tons_sold=0, cost=0,
                                                                      revenue=0, sell_margin=0))
                        market_id = event.get("MarketID")
                        trade_station = (markets.get(market_id, "unknown")
                                         if isinstance(market_id, (int, str)) else station)
                        station_totals = stations.setdefault(trade_station, [0, 0])
                        if buying:
                            buys += 1
                            cost += total
                            group["cost"] += total
                            group["tons_bought"] += tons
                            station_totals[0] += total
                        else:
                            sells += 1
                            revenue += total
                            group["revenue"] += total
                            group["tons_sold"] += tons
                            station_totals[1] += total
                            basis = _amount(event.get("AvgPricePaid"))
                            if basis is None:
                                margin_known = False
                                group["sell_margin"] = None
                            else:
                                sell_margin = total - basis * tons
                                margin += sell_margin
                                if group["sell_margin"] is not None:
                                    group["sell_margin"] += sell_margin
                    elif name in _OTHER_FLOWS:
                        field, sign = _OTHER_FLOWS[name]
                        amount = _amount(event.get(field))
                        if amount is not None:
                            other_flows[name] = other_flows.get(name, 0) + sign * amount
                            if name == "ModuleBuy":
                                other_flows[name] += _amount(event.get("SellPrice")) or 0
        except OSError:
            unreadable += 1
    if journal_dir is not None and reason is None:
        try:
            status = json.loads((journal_dir / "Status.json").read_bytes())
            when = _timestamp(status["timestamp"])
            balance = _amount(status.get("Balance"))
            if balance is not None and when <= until:
                balances.append((when, balance))
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            pass
    load_balances.sort()
    balances.sort()
    before = [item for item in load_balances if since is not None and item[0] <= since]
    start = before[-1] if before else (load_balances[0] if load_balances else None)
    end = balances[-1] if balances else None
    change = (end[1] - start[1] if start and end and end[0] > start[0]
              and (since is None or end[0] >= since) else None)
    if selected and not files:
        reason = "journal files are unreadable"
    return JournalTradeLedger(
        available=reason is None, reason=reason, buys=buys, sells=sells, cost=cost, revenue=revenue,
        profit=revenue-cost, sell_margin=margin if margin_known else None,
        commodities=tuple(LedgerCommodity(name, **group) for name, group in sorted(commodities.items())),
        stations=tuple(LedgerStation(name, totals[0], totals[1]) for name, totals in sorted(stations.items())),
        start_balance=start[1] if start else None, start_balance_at=start[0].isoformat() if start else None,
        end_balance=end[1] if end else None, end_balance_at=end[0].isoformat() if end else None,
        net_balance_change=change,
        coverage=LedgerCoverage(first_event.isoformat() if first_event else None,
                                last_event.isoformat() if last_event else None, files,
                                bool(since is not None and oldest is not None and since < oldest), skipped, unreadable),
        other_flows=other_flows,
    )
