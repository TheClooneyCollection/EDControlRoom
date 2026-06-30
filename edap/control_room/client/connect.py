from __future__ import annotations

import socket
from dataclasses import replace

from edap.control_room.app import ControlRoomApp, _ALL_ROUTINE_ACTIONS
from edap.control_room.client.backend import (
    RemoteObserverBackend,
    RemoteObserverDataSource,
    RemoteObserverExecution,
    fetch_remote_control_room_data,
)
from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.dependencies import ControlRoomDependencies
from edap.control_room.protocol import build_remote_observer_websocket_connect_info
from edap.runtime import build_runtime_context, load_config_with_fallback


def connect_observer_mode(
    *,
    config_path: str,
    target: str,
    access_token: str,
    client_name: str | None = None,
    claim_operator: bool = False,
) -> None:
    server_target = parse_observer_server_target(target)
    display_client_name = client_name or socket.gethostname() or "observer"
    _capabilities, initial_data = fetch_remote_control_room_data(
        server_target=server_target,
        access_token=access_token,
    )
    data_source = RemoteObserverDataSource(initial_data)
    connect_info = build_remote_observer_websocket_connect_info(
        server_target.web_socket_url,
        access_token=access_token,
        client_name=display_client_name,
        claim_operator=claim_operator,
    )
    backend = RemoteObserverBackend(
        server_target=server_target,
        access_token=access_token,
        client_name=display_client_name,
        websocket_connect_info=connect_info,
        data_source=data_source,
    )
    ctx = build_runtime_context(
        config=load_config_with_fallback(config_path),
        config_path=config_path,
        required_actions=_ALL_ROUTINE_ACTIONS,
        allow_missing_journal=True,
    )
    execution = RemoteObserverExecution(backend)
    app = ControlRoomApp(
        ctx,
        backend=backend,
        dependencies=ControlRoomDependencies(
            data_source=data_source,
            execution=execution,
        ),
        title_override=f"ED Control Room Observer - {server_target.host}:{server_target.port}",
    )
    execution.bind_app(app)
    app.run()
