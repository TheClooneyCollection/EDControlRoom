from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import socket
import sys
from typing import Any
from urllib.parse import quote, urlsplit

import httpx
import websockets

from edap.runtime import load_config_with_fallback
from edap.tts import TTSAnnouncer, parse_announcement_id


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


def connect_observer_mode(
    *,
    config_path: str,
    target: str,
    access_token: str,
    client_name: str | None = None,
) -> None:
    loaded = load_config_with_fallback(config_path)
    server_target = parse_observer_server_target(target)
    resolved_client_name = (client_name or socket.gethostname()).strip() or "observer-client"
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    with httpx.Client(timeout=10.0) as client:
        capabilities_response = client.get(
            f"{server_target.http_base_url}/capabilities",
            headers=auth_headers,
        )
        _raise_for_auth_or_http_error(capabilities_response, server_target)
        capabilities = capabilities_response.json()

        snapshot_response = client.get(
            f"{server_target.http_base_url}/snapshot",
            headers=auth_headers,
        )
        _raise_for_auth_or_http_error(snapshot_response, server_target)
        snapshot = snapshot_response.json()

    announcer = TTSAnnouncer(
        loaded.config.tts,
        platform_name=loaded.config.runtime.platform,
    )
    try:
        announcer.set_commander_name(snapshot["ship"]["commander_name"])
        _print_snapshot_summary(server_target, resolved_client_name, capabilities, snapshot)
        asyncio.run(
            _stream_observer_session(
                websocket_url=server_target.websocket_url,
                access_token=access_token,
                client_name=resolved_client_name,
                announcer=announcer,
            )
        )
    except KeyboardInterrupt:
        print("Disconnected from observer session.", file=sys.stderr)
    finally:
        announcer.close()


def _raise_for_auth_or_http_error(
    response: httpx.Response,
    server_target: ObserverServerTarget,
) -> None:
    if response.status_code == 401:
        raise SystemExit(
            f"Authentication failed for {server_target.host}:{server_target.port}. "
            "Check the shared access token."
        )
    response.raise_for_status()


def _print_snapshot_summary(
    server_target: ObserverServerTarget,
    client_name: str,
    capabilities: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    ship = snapshot["ship"]
    server_status = snapshot["server_status"]
    connected_count = len(snapshot["connected_clients"])
    location = _render_location(ship)
    print(
        f"Connected observer {client_name} to {server_target.host}:{server_target.port} "
        f"({server_status['server_name']} {server_status['server_version']})."
    )
    print(
        f"Commander: {ship['commander_name'] or 'unknown'} | "
        f"Location: {location} | "
        f"Connected clients: {connected_count}"
    )
    print(
        "Capabilities: " + ", ".join(capabilities.get("capability_names", []))
    )


async def _stream_observer_session(
    *,
    websocket_url: str,
    access_token: str,
    client_name: str,
    announcer: TTSAnnouncer,
) -> None:
    session_url = (
        f"{websocket_url}?client_name={quote(client_name)}"
        f"&access_token={quote(access_token)}"
    )
    async with websockets.connect(session_url) as websocket:
        async for raw_message in websocket:
            message = json.loads(raw_message)
            _handle_session_message(message, announcer=announcer)


def _handle_session_message(
    message: dict[str, Any],
    *,
    announcer: TTSAnnouncer,
) -> None:
    message_type = message.get("message_type")
    payload = message.get("payload", {})
    if message_type == "event.connection_ready":
        print(
            f"Observer session ready: {payload['session_id']} "
            f"({payload['server_name']} {payload['server_version']})"
        )
        return
    if message_type == "state.snapshot":
        ship = payload["ship"]
        print(f"Snapshot synced: {_render_location(ship)}")
        return
    if message_type == "event.activity_log_appended":
        entry = payload["entry"]
        print(f"[activity] {entry['message_text']}")
        return
    if message_type == "event.announcement_emitted":
        print(f"[announcement] {payload['message_text']}")
        _play_local_announcement(announcer, payload)


def _play_local_announcement(announcer: TTSAnnouncer, payload: dict[str, Any]) -> None:
    parsed_id = parse_announcement_id(payload["announcement_id"])
    if parsed_id is None:
        return
    values = payload.get("message_values", {})
    announcer.announce(parsed_id, **values)


def _render_location(ship: dict[str, Any]) -> str:
    system_name = ship.get("system_name")
    station_name = ship.get("station_name")
    if system_name and station_name:
        return f"{system_name} / {station_name}"
    return system_name or station_name or "unknown"
