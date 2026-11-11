"""The market and station database, owned by role: hub and standalone always open it, a peer never does.

`[eddn]` only decides whether the EDDN listener writes into it.
"""
from __future__ import annotations

import sqlite3
from typing import Callable

from edap.config import AppConfig
from edap.eddn.messages import EddnUpdate
from edap.eddn.store import EddnStore


def open_market_store(config: AppConfig) -> EddnStore | None:
    return EddnStore.open(config.eddn.database_file) if config.hub.owns_data else None


def station_facts_writer(store: EddnStore | None, log: Callable[[str], None]) -> Callable[[list[EddnUpdate]], None]:
    """Where the local node's journal facts go: the store, newest wins; a peer keeps none for now."""

    def write(updates: list[EddnUpdate]) -> None:
        if store is None:
            # A peer owns no data; the hub link (plan 0015 step 2) sends these up.
            return
        try:
            store.save(updates)
        except sqlite3.Error as exc:
            log(f"Warning: failed to record station facts: {exc}")

    return write
