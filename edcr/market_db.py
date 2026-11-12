"""The market and station database, owned by role: hub and standalone always open it, a peer never does.

`[eddn]` only decides whether the EDDN listener writes into it.
"""
from __future__ import annotations

import sqlite3
from typing import Callable

from edcr.config import AppConfig
from edcr.eddn.messages import EddnUpdate
from edcr.eddn.store import EddnStore


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
