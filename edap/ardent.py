"""On-demand station and system lookups from the Ardent Insight API (research 0009, plan 0014 slice 3).

`GET /v2/system/name/{name}/stations` lists a system's stations with `marketId`, `stationName`,
`stationType`, `distanceToArrival` (Ls), `maxLandingPadSize` (1/2/3), `systemAddress`,
`systemX/Y/Z` and `updatedAt`. A system with no stations listed falls back to
`GET /v2/system/name/{name}` (`systemAddress`, `systemX/Y/Z`, `updatedAt`) for coordinates.

Each request has a short timeout and a system is fetched at most once per process; a failed
lookup is retried only after `retry_after_s`, so a slow or down Ardent costs one wait, not one
per page refresh. Found rows go to `save` (the EDDN store when there is one).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable
from urllib.parse import quote

from edap.eddn.messages import EddnUpdate, StationInfo, SystemPosition
from edap.trade_trip import PartialFacts

ARDENT_BASE_URL = "https://api.ardent-insight.com/v2"
ARDENT_TIMEOUT_S = 3.0
ARDENT_RETRY_AFTER_S = 600.0
_PADS = {1: "S", 2: "M", 3: "L"}

# Fetch decoded JSON from a URL within a timeout in seconds; raises on any failure.
FetchJson = Callable[[str, float], object]


class ArdentError(Exception):
    """A lookup that failed (network, HTTP status or an unexpected body)."""


@dataclass(frozen=True)
class ArdentSystem:
    position: SystemPosition | None
    stations: tuple[StationInfo, ...]


class ArdentLookup:
    def __init__(
        self,
        fetch_json: FetchJson,
        *,
        now: Callable[[], float],
        save: Callable[[list[EddnUpdate]], None],
        log: Callable[[str], None],
        base_url: str = ARDENT_BASE_URL,
        timeout_s: float = ARDENT_TIMEOUT_S,
        retry_after_s: float = ARDENT_RETRY_AFTER_S,
    ) -> None:
        self._fetch_json = fetch_json
        self._now = now
        self._save = save
        self._log = log
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._retry_after_s = retry_after_s
        self._systems: dict[str, ArdentSystem] = {}
        self._failed_at: dict[str, float] = {}
        self._lock = threading.Lock()

    def __call__(self, market_id: int, station: str, system: str) -> PartialFacts:
        """A `FactLookup`: what Ardent knows about one station; nothing when the lookup fails."""
        found = self.system(system)
        if found is None:
            return PartialFacts()
        row = next((info for info in found.stations if info.market_id == market_id), None)
        if row is None:
            key = station.casefold()
            row = next((info for info in found.stations if info.name.casefold() == key), None)
        position = found.position
        return PartialFacts(
            coords=(position.x, position.y, position.z) if position is not None else None,
            dist_ls=row.dist_ls if row is not None else None,
            station_type=(row.type or None) if row is not None else None,
        )

    def system(self, name: str) -> ArdentSystem | None:
        key = name.casefold()
        with self._lock:
            if key in self._systems:
                return self._systems[key]
            failed_at = self._failed_at.get(key)
            if failed_at is not None and self._now() - failed_at < self._retry_after_s:
                return None
        try:
            found = self._fetch_system(name)
        except ArdentError as exc:
            self._log(f"Ardent lookup for {name} failed: {exc}")
            with self._lock:
                self._failed_at[key] = self._now()
            return None
        with self._lock:
            self._systems[key] = found
            self._failed_at.pop(key, None)
        updates: list[EddnUpdate] = [*([found.position] if found.position is not None else []), *found.stations]
        if updates:
            self._save(updates)
        return found

    def _fetch_system(self, name: str) -> ArdentSystem:
        url = f"{self._base_url}/system/name/{quote(name, safe='')}"
        rows = self._get(f"{url}/stations")
        if not isinstance(rows, list):
            raise ArdentError("stations response is not a list")
        stations = tuple(info for info in (_station_info(row) for row in rows) if info is not None)
        position = next((p for p in (_system_position(row, name) for row in rows) if p is not None), None)
        if position is None:
            position = _system_position(self._get(url), name)
        return ArdentSystem(position=position, stations=stations)

    def _get(self, url: str) -> object:
        try:
            return self._fetch_json(url, self._timeout_s)
        except ArdentError:
            raise
        except Exception as exc:  # The injected fetch may raise anything its client raises.
            raise ArdentError(str(exc) or type(exc).__name__) from exc


def httpx_fetch_json(user_agent: str) -> FetchJson:
    """The production fetch: one GET with an identifying User-Agent; a 404 is an unknown system."""
    import httpx

    def fetch(url: str, timeout_s: float) -> object:
        try:
            response = httpx.get(url, headers={"User-Agent": user_agent}, timeout=timeout_s)
        except httpx.HTTPError as exc:
            raise ArdentError(str(exc) or type(exc).__name__) from exc
        if response.status_code == 404:
            return []
        if response.status_code != 200:
            raise ArdentError(f"HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise ArdentError("response is not JSON") from exc

    return fetch


def _timestamp(value: object) -> float | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _system_position(row: object, name: str) -> SystemPosition | None:
    if not isinstance(row, dict):
        return None
    address = row.get("systemAddress")
    coords = [_number(row.get(axis)) for axis in ("systemX", "systemY", "systemZ")]
    timestamp = _timestamp(row.get("updatedAt"))
    if not isinstance(address, int) or any(value is None for value in coords) or timestamp is None:
        return None
    x, y, z = coords
    return SystemPosition(address=address, name=str(row.get("systemName") or name), x=x, y=y, z=z,  # type: ignore[arg-type]
                          timestamp=timestamp)


def _station_info(row: object) -> StationInfo | None:
    if not isinstance(row, dict):
        return None
    market_id = row.get("marketId")
    address = row.get("systemAddress")
    name = row.get("stationName")
    timestamp = _timestamp(row.get("updatedAt"))
    if not isinstance(market_id, int) or not isinstance(address, int) or not isinstance(name, str) or timestamp is None:
        return None
    return StationInfo(
        market_id=market_id,
        system_address=address,
        system_name=str(row.get("systemName") or ""),
        name=name,
        type=str(row.get("stationType") or ""),
        dist_ls=_number(row.get("distanceToArrival")),
        max_pad=_PADS.get(row.get("maxLandingPadSize"), ""),  # type: ignore[arg-type]
        timestamp=timestamp,
    )


def store_saver(apply: Callable[[EddnUpdate], bool], commit: Callable[[], None]) -> Callable[[list[EddnUpdate]], None]:
    """Write Ardent rows into the EDDN store, so `/routes` gains the coordinates and station details too."""

    def save(updates: Iterable[EddnUpdate]) -> None:
        for update in updates:
            apply(update)
        commit()

    return save
