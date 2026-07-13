"""In-memory cache of Spansh routes keyed by request parameters.

Keeps the neutron-travel dispatch payload small: clients hand the server a
short route_id from a previous `/api/route-compare` response, and the server
resolves it back to the full Route without a Spansh refetch. LRU-evicting so
long-running sessions do not grow unbounded.
"""
from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass

from edap.routing.types import Route


@dataclass(frozen=True)
class RouteRequestKey:
    source_system: str
    destination_system: str
    range_ly: float
    efficiency: int
    supercharge_multiplier: int


def _hash_key(key: RouteRequestKey) -> str:
    payload = (
        f"{key.source_system}|{key.destination_system}|{key.range_ly:.6f}|"
        f"{key.efficiency}|{key.supercharge_multiplier}"
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


class RouteCache:
    def __init__(self, *, max_entries: int = 16) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, Route] = OrderedDict()

    def put(self, route: Route, *, request_key: RouteRequestKey) -> str:
        route_id = _hash_key(request_key)
        if route_id in self._entries:
            self._entries.move_to_end(route_id)
            self._entries[route_id] = route
            return route_id
        self._entries[route_id] = route
        if len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
        return route_id

    def get(self, route_id: str) -> Route | None:
        route = self._entries.get(route_id)
        if route is not None:
            self._entries.move_to_end(route_id)
        return route

    def __len__(self) -> int:
        return len(self._entries)
