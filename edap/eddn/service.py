"""EDDN listener plus store, run as one background service inside the Control Room server."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from edap.config import EddnConfig
from edap.eddn.listener import EddnListener, EddnSocket
from edap.eddn.store import EddnStore


@dataclass(frozen=True)
class EddnService:
    store: EddnStore
    listener: EddnListener

    def status(self) -> dict[str, Any]:
        return {"listener": asdict(self.listener.stats()), "store": asdict(self.store.counts())}

    def close(self) -> None:
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
    return EddnService(store=store, listener=listener)
