"""Hub-owned peer recommendations, with opt-in delivery to node-owned state."""
from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any

from edcr.control_room.server.commands import trade_route_from_payload
from edcr.control_room.server.state import ControlRoomServerState
from edcr.route_recommend import RouteRecommendations, RouteRecommendSettings
from edcr.route_recommend_node import RecommendationAnnouncer


class PeerRecommendations:
    def __init__(self, *, settings: RouteRecommendSettings, time_fn: Callable[[], float],
                 send: Callable[[str, dict[str, Any]], bool],
                 render: Callable[..., str | None], callout: Callable[[str, str], None],
                 name: Callable[[str], str]) -> None:
        self.owns = not settings.deliver_to_peers
        self._settings, self._time, self._send = settings, time_fn, send
        self._render, self._callout, self._name = render, callout, name
        self._lock = RLock()
        self._states: dict[str, ControlRoomServerState] = {}
        self._announcers: dict[str, RecommendationAnnouncer] = {}
        self._listeners: dict[str, list[Callable[[], None]]] = {}

    def _state(self, node_id: str) -> ControlRoomServerState:
        if node_id not in self._states:
            self._states[node_id] = ControlRoomServerState()
        return self._states[node_id]

    def selection(self, node_id: str, selected: dict[str, Any] | None) -> None:
        if self.owns:
            with self._lock:
                self._state(node_id).set_selected_trade_route(trade_route_from_payload(selected) if selected else None)

    def current(self, node_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._state(node_id).route_recommendations()

    def deliver(self, node_id: str, result: RouteRecommendations) -> bool:
        if not self.owns:
            return self._send(node_id, {"type": "route_recommendation", "recommendations": result.to_payload()})
        with self._lock:
            state = self._state(node_id)
            state.set_route_recommendations(result)
            if node_id not in self._announcers:
                self._announcers[node_id] = RecommendationAnnouncer(settings=self._settings, time_fn=self._time,
                    announce=lambda message, **values: self._announce(node_id, message, **values))
            self._announcers[node_id].consider(state.route_recommendations())
        self._publish(node_id)
        return True

    def _announce(self, node_id: str, message, **values: object) -> None:
        line = self._render(message, **values)
        if line:
            self._callout(node_id, f"{self._name(node_id)}: {line}")

    def dismiss(self, node_id: str, key: str) -> bool:
        with self._lock:
            accepted = self._state(node_id).dismiss_route_recommendation(key)
        if accepted:
            self._publish(node_id)
        return accepted

    def listen(self, node_id: str, changed: Callable[[], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.setdefault(node_id, []).append(changed)
        def remove() -> None:
            with self._lock:
                self._listeners[node_id].remove(changed)
        return remove

    def _publish(self, node_id: str) -> None:
        with self._lock:
            listeners = list(self._listeners.get(node_id, ()))
        for changed in listeners:
            changed()
