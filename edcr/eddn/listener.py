"""Background EDDN relay subscriber that keeps an `EddnStore` current."""
from __future__ import annotations

import json
import sqlite3
import threading
import zlib
from dataclasses import dataclass, replace
from typing import Callable, Protocol

from edcr.eddn.messages import MarketSnapshot, StationInfo, SystemPosition, parse_eddn_message
from edcr.eddn.store import EddnStore

DEFAULT_RELAY = "tcp://eddn.edcd.io:9500"
# EDDN recommends reconnecting when the relay goes quiet; real traffic is several messages a second.
SILENCE_RECONNECT_S = 60.0
PRUNE_INTERVAL_S = 3600.0


class EddnSocket(Protocol):
    def recv(self, timeout_s: float) -> bytes | None: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class EddnListenerStats:
    connected: bool = False
    messages: int = 0
    markets: int = 0
    stations: int = 0
    systems: int = 0
    errors: int = 0
    reconnects: int = 0
    last_message_at: float | None = None
    last_error: str = ""


def apply_payload(store: EddnStore, payload: bytes) -> list[type]:
    """Decode one relay frame and apply it; returns the update types applied."""
    envelope = json.loads(zlib.decompress(payload))
    return [type(update) for update in parse_eddn_message(envelope) if store.apply(update)]


def open_zmq_socket(relay: str) -> EddnSocket:
    import zmq

    context = zmq.Context.instance()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(relay)

    class _ZmqSocket:
        def recv(self, timeout_s: float) -> bytes | None:
            if not socket.poll(int(timeout_s * 1000)):
                return None
            return socket.recv()

        def close(self) -> None:
            socket.close()

    return _ZmqSocket()


class EddnListener:
    def __init__(
        self,
        *,
        store: EddnStore,
        open_socket: Callable[[], EddnSocket],
        time_fn: Callable[[], float],
        max_age_s: float,
        log: Callable[[str], None],
        commit_interval_s: float = 1.0,
        poll_timeout_s: float = 1.0,
    ) -> None:
        self._store = store
        self._open_socket = open_socket
        self._time = time_fn
        self._max_age_s = max_age_s
        self._log = log
        self._commit_interval_s = commit_interval_s
        self._poll_timeout_s = poll_timeout_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stats = EddnListenerStats()

    def stats(self) -> EddnListenerStats:
        with self._lock:
            return self._stats

    def start(self) -> None:
        self._thread = threading.Thread(target=self.run, name="eddn-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout_s: float) -> None:
        if self._thread is not None:
            self._thread.join(timeout_s)

    def run(self) -> None:
        """Receive until `stop()`; reconnects after a silent minute."""
        self._prune()
        last_prune = last_commit = self._time()
        while not self._stop.is_set():
            socket = self._open_socket()
            self._update(connected=True)
            last_heard = self._time()
            try:
                while not self._stop.is_set():
                    payload = socket.recv(self._poll_timeout_s)
                    now = self._time()
                    if payload is not None:
                        last_heard = now
                        self._handle(payload, now)
                    if now - last_commit >= self._commit_interval_s:
                        self._store.commit()
                        last_commit = now
                    if now - last_prune >= PRUNE_INTERVAL_S:
                        self._prune()
                        last_prune = now
                    if now - last_heard >= SILENCE_RECONNECT_S:
                        self._log("EDDN relay silent; reconnecting.")
                        self._update(reconnects=self._stats.reconnects + 1)
                        break
            finally:
                socket.close()
                self._update(connected=False)
        self._store.commit()

    def _handle(self, payload: bytes, now: float) -> None:
        try:
            applied = apply_payload(self._store, payload)
        except (ValueError, zlib.error, sqlite3.Error) as error:
            self._update(messages=self._stats.messages + 1, errors=self._stats.errors + 1, last_error=str(error))
            return
        stats = self._stats
        self._update(
            messages=stats.messages + 1,
            markets=stats.markets + applied.count(MarketSnapshot),
            stations=stats.stations + applied.count(StationInfo),
            systems=stats.systems + applied.count(SystemPosition),
            last_message_at=now,
        )

    def _prune(self) -> None:
        removed = self._store.prune(older_than=self._time() - self._max_age_s)
        if removed:
            self._log(f"EDDN: pruned {removed} stale markets.")

    def _update(self, **changes: object) -> None:
        with self._lock:
            self._stats = replace(self._stats, **changes)
