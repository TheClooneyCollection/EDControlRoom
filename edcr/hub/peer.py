"""A peer's side of the hub link: it dials out, says hello, drains its outbox and asks the hub.

The link is one websocket to the hub's `/api/peer-link`, kept open and redialled with backoff.
`connect` is a plain function returning a `LinkConnection`, so tests use an in-memory pair.
"""
from __future__ import annotations

import itertools
import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

from edcr.eddn.messages import EddnUpdate
from edcr.haul_history import run_key
from edcr.hub.outbox import Outbox
from edcr.hub.protocol import (
    ITEM_HAUL_RUN, ITEM_JOURNAL_EVENTS, ITEM_MARKET, ITEM_STATION_FACTS, PEER_LINK_PATH, HubUnreachable, LinkClosed, LinkConnection, LinkReply,
    encode_update,
)
from edcr.hub.voice import VOICE_MUTE_FRAME
from edcr.journal_sync import JournalBatch, batch_body
from edcr.recent_markets import MarketSnapshot, snapshot_entry

# Seconds between redials while the hub stays away; the last one repeats.
RECONNECT_DELAYS_S = (1.0, 2.0, 5.0, 10.0, 30.0)
# The node id lives next to the config file, so it survives restarts and reinstalls of the code.
NODE_ID_FILE_NAME = ".control_room_node_id"


class LinkRelay(Protocol):
    """Hub pages looking at this peer (`edcr.hub.relay.PeerRelay`): told when the link comes and goes,
    handed every frame the link itself does not handle."""

    def link_up(self, send: Callable[[dict[str, Any]], None]) -> None: ...

    def link_down(self) -> None: ...

    def on_frame(self, frame: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class NodeHello:
    node_id: str
    name: str
    version: str


def load_node_id(path: Path, new_id: Callable[[], str]) -> str:
    """This node's stable id: read from `path`, or made once and written there."""
    try:
        existing = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        existing = ""
    if existing:
        return existing
    node_id = new_id()
    path.write_text(node_id + "\n", encoding="utf-8")
    return node_id


def new_node_id() -> str:
    return uuid.uuid4().hex


def iso_utc(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class _Waiter:
    def __init__(self) -> None:
        self.done = threading.Event()
        self.reply: LinkReply | None = None
        self.error = ""


class PeerLink:
    """The peer's link state. Thread-safe: the link thread reads frames while server threads ask and queue."""

    def __init__(
        self,
        *,
        hello: NodeHello,
        hub_url: Callable[[], str],
        outbox: Outbox,
        relay: LinkRelay,
        connect: Callable[[], LinkConnection],
        accept_hub: Callable[[str, str, str], str],
        now: Callable[[], float],
        log: Callable[[str], None],
        heartbeat_s: float,
        request_timeout_s: float,
        search_timeout_s: float,
    ) -> None:
        self.hello = hello
        # How long route, status and station fact requests wait; Inara searches drive a browser and take longer.
        self.request_timeout_s = request_timeout_s
        self.search_timeout_s = search_timeout_s
        # The configured hub, or the one discovery dialled last (`edcr.hub.discovery.DiscoveredHub`).
        self._hub_url = hub_url
        # Checks the hub's id, name and url on welcome: "" keeps the link, else why it is refused.
        self._accept_hub = accept_hub
        self.outbox = outbox
        self._relay = relay
        self._connect = connect
        self._now = now
        self._log = log
        self._heartbeat_s = heartbeat_s
        # Reentrant: an in-memory link answers inside `send`, on the same thread.
        self._lock = threading.RLock()
        self._conn: LinkConnection | None = None
        self._welcomed = False
        # True once the outbox is drained on this connection: new items then go out at once.
        self._live = False
        self._sent_upto = 0
        self._hub_name = ""
        self._hub_version = ""
        self._connected_since: float | None = None
        self._last_contact: float | None = None
        self._last_error = ""
        self._waiters: dict[str, _Waiter] = {}
        self._ids = itertools.count(1)

    @property
    def hub_url(self) -> str:
        return self._hub_url()

    @property
    def host(self) -> str:
        return urlparse(self.hub_url).netloc or self.hub_url

    @property
    def hub_label(self) -> str:
        """How answers are tagged: the hub's name once it said hello, else its address."""
        return self._hub_name or self.host

    # Outbox ------------------------------------------------------------------------------------

    def enqueue_market(self, market: MarketSnapshot) -> None:
        self._enqueue(ITEM_MARKET, snapshot_entry(market), key=f"market:{market.market_id}:{market.timestamp}")

    def enqueue_markets(self, markets: tuple[MarketSnapshot, ...]) -> None:
        """Queue every market not queued before; the recent-markets watcher calls this at start and on change."""
        for market in markets:
            self.enqueue_market(market)

    def enqueue_station_facts(self, updates: list[EddnUpdate]) -> None:
        for update in updates:
            body = encode_update(update)
            identity = body.get("market_id", body.get("address", body.get("callsign")))
            self._enqueue(ITEM_STATION_FACTS, body, key=f"{body['kind']}:{identity}:{update.timestamp}")

    def enqueue_runs(self, rows: list[dict[str, Any]]) -> None:
        """Queue every finished haul run not queued before; the run history watcher calls this at
        start (the first link backfills the whole file once) and whenever the file changes."""
        for row in rows:
            started_at, ended_at, station_1, _ = run_key(row)
            self._enqueue(ITEM_HAUL_RUN, row, key=f"run:{started_at}|{ended_at}|{station_1}", forever=True)

    def enqueue_journal(self, batch: JournalBatch) -> None:
        """Queue a batch of journal lines; raises when it could not be queued, so the sync retries it."""
        first = batch.lines[0].line if batch.lines else batch.position.line
        if not self._enqueue(ITEM_JOURNAL_EVENTS, batch_body(batch), key=f"journal:{batch.file}:{first}", forever=True):
            raise OSError("hub outbox write failed")

    def _enqueue(self, kind: str, body: Any, *, key: str, forever: bool = False) -> bool:
        """False only when the outbox could not be written."""
        with self._lock:
            try:
                seq = self.outbox.add(kind, body, key=key, now=self._now(), forever=forever)
            except sqlite3.Error as exc:
                self._log(f"Warning: hub outbox write failed, {kind} not queued: {exc}")
                return False
            if seq is not None and self._live:
                try:
                    self._send_items()
                except Exception as exc:  # Still queued; the read loop notices the broken link.
                    self._log(f"Hub link send failed, {kind} stays queued: {exc}")
            return True

    def _send_items(self) -> None:
        """Send what this connection has not sent yet, in order (the caller holds the lock)."""
        assert self._conn is not None
        while True:
            items = self.outbox.pending(after=self._sent_upto)
            if not items:
                return
            for item in items:
                self._conn.send({"type": "item", "seq": item.seq, "kind": item.kind, "body": item.body})
                self._sent_upto = item.seq

    # One connection ----------------------------------------------------------------------------

    def attach(self, conn: LinkConnection) -> None:
        with self._lock:
            self._conn = conn
            self._welcomed = self._live = False
            self._sent_upto = 0
            conn.send({"type": "hello", "node_id": self.hello.node_id, "name": self.hello.name,
                       "version": self.hello.version})

    def detach(self, conn: LinkConnection, error: str) -> bool:
        """Forget the connection; True when the hub had welcomed it."""
        with self._lock:
            if self._conn is not conn:
                return False
            was_up = self._welcomed
            self._conn = None
            self._welcomed = self._live = False
            self._connected_since = None
            self._last_error = error
            waiters, self._waiters = self._waiters, {}
        # Outside the lock: the relay sends through this link from other threads too.
        self._relay.link_down()
        for waiter in waiters.values():
            waiter.error = f"the hub link closed: {error}"
            waiter.done.set()
        if was_up:
            self._log(f"Hub link to {self.hub_label} lost: {error}; redialling")
        return was_up

    def send_frame(self, frame: dict[str, Any]) -> None:
        """Send one frame on the current connection; raises LinkClosed when there is none."""
        with self._lock:
            if self._conn is None or not self._welcomed:
                raise LinkClosed("not connected to the hub")
            self._conn.send(frame)

    def on_frame(self, frame: dict[str, Any]) -> None:
        kind = frame.get("type")
        # Hub pages looking at and driving this node (`edcr.hub.relay.HUB_RELAY_FRAMES`); they arrive
        # only here, on the link this peer dialled to its own hub.
        if kind in {"channel_open", "channel_close", "channel_command", "read", "act", VOICE_MUTE_FRAME}:
            with self._lock:
                self._last_contact = self._now()
            self._relay.on_frame(frame)
            return
        with self._lock:
            self._last_contact = self._now()
            if kind == "welcome":
                refusal = self._accept_hub(str(frame.get("node_id") or ""), str(frame.get("name") or ""),
                                           self.hub_url)
                if refusal:
                    self._last_error = refusal
                    self._log(f"WARNING: not linking to {self.host}: {refusal}")
                    raise LinkClosed(refusal)
                self._welcomed = True
                self._connected_since = self._last_contact
                self._last_error = ""
                self._hub_name = str(frame.get("name") or "")
                self._hub_version = str(frame.get("version") or "")
                pending = self.outbox.count()
                self._log(f"Hub link up: {self.hub_label} ({self.host}); sending {pending} queued item(s)")
                if self._conn is not None:
                    self._send_items()
                self._live = True
            elif kind == "ack":
                seq = frame.get("seq")
                if isinstance(seq, int):
                    self.outbox.remove(seq)
                if frame.get("error"):
                    self._log(f"Hub {self.hub_label} dropped outbox item {seq}: {frame['error']}")
            elif kind == "nack":
                # Kept; the next connection sends it again.
                self._log(f"Hub {self.hub_label} could not store outbox item {frame.get('seq')}: {frame.get('error')}")
            elif kind == "error":
                self._last_error = str(frame.get("detail") or "refused by the hub")
                self._log(f"Hub {self.host} refused the link: {self._last_error}")
                raise LinkClosed(self._last_error)
        if kind == "welcome":
            self._relay.link_up(self.send_frame)
        if kind == "response":
            waiter = self._waiters.pop(str(frame.get("id")), None)
            if waiter is not None:
                waiter.reply = LinkReply(int(frame.get("status") or 0), frame.get("body"))
                waiter.done.set()

    def serve(self, conn: LinkConnection) -> bool:
        """Run one connection until it closes; True when the hub welcomed it.

        Pings the hub after `heartbeat_s` of quiet and gives up after twice that.
        """
        error = "closed"
        try:
            self.attach(conn)
            while True:
                frame = conn.receive(self._heartbeat_s)
                if frame is not None:
                    self.on_frame(frame)
                    continue
                quiet = self._now() - (self._last_contact or 0.0)
                if quiet >= 2 * self._heartbeat_s:
                    raise LinkClosed(f"no answer for {quiet:.0f} s")
                conn.send({"type": "ping"})
        except LinkClosed as exc:
            error = str(exc) or "closed"
        except Exception as exc:  # A broken socket or bad frame ends this connection only.
            error = str(exc) or type(exc).__name__
        finally:
            was_up = self.detach(conn, error)
            conn.close()
        return was_up

    def run(self, wait: Callable[[float], bool]) -> None:
        """Dial, serve and redial with backoff until `wait` returns True (a stop event's `wait`)."""
        attempt = 0
        quiet = False
        while True:
            try:
                conn = self._connect()
            except Exception as exc:  # Refused, timed out, bad token: try again later.
                error = str(exc) or type(exc).__name__
                with self._lock:
                    self._last_error = error
                if not quiet:
                    self._log(f"Hub link to {self.host or 'the hub'} failed: {error}; redialling with backoff")
                    quiet = True
            else:
                if self.serve(conn):
                    attempt = 0
                    quiet = False
            delay = RECONNECT_DELAYS_S[min(attempt, len(RECONNECT_DELAYS_S) - 1)]
            attempt += 1
            if wait(delay):
                return

    # Requests ----------------------------------------------------------------------------------

    def request(self, kind: str, body: Any, *, timeout_s: float) -> LinkReply:
        """Ask the hub and wait for its answer; raises HubUnreachable when the link is down or slow."""
        waiter = _Waiter()
        request_id = str(next(self._ids))
        with self._lock:
            if self._conn is None or not self._welcomed:
                reason = f": {self._last_error}" if self._last_error else ""
                raise HubUnreachable(f"not connected to the hub{reason}")
            self._waiters[request_id] = waiter
            try:
                self._conn.send({"type": "request", "id": request_id, "kind": kind, "body": body})
            except Exception as exc:
                self._waiters.pop(request_id, None)
                raise HubUnreachable(str(exc) or type(exc).__name__) from exc
        if not waiter.done.wait(timeout_s):
            with self._lock:
                self._waiters.pop(request_id, None)
            raise HubUnreachable(f"no answer in {timeout_s:g} s")
        if waiter.reply is None:
            raise HubUnreachable(waiter.error)
        return waiter.reply

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "configured": True,
                "role": "peer",
                "url": self.hub_url,
                "host": self.host,
                "hub_name": self._hub_name or None,
                "hub_version": self._hub_version or None,
                "connected": self._welcomed,
                "connected_since": iso_utc(self._connected_since),
                "last_contact_at": iso_utc(self._last_contact),
                "last_error": self._last_error or None,
                "outbox_pending": self.outbox.count(),
                "node_id": self.hello.node_id,
                "node_name": self.hello.name,
            }


def with_hub_source(payload: Any, label: str) -> Any:
    """Tag a hub answer so pages can say where it came from."""
    return {**payload, "hub": label} if isinstance(payload, dict) else payload


def hub_unreachable_detail(label: str, exc: Exception) -> str:
    return f"Hub {label} is unreachable: {exc}"


def peer_link_url(hub_url: str) -> str:
    scheme = "wss" if hub_url.startswith("https://") else "ws"
    return f"{scheme}://{hub_url.split('://', 1)[1]}{PEER_LINK_PATH}"


class WebSocketLink:
    """A `LinkConnection` over a real websocket (websockets' sync client)."""

    def __init__(self, socket: Any) -> None:
        self._socket = socket
        self._send_lock = threading.Lock()

    def send(self, frame: dict[str, Any]) -> None:
        from websockets.exceptions import ConnectionClosed

        try:
            with self._send_lock:
                self._socket.send(json.dumps(frame))
        except ConnectionClosed as exc:
            raise LinkClosed(str(exc)) from exc

    def receive(self, timeout_s: float) -> dict[str, Any] | None:
        from websockets.exceptions import ConnectionClosed

        try:
            text = self._socket.recv(timeout=timeout_s)
        except TimeoutError:
            return None
        except ConnectionClosed as exc:
            raise LinkClosed(str(exc)) from exc
        frame = json.loads(text)
        return frame if isinstance(frame, dict) else {}

    def close(self) -> None:
        self._socket.close()


def websocket_dialer(token: str, *, timeout_s: float) -> Callable[[str], LinkConnection]:
    """Dials a hub's link at the given base URL."""

    def dial(hub_url: str) -> LinkConnection:
        from websockets.sync.client import connect as ws_connect

        socket = ws_connect(
            peer_link_url(hub_url),
            additional_headers={"Authorization": f"Bearer {token}"},
            open_timeout=timeout_s,
            # Route lists and search results can be large.
            max_size=16 * 1024 * 1024,
        )
        return WebSocketLink(socket)

    return dial
