"""Talk to a hub Control Room: the home server that runs route searches and keeps the market DB.

A peer (Steam Deck, travel Mac) forwards its searches here and pushes the markets it visits.
The HTTP transport is a plain function so tests swap in a fake.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

import httpx

from edap.config import HubConfig
from edap.recent_markets import MarketSnapshot, load_recent_markets, snapshot_entry


@dataclass(frozen=True)
class HubRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    params: Mapping[str, str]
    body: Any
    timeout_s: float


@dataclass(frozen=True)
class HubResponse:
    status_code: int
    # The decoded JSON body; a body that is not JSON becomes {"detail": <text>}.
    payload: Any


class HubUnreachable(OSError):
    """The hub did not answer: refused, timed out or the name did not resolve."""


HubTransport = Callable[[HubRequest], HubResponse]


def httpx_transport(request: HubRequest) -> HubResponse:
    try:
        response = httpx.request(
            request.method,
            request.url,
            headers=dict(request.headers),
            params=dict(request.params) or None,
            json=request.body,
            timeout=request.timeout_s,
        )
    except httpx.HTTPError as exc:
        raise HubUnreachable(str(exc) or type(exc).__name__) from exc
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text[:500]}
    return HubResponse(response.status_code, payload)


@dataclass(frozen=True)
class HubClient:
    config: HubConfig
    transport: HubTransport

    @property
    def host(self) -> str:
        return urlparse(self.config.url).netloc or self.config.url

    def get(self, path: str, params: Mapping[str, str]) -> HubResponse:
        return self._send("GET", path, params=params, body=None, timeout_s=self.config.timeout_s)

    def post(self, path: str, body: Any, *, timeout_s: float) -> HubResponse:
        return self._send("POST", path, params={}, body=body, timeout_s=timeout_s)

    def _send(self, method: str, path: str, *, params: Mapping[str, str], body: Any, timeout_s: float) -> HubResponse:
        return self.transport(
            HubRequest(
                method=method,
                url=f"{self.config.url}{path}",
                headers={"Authorization": f"Bearer {self.config.token}"},
                params=params,
                body=body,
                timeout_s=timeout_s,
            )
        )


def with_hub_source(payload: Any, host: str) -> Any:
    """Tag a forwarded JSON object so pages can say where the answer came from."""
    return {**payload, "hub": host} if isinstance(payload, dict) else payload


def hub_unreachable_detail(host: str, exc: Exception) -> str:
    return f"Hub {host} is unreachable: {exc}"


@dataclass
class HubMarketPusher:
    """Push newly visited markets to the hub instead of writing a local DB.

    The first push, and the first after a failure, sends every entry in the recent-markets file;
    the hub keeps the newest snapshot per station, so a resend is harmless.
    """

    client: HubClient
    log: Callable[[str], None]
    unsent: bool = True
    _seen: frozenset[tuple[int, str]] = field(default_factory=frozenset)

    def push_changes(self, recent_markets_file: Path) -> None:
        markets = load_recent_markets(recent_markets_file)
        current = frozenset((market.market_id, market.timestamp) for market in markets)
        if self.unsent:
            batch = markets
        else:
            batch = tuple(market for market in markets if (market.market_id, market.timestamp) not in self._seen)
        self._seen = current
        if not batch:
            return
        self.unsent = not self._push(batch)

    def _push(self, markets: tuple[MarketSnapshot, ...]) -> bool:
        names = ", ".join(market.station for market in markets)
        try:
            response = self.client.post(
                "/api/markets",
                {"markets": [snapshot_entry(market) for market in markets]},
                timeout_s=self.client.config.timeout_s,
            )
        except HubUnreachable as exc:
            self.log(f"Hub market push failed, will resend all recent markets: {hub_unreachable_detail(self.client.host, exc)}")
            return False
        if response.status_code != 200:
            detail = response.payload.get("detail") if isinstance(response.payload, dict) else response.payload
            self.log(f"Hub {self.client.host} refused the market push ({response.status_code}: {detail}); will resend")
            return False
        results = response.payload.get("results", []) if isinstance(response.payload, dict) else []
        written = sum(1 for result in results if isinstance(result, dict) and result.get("written"))
        self.log(f"Hub {self.client.host}: pushed {names} ({written} written, {len(results) - written} already newer)")
        return True


def watch_recent_markets(
    recent_markets_file: Path,
    interval_s: float,
    on_change: Callable[[Path], None],
    *,
    stop: threading.Event,
    log: Callable[[str], None],
    name: str,
) -> threading.Thread:
    """Call `on_change` at start and whenever the file's mtime changes, until `stop` is set."""

    def watch() -> None:
        last_mtime: float | None = None
        while True:
            try:
                mtime: float | None = recent_markets_file.stat().st_mtime
            except OSError:
                mtime = None
            if mtime is not None and mtime != last_mtime:
                last_mtime = mtime
                try:
                    on_change(recent_markets_file)
                except Exception as exc:  # A bad push or import must not end the watcher.
                    log(f"Recent markets watcher error: {exc}")
            if stop.wait(interval_s):
                return

    thread = threading.Thread(target=watch, name=name, daemon=True)
    thread.start()
    return thread
