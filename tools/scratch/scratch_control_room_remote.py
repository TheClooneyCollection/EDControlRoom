from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from urllib.parse import quote

import httpx
import websockets

from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.protocol import validate_remote_observer_capabilities_payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe Control Room remote observer HTTP and websocket surfaces."
    )
    parser.add_argument("target", help="host[:port] or http(s)://host[:port]")
    parser.add_argument("--token", required=True, help="shared observer access token")
    parser.add_argument(
        "--client-name",
        default="scratch-probe",
        help="client_name sent on the websocket session",
    )
    parser.add_argument(
        "--claim-operator",
        action="store_true",
        help="request active operator after websocket connect",
    )
    parser.add_argument(
        "--watch-seconds",
        type=float,
        default=5.0,
        help="how long to watch websocket messages after connect",
    )
    parser.add_argument(
        "--request-snapshot",
        action="store_true",
        help="send command.request_snapshot after connect",
    )
    return parser


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _print_snapshot_summary(snapshot: dict[str, Any]) -> None:
    session = snapshot.get("session", {})
    active_operator = snapshot.get("active_operator", {})
    activity_log = snapshot.get("activity_log", [])
    prompt = snapshot.get("prompt", {})
    prompt_state = snapshot.get("prompt_state", {})
    replay = snapshot.get("replay_browser", {})
    prompt_visible = bool(
        prompt.get("is_visible")
        or prompt_state.get("haul_prompt_step")
        or prompt_state.get("destination_prompt_destination")
    )
    print("snapshot:")
    print(f"  session role: {session.get('client_role')}")
    print(f"  active operator: {active_operator.get('client_name')}")
    print(f"  connected clients: {len(snapshot.get('connected_clients', []))}")
    print(f"  activity lines: {len(activity_log)}")
    print(f"  prompt visible: {prompt_visible}")
    print(f"  replay open: {bool(replay.get('open'))}")


def _message(message_type: str, payload: dict[str, object], *, message_id: str) -> dict[str, object]:
    return {
        "message_id": message_id,
        "message_type": message_type,
        "payload": payload,
    }


async def _watch_session(
    target: ObserverServerTarget,
    *,
    token: str,
    client_name: str,
    capabilities: dict[str, Any],
    claim_operator: bool,
    request_snapshot: bool,
    watch_seconds: float,
) -> None:
    session_url = _session_url_from_capabilities(
        target,
        token=token,
        client_name=client_name,
        capabilities=capabilities,
    )
    print(f"websocket: {session_url}")
    async with websockets.connect(session_url) as websocket:
        if claim_operator:
            await websocket.send(
                json.dumps(
                    _message(
                        "command.request_active_operator",
                        {},
                        message_id="claim-operator",
                    )
                )
            )
        if request_snapshot:
            await websocket.send(
                json.dumps(
                    _message(
                        "command.request_snapshot",
                        {},
                        message_id="request-snapshot",
                    )
                )
            )
        deadline = asyncio.get_running_loop().time() + max(watch_seconds, 0.0)
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                break
            message = json.loads(raw)
            message_type = message.get("message_type", "<unknown>")
            payload = message.get("payload", {})
            print(f"message: {message_type}")
            if message_type == "event.connection_ready":
                print(
                    "  role="
                    f"{payload.get('client_role')} session={payload.get('session_id')}"
                )
            elif message_type == "state.snapshot":
                _print_snapshot_summary(payload)
            elif message_type == "event.activity_log_appended":
                entry = payload.get("entry", {})
                print(f"  activity: {entry.get('message_text')}")
            elif message_type == "event.active_operator_changed":
                print(f"  active operator: {payload.get('active_operator_client_name')}")
            elif message_type == "response.error":
                print(f"  error: {payload.get('error_code')} {payload.get('error_message')}")
            elif message_type == "response.success":
                print(f"  success: {payload.get('message_text')}")


def _session_url_from_capabilities(
    target: ObserverServerTarget,
    *,
    token: str,
    client_name: str,
    capabilities: dict[str, Any],
) -> str:
    validation_error = validate_remote_observer_capabilities_payload(capabilities)
    if validation_error is not None:
        raise SystemExit(f"capabilities validation failed: {validation_error}")
    supported_transports = capabilities.get("authentication_supported_transports", [])
    if "query_parameter" not in supported_transports:
        raise SystemExit(
            "scratch websocket probe requires query-parameter authentication transport support"
        )
    query_parameter_name = str(capabilities["authentication_query_parameter_name"])
    return (
        f"{target.websocket_url}?client_name={quote(client_name)}"
        f"&{quote(query_parameter_name)}={quote(token)}"
    )


def main() -> None:
    args = _build_parser().parse_args()
    target = parse_observer_server_target(args.target)

    with httpx.Client(headers=_auth_headers(args.token), timeout=5.0) as client:
        health = client.get(f"{target.http_base_url}/health")
        print("health:")
        print(json.dumps(health.json(), indent=2, sort_keys=True))

        capabilities = client.get(f"{target.http_base_url}/capabilities")
        capabilities.raise_for_status()
        capabilities_json = capabilities.json()
        validation_error = validate_remote_observer_capabilities_payload(capabilities_json)
        if validation_error is not None:
            raise SystemExit(f"capabilities validation failed: {validation_error}")
        print("capabilities:")
        print(json.dumps(capabilities_json, indent=2, sort_keys=True))
        print(f"schema url: {target.http_base_url}{capabilities_json['message_schema_url']}")
        print(f"browser probe url: {target.http_base_url}{capabilities_json['browser_probe_url']}")

        snapshot = client.get(f"{target.http_base_url}/snapshot")
        snapshot.raise_for_status()
        _print_snapshot_summary(snapshot.json())

    asyncio.run(
        _watch_session(
            target,
            token=args.token,
            client_name=args.client_name,
            capabilities=capabilities_json,
            claim_operator=args.claim_operator,
            request_snapshot=args.request_snapshot,
            watch_seconds=args.watch_seconds,
        )
    )


if __name__ == "__main__":
    main()
