from __future__ import annotations

import socket

from edap.control_room.app import ControlRoomApp, _ALL_ROUTINE_ACTIONS
from edap.control_room.client.backend import (
    RemoteObserverBackend,
    RemoteObserverDataSource,
    RemoteObserverExecution,
    fetch_remote_control_room_data,
)
from edap.control_room.client.target import parse_observer_server_target
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
    capabilities, initial_data = fetch_remote_control_room_data(
        server_target=server_target,
        access_token=access_token,
    )
    data_source = RemoteObserverDataSource(initial_data)
    connect_info = build_remote_observer_websocket_connect_info(
        websocket_url=server_target.websocket_url,
        access_token=access_token,
        client_name=display_client_name,
        capabilities=capabilities,
        prefer_authorization_header=True,
    )
    backend = RemoteObserverBackend(
        server_target=server_target,
        access_token=access_token,
        client_name=display_client_name,
        websocket_connect_info=connect_info,
        data_source=data_source,
    )
    if claim_operator:
        backend.request_active_operator()
    loaded = load_config_with_fallback(config_path)
    ctx = build_runtime_context(
        loaded.config,
        config_path=loaded.config_path,
        used_example_config_fallback=loaded.used_example_config_fallback,
        actions=_ALL_ROUTINE_ACTIONS,
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
