from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


DEFAULT_OBSERVER_PORT = 8765


@dataclass(frozen=True)
class ObserverServerTarget:
    host: str
    port: int
    http_base_url: str
    websocket_url: str


def parse_observer_server_target(raw_target: str) -> ObserverServerTarget:
    stripped = raw_target.strip()
    if not stripped:
        raise ValueError("Connect target cannot be empty.")
    if "://" not in stripped:
        split = urlsplit(f"http://{stripped}")
    else:
        split = urlsplit(stripped)
    if split.hostname is None:
        raise ValueError(f"Connect target is missing a host: {raw_target!r}")
    http_scheme = "https" if split.scheme == "https" else "http"
    websocket_scheme = "wss" if http_scheme == "https" else "ws"
    port = split.port or (443 if http_scheme == "https" else DEFAULT_OBSERVER_PORT)
    host = split.hostname
    return ObserverServerTarget(
        host=host,
        port=port,
        http_base_url=f"{http_scheme}://{host}:{port}",
        websocket_url=f"{websocket_scheme}://{host}:{port}/session",
    )
