"""Frames on the hub link, as JSON objects with a `type`.

Peer to hub: `hello` (node_id, name, version), `item` (seq, kind, body: an outbox entry),
`request` (id, kind, body) and `ping`. Hub to peer: `welcome` (name, version, node_id), `ack`
(seq; `error` when the hub dropped a bad item), `nack` (seq, error: kept, sent again on the next
connection), `response` (id, status, body), `pong` and `error` (detail; the hub then closes).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from edap.eddn.messages import EddnUpdate, MarketSnapshot, StationInfo, StationTypeSeen, SystemPosition

PEER_LINK_PATH = "/api/peer-link"

# Outbox item kinds.
ITEM_MARKET = "market"
ITEM_STATION_FACTS = "station_facts"

# Requests a peer asks the hub.
REQUEST_HAUL_SEARCH = "haul_search"
REQUEST_EDDN_ROUTES = "eddn_routes"
REQUEST_EDDN_STATUS = "eddn_status"
REQUEST_STATION_FACTS = "station_facts"


class HubUnreachable(OSError):
    """The hub link is down, or the hub did not answer in time."""


class LinkClosed(Exception):
    """The other end closed the link, or it broke."""


class LinkConnection(Protocol):
    """One open link. Production wraps a websocket; tests use an in-memory pair."""

    def send(self, frame: dict[str, Any]) -> None: ...

    def receive(self, timeout_s: float) -> dict[str, Any] | None:
        """The next frame, or None after `timeout_s` without one; raises LinkClosed."""
        ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class LinkReply:
    # HTTP-style status, so peers answer pages with the hub's status code unchanged.
    status: int
    body: Any


def response_frame(request_id: str, reply: LinkReply) -> dict[str, Any]:
    return {"type": "response", "id": request_id, "status": reply.status, "body": reply.body}


_UPDATE_KINDS: dict[str, type] = {
    "system": SystemPosition,
    "station": StationInfo,
    "station_type": StationTypeSeen,
}


def encode_update(update: EddnUpdate) -> dict[str, Any]:
    """A station or system fact as JSON; markets travel as recent-market entries instead."""
    if isinstance(update, MarketSnapshot):
        raise ValueError("markets travel as recent-market entries")
    kind = next(name for name, cls in _UPDATE_KINDS.items() if isinstance(update, cls))
    return {"kind": kind, **asdict(update)}


def decode_update(value: object) -> EddnUpdate | None:
    if not isinstance(value, dict):
        return None
    cls = _UPDATE_KINDS.get(str(value.get("kind")))
    if cls is None:
        return None
    fields = {key: item for key, item in value.items() if key != "kind"}
    try:
        return cls(**fields)
    except TypeError:
        return None
