from __future__ import annotations

from dataclasses import asdict
from threading import RLock
from typing import Any

from edcr.route_recommend import RouteRecommendations, route_key

from edcr.control_room.protocol.events import ActivityLogEntry, AnnouncementEvent
from edcr.inara.trade_routes import TradeRoute
from edcr.routing.route_cache import RouteCache, RouteRequestKey
from edcr.routing.types import Route


class ControlRoomServerState:
    def __init__(
        self,
        *,
        activity_log_limit: int = 2000,
        announcement_limit: int = 100,
        spansh_route_cache_size: int = 16,
    ) -> None:
        self._recommend_lock = RLock()
        self._recommendations: RouteRecommendations | None = None
        self._dismissed_recommendations: set[str] = set()
        self._activity_log_limit = activity_log_limit
        self._announcement_limit = announcement_limit
        self._activity_log: list[ActivityLogEntry] = []
        self._announcements: list[AnnouncementEvent] = []
        self._selected_trade_route: TradeRoute | None = None
        self._running_trade_route: TradeRoute | None = None
        self._spansh_route_cache = RouteCache(max_entries=spansh_route_cache_size)
        self._active_spansh_route_id: str | None = None

    def replace_activity_log(self, entries: list[ActivityLogEntry]) -> None:
        self._activity_log = list(entries)[-self._activity_log_limit :]

    def record_activity_log(self, entry: ActivityLogEntry) -> None:
        self._activity_log.append(entry)
        self._activity_log = self._activity_log[-self._activity_log_limit :]

    def record_announcement(self, event: AnnouncementEvent) -> None:
        self._announcements.append(event)
        self._announcements = self._announcements[-self._announcement_limit :]

    def activity_log_entries(self) -> list[ActivityLogEntry]:
        return list(self._activity_log)

    def announcements(self) -> list[AnnouncementEvent]:
        return list(self._announcements)

    def set_selected_trade_route(self, route: TradeRoute | None) -> None:
        with self._recommend_lock:
            old = route_key(asdict(self._selected_trade_route)) if self._selected_trade_route else None
            new = route_key(asdict(route)) if route else None
            if old != new:
                self._dismissed_recommendations.clear()
                # Previous gains were measured against a different selection.
                self._recommendations = None
            self._selected_trade_route = route

    def selected_trade_route(self) -> TradeRoute | None:
        return self._selected_trade_route

    def set_route_recommendations(self, recommendations: RouteRecommendations) -> None:
        with self._recommend_lock:
            self._recommendations = recommendations

    def dismiss_route_recommendation(self, key: str) -> bool:
        with self._recommend_lock:
            if self._recommendations is None or not any(row["key"] == key for row in self._recommendations.routes):
                return False
            self._dismissed_recommendations.add(key)
            return True

    def route_recommendations(self) -> dict[str, Any] | None:
        with self._recommend_lock:
            if self._recommendations is None:
                return None
            payload = self._recommendations.to_payload()
            payload["routes"] = [row for row in payload["routes"] if row["key"] not in self._dismissed_recommendations]
            payload["dismissed"] = len(self._recommendations.routes) - len(payload["routes"])
            return payload

    def set_running_trade_route(self, route: TradeRoute | None) -> None:
        self._running_trade_route = route

    def running_trade_route(self) -> TradeRoute | None:
        return self._running_trade_route

    def cache_spansh_route(self, route: Route, *, request_key: RouteRequestKey) -> str:
        return self._spansh_route_cache.put(route, request_key=request_key)

    def get_spansh_route(self, route_id: str) -> Route | None:
        return self._spansh_route_cache.get(route_id)

    def set_active_spansh_route(self, route_id: str | None) -> None:
        self._active_spansh_route_id = route_id or None

    def active_spansh_route_id(self) -> str | None:
        return self._active_spansh_route_id
