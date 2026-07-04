from __future__ import annotations

import sys

import uvicorn

from edap.control_room import error_text
from edap.control_room.app import _ALL_ROUTINE_ACTIONS
from edap.control_room.server.app import build_observer_server_app, _server_hydrate_data
from edap.control_room.server.auth import SharedAccessTokenAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.control_room.server.host import HeadlessControlRoomHost
from edap.control_room.server.sink import (
    DataHydrateFanoutSink,
    FanoutControlRoomEventSink,
    ServerActivityLogSink,
)
from edap.runtime import build_runtime_context, load_config_with_fallback


def serve_observer_mode(
    *,
    config_path: str,
    host: str,
    port: int,
    access_token: str,
    web_default_access_token: str = "",
) -> None:
    loaded = load_config_with_fallback(config_path)
    ctx = build_runtime_context(
        loaded.config,
        config_path=loaded.config_path,
        used_example_config_fallback=loaded.used_example_config_fallback,
        actions=_ALL_ROUTINE_ACTIONS,
    )
    journal_dir = ctx.journal.effective_path

    if journal_dir is None:
        print(
            "ERROR: "
            + error_text.render(
                loaded.config,
                "journal_dir_not_found",
                source_status=ctx.journal.cli_source_status(),
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    broker = InMemoryObserverSessionBroker()
    runtime_host = HeadlessControlRoomHost(ctx)

    def data_provider():
        return _server_hydrate_data(
            runtime_host.dependencies.data_source.current(),
            broker=broker,
        )

    runtime_host._protocol_event_sink = FanoutControlRoomEventSink(
        [
            broker,
            DataHydrateFanoutSink(
                data_provider=data_provider,
                broker=broker,
            ),
            ServerActivityLogSink(),
        ]
    )
    runtime_host.start()
    app = build_observer_server_app(
        data_provider=data_provider,
        command_handler=runtime_host,
        broker=broker,
        auth=SharedAccessTokenAuth(access_token),
        web_default_access_token=web_default_access_token,
    )
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    finally:
        runtime_host.close()
