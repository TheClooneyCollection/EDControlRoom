"""EDDN listener plus store, run as one background service inside the Control Room server."""
from __future__ import annotations

import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from edap.config import EddnConfig
from edap.eddn.game_markets import import_game_markets, import_summary
from edap.eddn.listener import EddnListener, EddnListenerStats, EddnSocket
from edap.eddn.store import EddnStore, EddnStoreCounts
from edap.hub import watch_recent_markets


def status_line(stats: EddnListenerStats, counts: EddnStoreCounts) -> str:
    state = "connected" if stats.connected else "disconnected"
    newest = (
        datetime.fromtimestamp(counts.newest_market_at).strftime("%H:%M:%S")
        if counts.newest_market_at is not None
        else "-"
    )
    return (
        f"{state}: {stats.messages} msgs, {stats.markets} market updates, {stats.errors} errors | "
        f"db {counts.markets} markets, {counts.prices} prices, {counts.stations} stations, "
        f"{counts.systems} systems, newest {newest}"
    )


@dataclass(frozen=True)
class EddnService:
    store: EddnStore
    listener: EddnListener
    _stop_status: threading.Event = field(default_factory=threading.Event)

    def status(self) -> dict[str, Any]:
        return {"listener": asdict(self.listener.stats()), "store": asdict(self.store.counts())}

    def status_line(self) -> str:
        return status_line(self.listener.stats(), self.store.counts())

    def report_status_every(self, interval_s: float, log: Callable[[str], None]) -> None:
        def report() -> None:
            while not self._stop_status.wait(interval_s):
                log(f"EDDN {self.status_line()}")

        threading.Thread(target=report, name="eddn-status", daemon=True).start()

    def import_game_markets_every(self, recent_markets_file: Path, interval_s: float, log: Callable[[str], None]) -> None:
        """Write our own Market.json captures into the store, at start and whenever the Control Room records one."""
        watch_recent_markets(
            recent_markets_file,
            interval_s,
            lambda path: log(f"EDDN {import_summary(import_game_markets(self.store, path))}"),
            stop=self._stop_status,
            log=log,
            name="eddn-game-markets",
        )

    def close(self) -> None:
        self._stop_status.set()
        self.listener.stop()
        self.listener.join(5.0)
        self.store.close()


def start_eddn_service(
    config: EddnConfig,
    *,
    open_socket: Callable[[], EddnSocket],
    time_fn: Callable[[], float],
    log: Callable[[str], None],
) -> EddnService:
    store = EddnStore.open(config.database_file)
    listener = EddnListener(
        store=store,
        open_socket=open_socket,
        time_fn=time_fn,
        max_age_s=config.max_age_days * 86400,
        log=log,
    )
    listener.start()
    service = EddnService(store=store, listener=listener)
    if config.status_every_s > 0:
        service.report_status_every(config.status_every_s, log)
    return service
