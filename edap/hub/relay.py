"""Hub pages looking at a peer (plan 0015 step 5): session channels and allowlisted reads over the link.

A hub page opens its session with `?node=<node_id>`. For a peer the hub opens a channel over the peer
link; the peer attaches a broker listener and streams the same session messages (connection ready,
hydrate, broker events) back, and the hub hands them to the page. Node-specific HTTP reads go down as
`read` frames and are answered only for `NODE_READS`. Viewing only: commands are refused on the hub.

Hub to peer: `channel_open` (channel, client_name), `channel_close` (channel), `read` (id, path, params).
Peer to hub: `channel` (channel, message), `read_response` (id, status, body), `node_state` (state).
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass
from typing import Any, Callable

from edap.hub.peer import NodeHello
from edap.hub.protocol import LinkReply

# The page reads a hub relays to the node a page looks at; everything else the hub answers itself.
NODE_READS = frozenset({
    "/api/recent-markets",
    "/api/market-compare",
    "/api/route-compare",
    "/api/route-compare/config",
    "/api/spansh-route",
    # The hub owns the market store, but routes start from the node's ship; the peer asks the hub back.
    "/api/eddn-routes",
})
# Reads that ask Spansh and can take minutes.
SLOW_READS = frozenset({"/api/route-compare", "/api/spansh-route"})
# Frames from a peer that belong to the relay.
RELAY_FRAMES = frozenset({"channel", "read_response", "node_state"})

# Hands one session message to a page.
Deliver = Callable[[dict[str, Any]], None]
# Tells a page its channel ended, with why.
End = Callable[[str], None]
# Sends one frame on the link; raises when it is down.
Send = Callable[[dict[str, Any]], None]


class NodeOffline(OSError):
    """The node a page looks at is not linked, or did not answer in time."""


def node_state(data: object) -> dict[str, Any]:
    """What the hub's node picker shows for a node: its ship and the routine it runs."""
    ship = getattr(data, "ship", None)
    routine = getattr(data, "routine", None)
    return {
        "ship": {"id": getattr(ship, "ship_id", None), "type": getattr(ship, "ship_type", None),
                 "name": getattr(ship, "ship_name", None)},
        "routine": getattr(routine, "active_routine_name", None) if getattr(routine, "routine_active", False) else None,
    }


@dataclass
class _Channel:
    node_id: str
    deliver: Deliver
    end: End


class _Waiter:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.done = threading.Event()
        self.reply: LinkReply | None = None
        self.error = ""


@dataclass
class _Link:
    hello: NodeHello
    generation: int
    send: Send


class HubRelay:
    """The hub's side: which peers can be reached, the pages looking at them and reads in flight.

    Thread-safe. `send` functions must not block for long: production schedules the frame on the
    event loop; tests answer inside the call, so the lock is reentrant.
    """

    def __init__(self, *, log: Callable[[str], None], read_timeout_s: float, slow_read_timeout_s: float) -> None:
        self._log = log
        self._read_timeout_s = read_timeout_s
        self._slow_read_timeout_s = slow_read_timeout_s
        self._lock = threading.RLock()
        self._links: dict[str, _Link] = {}
        # Every node seen since start, so pages still name a node that went away.
        self._names: dict[str, str] = {}
        self._channels: dict[str, _Channel] = {}
        self._waiters: dict[str, _Waiter] = {}
        self._ids = itertools.count(1)

    def attach(self, hello: NodeHello, generation: int, send: Send) -> None:
        """A peer said hello; pages still on its previous connection end and reconnect."""
        with self._lock:
            self._links[hello.node_id] = _Link(hello, generation, send)
            self._names[hello.node_id] = hello.name
            stale = self._end_node(hello.node_id)
        for channel in stale:
            channel.end("it reconnected")

    def detach(self, node_id: str, generation: int) -> None:
        """The peer's connection closed: its pages are told it went offline and its reads fail."""
        with self._lock:
            link = self._links.get(node_id)
            if link is None or link.generation != generation:
                return
            del self._links[node_id]
            ended = self._end_node(node_id)
            failed = [waiter for waiter in self._waiters.values() if waiter.node_id == node_id]
            for waiter in failed:
                waiter.error = "the link closed"
                waiter.done.set()
        for channel in ended:
            channel.end("the link closed")

    def _end_node(self, node_id: str) -> list[_Channel]:
        ended = [channel_id for channel_id, channel in self._channels.items() if channel.node_id == node_id]
        return [self._channels.pop(channel_id) for channel_id in ended]

    def name(self, node_id: str) -> str:
        with self._lock:
            return self._names.get(node_id, node_id)

    def open_channel(self, node_id: str, client_name: str, deliver: Deliver, end: End) -> str:
        """Start streaming the node's session to a page; raises NodeOffline when it is not linked."""
        with self._lock:
            link = self._links.get(node_id)
            if link is None:
                raise NodeOffline("not linked to the hub")
            channel_id = f"channel-{next(self._ids)}"
            self._channels[channel_id] = _Channel(node_id, deliver, end)
            try:
                link.send({"type": "channel_open", "channel": channel_id, "client_name": client_name})
            except Exception as exc:
                self._channels.pop(channel_id, None)
                raise NodeOffline(f"the link closed: {exc}") from exc
        return channel_id

    def close_channel(self, channel_id: str) -> None:
        """The page went away: the peer drops its listener."""
        with self._lock:
            channel = self._channels.pop(channel_id, None)
            link = self._links.get(channel.node_id) if channel is not None else None
            if link is None:
                return
            try:
                link.send({"type": "channel_close", "channel": channel_id})
            except Exception:  # The link is going down; the peer drops every channel then.
                pass

    def read(self, node_id: str, path: str, params: dict[str, str]) -> LinkReply:
        """Answer one allowlisted page read on the node; blocks, raises NodeOffline."""
        if path not in NODE_READS:
            return LinkReply(403, {"detail": f"{path} is not read from other nodes"})
        timeout_s = self._slow_read_timeout_s if path in SLOW_READS else self._read_timeout_s
        with self._lock:
            link = self._links.get(node_id)
            if link is None:
                raise NodeOffline("not linked to the hub")
            read_id = f"read-{next(self._ids)}"
            waiter = self._waiters[read_id] = _Waiter(node_id)
            try:
                link.send({"type": "read", "id": read_id, "path": path, "params": params})
            except Exception as exc:
                self._waiters.pop(read_id, None)
                raise NodeOffline(f"the link closed: {exc}") from exc
        try:
            if not waiter.done.wait(timeout_s):
                raise NodeOffline(f"no answer in {timeout_s:g} s")
        finally:
            with self._lock:
                self._waiters.pop(read_id, None)
        if waiter.reply is None:
            raise NodeOffline(waiter.error)
        return waiter.reply

    def on_frame(self, node_id: str, frame: dict[str, Any]) -> None:
        """A relay frame from the peer `node_id` (the link session checked its hello)."""
        kind = frame.get("type")
        if kind == "channel":
            message = frame.get("message")
            with self._lock:
                channel = self._channels.get(str(frame.get("channel")))
            if channel is not None and channel.node_id == node_id and isinstance(message, dict):
                channel.deliver(message)
        elif kind == "read_response":
            with self._lock:
                waiter = self._waiters.get(str(frame.get("id")))
            if waiter is not None and waiter.node_id == node_id:
                waiter.reply = LinkReply(int(frame.get("status") or 0), frame.get("body"))
                waiter.done.set()


class PeerRelay:
    """The peer's side: answers the hub's channel and read frames with its own session and reads.

    `open_session` gives a new channel's first messages (connection ready, hydrate); `add_listener`
    attaches a broker listener and returns its remover; `answer_read` answers one allowlisted read;
    `run_in_background` runs a read off the link thread, which must keep reading frames (a read may
    itself ask the hub).
    """

    def __init__(
        self,
        *,
        open_session: Callable[[str], list[dict[str, Any]]],
        add_listener: Callable[[Deliver], Callable[[], None]],
        answer_read: Callable[[str, dict[str, str]], LinkReply],
        state: Callable[[], dict[str, Any]],
        run_in_background: Callable[[Callable[[], None]], None],
        log: Callable[[str], None],
    ) -> None:
        self._open_session = open_session
        self._add_listener = add_listener
        self._answer_read = answer_read
        self._state = state
        self._run_in_background = run_in_background
        self._log = log
        self._lock = threading.RLock()
        self._send: Send | None = None
        self._channels: dict[str, Callable[[], None]] = {}
        self._remove_state_listener: Callable[[], None] | None = None
        self._last_state: dict[str, Any] | None = None
        # Channels the hub opened before this side saw its welcome (the hub may send both at once).
        self._early: list[str] = []

    def link_up(self, send: Send) -> None:
        """The hub welcomed this peer: tell it the ship and routine, and again whenever they change."""
        with self._lock:
            self._send = send
            self._last_state = None
            self._remove_state_listener = self._add_listener(lambda _message: self._send_state())
            early, self._early = self._early, []
        self._send_state()
        for channel_id in early:
            self._open(channel_id)

    def link_down(self) -> None:
        """The link closed: every hub page channel goes with it."""
        with self._lock:
            self._send = None
            self._early.clear()
            removers = list(self._channels.values())
            self._channels.clear()
            if self._remove_state_listener is not None:
                removers.append(self._remove_state_listener)
                self._remove_state_listener = None
        for remove in removers:
            remove()

    def channels(self) -> int:
        with self._lock:
            return len(self._channels)

    def on_frame(self, frame: dict[str, Any]) -> None:
        kind = frame.get("type")
        if kind == "channel_open":
            self._open(str(frame.get("channel")))
        elif kind == "channel_close":
            with self._lock:
                channel_id = str(frame.get("channel"))
                if channel_id in self._early:
                    self._early.remove(channel_id)
                remove = self._channels.pop(channel_id, None)
            if remove is not None:
                remove()
        elif kind == "read":
            read_id = frame.get("id")
            path = str(frame.get("path"))
            params = frame.get("params")
            self._run_in_background(lambda: self._read(read_id, path, params))

    def _open(self, channel_id: str) -> None:
        # Held while the first messages go out, so broker events wait behind the hydrate.
        with self._lock:
            if self._send is None:
                self._early.append(channel_id)
                return
            if channel_id in self._channels:
                return

            def deliver(message: dict[str, Any]) -> None:
                with self._lock:
                    if channel_id in self._channels:
                        self._try_send({"type": "channel", "channel": channel_id, "message": message})

            self._channels[channel_id] = self._add_listener(deliver)
            for message in self._open_session(channel_id):
                self._try_send({"type": "channel", "channel": channel_id, "message": message})

    def _read(self, read_id: Any, path: str, params: Any) -> None:
        if path not in NODE_READS:
            reply = LinkReply(403, {"detail": f"{path} is not read from other nodes"})
        elif not isinstance(params, dict):
            reply = LinkReply(400, {"detail": "read params must be an object"})
        else:
            try:
                reply = self._answer_read(path, {str(key): str(value) for key, value in params.items()})
            except Exception as exc:  # One failed read must not end the link.
                self._log(f"Hub read {path} failed: {exc}")
                reply = LinkReply(500, {"detail": str(exc) or type(exc).__name__})
        self._try_send({"type": "read_response", "id": read_id, "status": reply.status, "body": reply.body})

    def _send_state(self) -> None:
        state = self._state()
        with self._lock:
            if state == self._last_state:
                return
            self._last_state = state
        self._try_send({"type": "node_state", "state": state})

    def _try_send(self, frame: dict[str, Any]) -> None:
        with self._lock:
            send = self._send
        if send is None:
            return
        try:
            send(frame)
        except Exception:  # A broken link: the link thread notices and tears every channel down.
            pass
