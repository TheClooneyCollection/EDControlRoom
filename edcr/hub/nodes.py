"""The hub's side of the link: the node registry and one session per connected peer.

`HubLinkSession.receive` turns one frame from a peer into the frames to send back, with no I/O,
so the websocket glue in the server stays thin and tests drive sessions directly.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from edcr.eddn.game_markets import import_markets
from edcr.eddn.store import EddnStore
from edcr.hub.history import CentralHistory, HubRuns
from edcr.hub.peer import NodeHello, iso_utc
from edcr.hub.protocol import ITEM_HAUL_RUN, ITEM_MARKET, ITEM_STATION_FACTS, LinkReply, decode_update, response_frame
from edcr.hub.relay import RELAY_FRAMES, HubRelay
from edcr.hub.voice import CALLOUT_FRAME, HubVoice
from edcr.recent_markets import MarketSnapshot, snapshot_from_entry


class BadItem(ValueError):
    """An outbox item the hub can never store; it is acknowledged with an error and dropped."""


# Stores one outbox item from a node; raises BadItem for one that can never be stored, anything else to keep it.
ItemSink = Callable[[NodeHello, str, Any], None]
# Answers one peer request from its body.
RequestHandler = Callable[[Any], LinkReply]


@dataclass
class _Node:
    hello: NodeHello
    local: bool
    connected: bool
    connected_since: float | None
    last_contact: float | None
    # Bumped on every connection, so a replaced connection's close does not mark the node offline.
    generation: int = 0
    # Ship and running routine, as the peer last reported them (`edcr.hub.relay.node_state`).
    state: dict[str, Any] | None = None


class NodeRegistry:
    """Every node the hub knows: its own game (the local node) and each peer that said hello."""

    def __init__(self, local: NodeHello, now: Callable[[], float]) -> None:
        self.local = local
        self._now = now
        self._lock = threading.Lock()
        self._nodes: dict[str, _Node] = {
            local.node_id: _Node(local, local=True, connected=True, connected_since=now(), last_contact=None),
        }

    def connect(self, hello: NodeHello) -> int:
        with self._lock:
            node = self._nodes.get(hello.node_id)
            generation = node.generation + 1 if node is not None else 1
            at = self._now()
            self._nodes[hello.node_id] = _Node(hello, local=False, connected=True, connected_since=at,
                                               last_contact=at, generation=generation)
            return generation

    def set_state(self, node_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is not None:
                node.state = state

    def touch(self, node_id: str) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is not None:
                node.last_contact = self._now()

    def disconnect(self, node_id: str, generation: int) -> bool:
        """Mark the node offline unless a newer connection replaced this one; True when it did."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None or node.generation != generation:
                return False
            node.connected = False
            node.connected_since = None
            return True

    def nodes(self) -> list[dict[str, Any]]:
        with self._lock:
            nodes = sorted(self._nodes.values(), key=lambda node: (not node.local, node.hello.name.casefold()))
            now = self._now()
            return [
                {
                    "node_id": node.hello.node_id,
                    "name": node.hello.name,
                    "version": node.hello.version,
                    "local": node.local,
                    "connected": node.connected,
                    "connected_since": iso_utc(node.connected_since),
                    # The local node is this process, so it is always in contact.
                    "last_contact_at": iso_utc(now if node.local else node.last_contact),
                    "state": node.state if node.connected else None,
                }
                for node in nodes
            ]

    def last_ship(self, node_id: str) -> dict[str, Any] | None:
        """The ship a node last reported, kept after it goes offline (None before its first report)."""
        with self._lock:
            node = self._nodes.get(node_id)
            ship = node.state.get("ship") if node is not None and node.state is not None else None
            return ship if isinstance(ship, dict) else None

    def connected_peers(self) -> int:
        with self._lock:
            return sum(1 for node in self._nodes.values() if node.connected and not node.local)


@dataclass(frozen=True)
class HubSide:
    """What a hub needs to take peer links: its registry, where items go, the token peers present,
    the central haul history its views read, the relay for pages looking at a peer and the voice
    that speaks one node's callouts."""

    registry: NodeRegistry
    store_item: ItemSink
    token: str
    history: CentralHistory
    relay: HubRelay
    voice: HubVoice


class HubLinkSession:
    """One peer's connection on the hub. Not thread-safe for `receive` of non-request frames;
    the server calls it in arrival order and answers requests concurrently."""

    def __init__(
        self,
        *,
        registry: NodeRegistry,
        store_item: ItemSink,
        handlers: Mapping[str, RequestHandler],
        relay: HubRelay,
        callout: Callable[[str, str], None],
        linked: Callable[[str], None],
        send: Callable[[dict[str, Any]], None],
        log: Callable[[str], None],
    ) -> None:
        self._registry = registry
        self._relay = relay
        # Hands a peer's callout (node id, text) to the hub voice.
        self._callout = callout
        # Tells the hub voice a peer linked, so a muted node is muted again.
        self._linked = linked
        # Sends a frame to this peer outside an answer: the relay's channel and read frames.
        self._send = send
        self._store_item = store_item
        self._handlers = handlers
        self._log = log
        self.hello: NodeHello | None = None
        self._generation = 0
        # Set once the session refused the peer; the server then closes the socket.
        self.closed = False

    @property
    def label(self) -> str:
        return self.hello.name if self.hello is not None else "unknown peer"

    def receive(self, frame: Any) -> list[dict[str, Any]]:
        if not isinstance(frame, dict):
            return self._refuse("frames must be JSON objects")
        kind = frame.get("type")
        if self.hello is None:
            return self._hello(frame) if kind == "hello" else self._refuse("say hello first")
        self._registry.touch(self.hello.node_id)
        if kind == "ping":
            return [{"type": "pong"}]
        if kind == "item":
            return [self._item(frame)]
        if kind == "request":
            return [self._request(frame)]
        if kind == "node_state":
            if isinstance(frame.get("state"), dict):
                self._registry.set_state(self.hello.node_id, frame["state"])
            return []
        if kind == CALLOUT_FRAME:
            if isinstance(frame.get("text"), str):
                self._callout(self.hello.node_id, frame["text"])
            return []
        if kind in RELAY_FRAMES:
            self._relay.on_frame(self.hello.node_id, frame)
        return []

    def close(self) -> None:
        if self.hello is None:
            return
        self._relay.detach(self.hello.node_id, self._generation)
        if self._registry.disconnect(self.hello.node_id, self._generation):
            self._log(f"Peer {self.label} disconnected")

    def _hello(self, frame: dict[str, Any]) -> list[dict[str, Any]]:
        node_id = str(frame.get("node_id") or "").strip()
        if not node_id:
            return self._refuse("hello needs a node_id")
        local = self._registry.local
        if node_id == local.node_id:
            return self._refuse("this peer has the hub's own node id; delete the copied node id file on the peer")
        self.hello = NodeHello(node_id=node_id, name=str(frame.get("name") or node_id),
                               version=str(frame.get("version") or ""))
        self._generation = self._registry.connect(self.hello)
        self._log(f"Peer {self.label} connected (node {node_id}, version {self.hello.version or '?'})")
        self._relay.attach(self.hello, self._generation, self._send)
        self._linked(node_id)
        return [{"type": "welcome", "node_id": local.node_id, "name": local.name, "version": local.version}]

    def _refuse(self, detail: str) -> list[dict[str, Any]]:
        self.closed = True
        return [{"type": "error", "detail": detail}]

    def _item(self, frame: dict[str, Any]) -> dict[str, Any]:
        seq = frame.get("seq")
        try:
            self._store_item(self.hello, str(frame.get("kind")), frame.get("body"))
        except BadItem as exc:
            self._log(f"Peer {self.label}: dropped outbox item {seq}: {exc}")
            return {"type": "ack", "seq": seq, "error": str(exc)}
        except Exception as exc:  # Kept on the peer and sent again on its next connection.
            self._log(f"Peer {self.label}: could not store outbox item {seq}: {exc}")
            return {"type": "nack", "seq": seq, "error": str(exc)}
        return {"type": "ack", "seq": seq}

    def _request(self, frame: dict[str, Any]) -> dict[str, Any]:
        request_id = str(frame.get("id"))
        handler = self._handlers.get(str(frame.get("kind")))
        if handler is None:
            return response_frame(request_id, LinkReply(404, {"detail": f"unknown request {frame.get('kind')!r}"}))
        try:
            reply = handler(frame.get("body"))
        except Exception as exc:  # One failed answer must not end the link.
            self._log(f"Peer {self.label}: {frame.get('kind')} failed: {exc}")
            reply = LinkReply(500, {"detail": str(exc) or type(exc).__name__})
        return response_frame(request_id, reply)


def store_link_item(store: EddnStore, runs: HubRuns, record_market: Callable[[MarketSnapshot], None],
                    log: Callable[[str], None]) -> ItemSink:
    """Write a peer's market snapshots and station facts into the hub's store, newest wins, and its
    haul runs into the central history, once per run key and node. `record_market` also lists each
    market on the hub's Markets page, beside the hub's own."""

    def store_item(node: NodeHello, kind: str, body: Any) -> None:
        if kind == ITEM_HAUL_RUN:
            try:
                added = runs.add(node, body)
            except ValueError as exc:
                raise BadItem(str(exc)) from exc
            if added:
                log(f"Haul history: run from {node.name} ({body.get('status')}, ended {body.get('ended_at')})")
            return
        if kind == ITEM_MARKET:
            snapshot = snapshot_from_entry(body)
            if snapshot is None:
                raise BadItem("not a recent market entry")
            result = import_markets(store, (snapshot,))
            record_market(snapshot)
            if result:
                log(f"Market DB peer market {snapshot.station}: {'written' if result[0].written else 'already in the DB'}")
            return
        if kind == ITEM_STATION_FACTS:
            update = decode_update(body)
            if update is None:
                raise BadItem("not a station or system fact")
            try:
                store.save([update])
            except sqlite3.InterfaceError as exc:  # Wrongly typed values can never be stored.
                raise BadItem(str(exc)) from exc
            return
        raise BadItem(f"unknown item kind {kind!r}")

    return store_item
