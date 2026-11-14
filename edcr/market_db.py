"""The market and station database, owned by role: hub and standalone always open it, a peer never does.

`[eddn]` only decides whether the EDDN listener writes into it.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping

from edcr.config import AppConfig
from edcr.eddn.messages import EddnUpdate
from edcr.eddn.store import EddnStore
from edcr.recent_markets import MarketItem


def open_market_store(config: AppConfig) -> EddnStore | None:
    return EddnStore.open(config.eddn.database_file) if config.hub.owns_data else None


def station_facts_writer(store: EddnStore | None, log: Callable[[str], None]) -> Callable[[list[EddnUpdate]], None]:
    """Where the local node's journal facts go: the store, newest wins.

    A peer with a hub link queues them for the hub instead (`PeerLink.enqueue_station_facts`); one
    without (the TUI-only mode, or no `[hub] url`) keeps none.
    """

    def write(updates: list[EddnUpdate]) -> None:
        if store is None:
            return
        try:
            store.save(updates)
        except sqlite3.Error as exc:
            log(f"Warning: failed to record station facts: {exc}")

    return write


@dataclass(frozen=True)
class StoredPrices:
    """One market's EDDN prices: `updated_at` is epoch seconds of the message they came from."""

    market_id: int
    updated_at: float
    items: tuple[MarketItem, ...]


def read_stored_prices(
    database_file: Path | None, market_ids: Iterable[int], display_names: Mapping[str, str]
) -> dict[int, StoredPrices]:
    """The store's prices for these markets, keyed by market id; markets it lacks are left out.

    EDDN carries only commodity keys, so `display_names` (from our own Market.json items) gives the
    in-game names; a commodity we have never seen keeps its key as its name.
    """
    ids = [int(market_id) for market_id in market_ids]
    if database_file is None or not database_file.exists() or not ids:
        return {}
    marks = ",".join("?" * len(ids))
    db = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)
    try:
        updated = {
            int(market_id): float(updated_at)
            for market_id, updated_at in db.execute(
                f"SELECT market_id, updated_at FROM market WHERE market_id IN ({marks})", ids
            )
        }
        rows = db.execute(
            f"SELECT market_id, commodity, buy, sell, supply, demand FROM price WHERE market_id IN ({marks})"
            " ORDER BY market_id, commodity",
            ids,
        ).fetchall()
    finally:
        db.close()
    items: dict[int, list[MarketItem]] = {market_id: [] for market_id in updated}
    for market_id, commodity, buy, sell, supply, demand in rows:
        if int(market_id) not in items:
            continue
        items[int(market_id)].append(
            MarketItem(
                commodity=str(commodity),
                name=display_names.get(str(commodity), str(commodity)),
                category="",
                buy_price=int(buy),
                sell_price=int(sell),
                mean_price=0,
                stock=int(supply),
                demand=int(demand),
                stock_bracket=0,
                demand_bracket=0,
            )
        )
    return {
        market_id: StoredPrices(market_id=market_id, updated_at=updated_at, items=tuple(items[market_id]))
        for market_id, updated_at in updated.items()
    }
