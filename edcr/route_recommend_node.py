"""Node-owned recommendation list and rate-limited callouts; no route execution."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from edcr.route_recommend import RouteRecommendations, RouteRecommendSettings
from edcr.tts import AnnouncementId, format_credits_short


class RecommendationAnnouncer:
    def __init__(self, *, settings: RouteRecommendSettings, time_fn: Callable[[], float],
                 announce: Callable[..., None]) -> None:
        self._settings = settings
        self._time = time_fn
        self._announce = announce
        self._last_key: str | None = None
        self._last_rate = 0.0
        self._last_spoken: float | None = None

    def consider(self, payload: dict[str, Any]) -> None:
        routes = payload["routes"]
        if not self._settings.enabled or not routes:
            return
        best = routes[0]
        rate = best["profit_per_hour"]
        now = self._time()
        if self._last_spoken is not None and now - self._last_spoken < self._settings.tts_gap_s:
            return
        if best["key"] == self._last_key and rate < self._last_rate * (1 + self._settings.min_gain):
            return
        baseline = payload["baseline_cr_h"]
        self._announce(
            AnnouncementId.ROUTE_RECOMMENDED,
            count="One" if len(routes) == 1 else str(len(routes)),
            routes_word="route" if len(routes) == 1 else "routes",
            from_station=best["station_1"]["station"], to_station=best["station_2"]["station"],
            gain_short=format_credits_short(round(rate - baseline if baseline is not None else rate)),
            cr_h_short=format_credits_short(round(rate)), more=" more" if baseline is not None else "",
        )
        self._last_key, self._last_rate, self._last_spoken = best["key"], rate, now


class RecommendationReceiver:
    """One delivery stores state, publishes a hydrate, then considers a callout."""

    def __init__(self, *, store: Callable[[RouteRecommendations], None], current: Callable[[], dict[str, Any] | None],
                 publish: Callable[[], None], announcer: RecommendationAnnouncer) -> None:
        self._store, self._current, self._publish, self._announcer = store, current, publish, announcer

    def receive(self, recommendations: RouteRecommendations) -> None:
        self._store(recommendations)
        self._publish()
        payload = self._current()
        if payload is not None:
            self._announcer.consider(payload)
