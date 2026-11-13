"""Hub pages looking at and driving a peer (plan 0015 steps 5 and 6) over the link.

A hub page opens its session with `?node=<node_id>`. For a peer the hub opens a channel over the peer
link; the peer attaches a broker listener and streams the same session messages (connection ready,
hydrate, broker events) back, and the hub hands them to the page. The page's `command.*` messages go
down the channel; the peer runs them one at a time through its normal session handler and the answer
comes back on the channel unchanged. Node-specific HTTP reads go down as `read` frames and are
answered only for `NODE_READS`; `POST /api/command` and `/api/stop` go down as `act` frames.

The peer takes these frames only from the link it dialled itself: nothing listens for them on a peer.

Hub to peer: `channel_open` (channel, client_name), `channel_close` (channel), `channel_command`
(channel, message), `read` (id, path, params), `act` (id, path, body) and `voice_mute` (muted: whether
the node stops speaking its own callouts; see `edcr.hub.voice`).
Peer to hub: `channel` (channel, message), `read_response` (id, status, body), `node_state` (state),
and `callout` (text: each callout the node speaks, for the hub to voice; see `edcr.hub.voice`).
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass
from typing import Any, Callable

from edcr.control_room.server.messages import protocol_message
from edcr.hub.peer import NodeHello
from edcr.hub.protocol import LinkReply
from edcr.hub.voice import CALLOUT_FRAME, VOICE_MUTE_FRAME, callout_text

# The page reads a hub relays to the node a page looks at; everything else the hub answers itself.
NODE_READS = frozenset({
    "/api/route-compare",
    "/api/route-compare/config",
    "/api/spansh-route",
    # The hub owns the market store, but routes start from the node's ship; the peer asks the hub back.
    "/api/eddn-routes",
    # The node's own journal trade ledger, shown beside the hub's central haul history.
    "/api/journal-ledger",
    # The hub fits the trip time, but for the node's ship; the peer asks the hub back.
    "/api/time-model",
})
# Reads that ask Spansh and can take minutes.
SLOW_READS = frozenset({"/api/route-compare", "/api/spansh-route"})
# The page actions a hub relays to the node a page drives (POST, JSON body).
NODE_ACTIONS = frozenset({"/api/command", "/api/stop"})
# Session commands that search or plot and can take minutes; the rest answer at once.
SLOW_COMMANDS = frozenset({"command.search_haul_routes", "command.dispatch_route_all_in_one",
                           "command.dispatch_spansh_route"})
# Frames from the hub that belong to the relay.
HUB_RELAY_FRAMES = frozenset({"channel_open", "channel_close", "channel_command", "read", "act", VOICE_MUTE_FRAME})
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


def relay_error(message_id: Any, error_code: str, error_message: str) -> dict[str, Any]:
    """A session `response.error` for a relayed command, shaped as the server's own."""
    return protocol_message("response.error", {
        "error_code": error_code,
        "error_message": error_message,
        "recommended_action": "Check the node and its activity log, then try again.",
        "retryable": True,
    }, correlation_message_id=str(message_id) if message_id is not None else None)


def node_state(data: object) -> dict[str, Any]:
    """What the hub's node picker shows for a node: its ship and the routine it runs. The hub's Markets
    page prices trips with the ship's hold and laden range."""
    ship = getattr(data, "ship", None)
    routine = getattr(data, "routine", None)
    return {
        "ship": {"id": getattr(ship, "ship_id", None), "type": getattr(ship, "ship_type", None),
                 "name": getattr(ship, "ship_name", None), "cargo_capacity": getattr(ship, "cargo_capacity", None),
                 "laden_jump_range_ly": getattr(ship, "laden_jump_range_ly", None)},
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

    def send(self, node_id: str, frame: dict[str, Any]) -> bool:
        """Send one frame to a linked peer; False when it is not linked or the link closed."""
        with self._lock:
            link = self._links.get(node_id)
            if link is None:
                return False
            try:
                link.send(frame)
            except Exception:  # The link is going down.
                return False
        return True

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

    def command_timeout_s(self, message_type: str) -> float:
        """How long a page waits for the node to answer a session command before it is told it failed."""
        return self._slow_read_timeout_s if message_type in SLOW_COMMANDS else self._read_timeout_s

    def command(self, channel_id: str, message: dict[str, Any]) -> None:
        """Send a page's session command down its channel; the answer comes back as a channel message.
        Raises NodeOffline when the channel or its link is gone."""
        with self._lock:
            channel = self._channels.get(channel_id)
            link = self._links.get(channel.node_id) if channel is not None else None
            if link is None:
                raise NodeOffline("not linked to the hub")
            try:
                link.send({"type": "channel_command", "channel": channel_id, "message": message})
            except Exception as exc:
                raise NodeOffline(f"the link closed: {exc}") from exc

    def read(self, node_id: str, path: str, params: dict[str, str]) -> LinkReply:
        """Answer one allowlisted page read on the node; blocks, raises NodeOffline."""
        if path not in NODE_READS:
            return LinkReply(403, {"detail": f"{path} is not read from other nodes"})
        timeout_s = self._slow_read_timeout_s if path in SLOW_READS else self._read_timeout_s
        return self._ask(node_id, {"type": "read", "path": path, "params": params}, timeout_s)

    def act(self, node_id: str, path: str, body: Any) -> LinkReply:
        """Run one allowlisted page action (command, stop) on the node; blocks, raises NodeOffline."""
        if path not in NODE_ACTIONS:
            return LinkReply(403, {"detail": f"{path} is not run on other nodes"})
        return self._ask(node_id, {"type": "act", "path": path, "body": body}, self._read_timeout_s)

    def _ask(self, node_id: str, frame: dict[str, Any], timeout_s: float) -> LinkReply:
        with self._lock:
            link = self._links.get(node_id)
            if link is None:
                raise NodeOffline("not linked to the hub")
            read_id = f"read-{next(self._ids)}"
            waiter = self._waiters[read_id] = _Waiter(node_id)
            try:
                link.send({**frame, "id": read_id})
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
    """The peer's side: answers the hub's channel, command, read and act frames with its own session,
    commands and reads.

    `open_session` gives a new channel's first messages (connection ready, hydrate); `add_listener`
    attaches a broker listener and returns its remover; `answer_command` runs one session command
    for a channel and gives its answer (None for none); `answer_read` answers one allowlisted read;
    `answer_action` runs one allowlisted action; `set_muted` mutes or unmutes this node's own
    callouts (the hub voices them instead; unmuted whenever the link drops); `run_in_background` runs work off the link thread,
    which must keep reading frames (a read or command may itself ask the hub). A channel's commands
    run one at a time in order, as on a local session.
    """

    def __init__(
        self,
        *,
        open_session: Callable[[str], list[dict[str, Any]]],
        add_listener: Callable[[Deliver], Callable[[], None]],
        answer_command: Callable[[str, dict[str, Any]], dict[str, Any] | None],
        answer_read: Callable[[str, dict[str, str]], LinkReply],
        answer_action: Callable[[str, Any], LinkReply],
        state: Callable[[], dict[str, Any]],
        set_muted: Callable[[bool], None],
        run_in_background: Callable[[Callable[[], None]], None],
        log: Callable[[str], None],
    ) -> None:
        self._open_session = open_session
        self._add_listener = add_listener
        self._answer_command = answer_command
        self._answer_read = answer_read
        self._answer_action = answer_action
        self._state = state
        self._set_muted = set_muted
        self._muted = False
        self._run_in_background = run_in_background
        self._log = log
        self._lock = threading.RLock()
        self._send: Send | None = None
        self._channels: dict[str, Callable[[], None]] = {}
        self._remove_state_listener: Callable[[], None] | None = None
        self._last_state: dict[str, Any] | None = None
        # Channels the hub opened before this side saw its welcome (the hub may send both at once).
        self._early: list[str] = []
        # Each channel's commands still to run, and the channels with a runner at work.
        self._commands: dict[str, list[dict[str, Any]]] = {}
        self._running: set[str] = set()

    def link_up(self, send: Send) -> None:
        """The hub welcomed this peer: tell it the ship and routine, and again whenever they change,
        and send up each callout this node speaks (live only: one missed while the link is down is gone)."""
        with self._lock:
            self._send = send
            self._last_state = None
            self._remove_state_listener = self._add_listener(self._on_event)
            early, self._early = self._early, []
        self._send_state()
        for channel_id in early:
            self._open(channel_id)

    def link_down(self) -> None:
        """The link closed: every hub page channel goes with it, and the node speaks its own callouts again."""
        self._mute(False)
        with self._lock:
            self._send = None
            self._early.clear()
            removers = list(self._channels.values())
            self._channels.clear()
            self._commands.clear()
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
        if kind == VOICE_MUTE_FRAME:
            self._mute(frame.get("muted") is True)
        elif kind == "channel_open":
            self._open(str(frame.get("channel")))
        elif kind == "channel_close":
            with self._lock:
                channel_id = str(frame.get("channel"))
                if channel_id in self._early:
                    self._early.remove(channel_id)
                remove = self._channels.pop(channel_id, None)
                self._commands.pop(channel_id, None)
            if remove is not None:
                remove()
        elif kind == "channel_command":
            self._queue_command(str(frame.get("channel")), frame.get("message"))
        elif kind == "read":
            read_id = frame.get("id")
            path = str(frame.get("path"))
            params = frame.get("params")
            self._run_in_background(lambda: self._read(read_id, path, params))
        elif kind == "act":
            read_id = frame.get("id")
            path = str(frame.get("path"))
            body = frame.get("body")
            self._run_in_background(lambda: self._act(read_id, path, body))

    def _mute(self, muted: bool) -> None:
        with self._lock:
            if muted == self._muted:
                return
            self._muted = muted
            self._set_muted(muted)
        self._log("The hub voices this node: its own speakers are muted" if muted
                  else "This node speaks its own callouts again")

    def _queue_command(self, channel_id: str, message: Any) -> None:
        with self._lock:
            if channel_id not in self._channels:
                self._log(f"Hub command for channel {channel_id}, which is not open here: dropped")
                return
            self._commands.setdefault(channel_id, []).append(message)
            if channel_id in self._running:
                return
            self._running.add(channel_id)
        self._run_in_background(lambda: self._run_commands(channel_id))

    def _run_commands(self, channel_id: str) -> None:
        while True:
            with self._lock:
                queued = self._commands.get(channel_id)
                if not queued or channel_id not in self._channels:
                    self._running.discard(channel_id)
                    self._commands.pop(channel_id, None)
                    return
                message = queued.pop(0)
            answer = self._command(channel_id, message)
            if answer is not None:
                with self._lock:
                    if channel_id in self._channels:
                        self._try_send({"type": "channel", "channel": channel_id, "message": answer})

    def _command(self, channel_id: str, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict) or not str(message.get("message_type", "")).startswith("command."):
            message_id = message.get("message_id") if isinstance(message, dict) else None
            return relay_error(message_id, "invalid_command", "Only command messages run on a node.")
        try:
            return self._answer_command(channel_id, message)
        except Exception as exc:  # One failed command must not end the link.
            self._log(f"Hub command {message.get('message_type')} failed: {exc}")
            return relay_error(message.get("message_id"), "command_execution_failed",
                               str(exc) or type(exc).__name__)

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

    def _act(self, read_id: Any, path: str, body: Any) -> None:
        if path not in NODE_ACTIONS:
            reply = LinkReply(403, {"detail": f"{path} is not run on other nodes"})
        else:
            try:
                reply = self._answer_action(path, body)
            except Exception as exc:  # One failed action must not end the link.
                self._log(f"Hub action {path} failed: {exc}")
                reply = LinkReply(500, {"detail": str(exc) or type(exc).__name__})
        self._try_send({"type": "read_response", "id": read_id, "status": reply.status, "body": reply.body})

    def _on_event(self, message: dict[str, Any]) -> None:
        text = callout_text(message)
        if text is not None:
            self._try_send({"type": CALLOUT_FRAME, "text": text})
            return
        self._send_state()

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
