from __future__ import annotations

import logging
import sys
import threading
import time

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
from edap.eddn.game_markets import import_markets
from edap.eddn.listener import open_zmq_socket
from edap.eddn.service import EddnService, start_eddn_service
from edap.hub import HubClient, HubMarketPusher, httpx_transport, watch_recent_markets
from edap.runtime import build_runtime_context, load_config_with_fallback
from edap.tts import NullSpeechBackend, build_speech_backend


def serve_observer_mode(
    *,
    config_path: str,
    host: str,
    port: int,
    access_token: str,
    speak_tts: bool,
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
    # The server speaks on its own host so a headless Deck needs no TUI; `--no-tts` avoids
    # a double callout when a `connect` TUI runs on the same machine.
    speech_backend = (
        build_speech_backend(ctx.config.runtime.platform, ctx.config.tts.piper)
        if speak_tts
        else NullSpeechBackend()
    )
    runtime_host = HeadlessControlRoomHost(ctx, speech_backend=speech_backend)

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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    eddn_config = loaded.config.eddn
    eddn: EddnService | None = None
    if eddn_config.enabled:
        eddn_logger = logging.getLogger("edap.eddn")
        eddn = start_eddn_service(
            eddn_config,
            open_socket=lambda: open_zmq_socket(eddn_config.relay),
            time_fn=time.time,
            log=eddn_logger.info,
        )
        eddn_logger.info("EDDN listener started: %s -> %s", eddn_config.relay, eddn_config.database_file)
    recent_markets_file = loaded.config.control_room.recent_markets_file
    hub_config = loaded.config.hub
    hub = HubClient(hub_config, httpx_transport) if hub_config.enabled else None
    stop_hub_push = threading.Event()
    # Recent markets are recorded by the Control Room whenever Market.json changes; with a hub
    # they go only to the hub's DB.
    if hub is not None:
        hub_logger = logging.getLogger("edap.hub")
        hub_logger.info("Hub: searches and market pushes go to %s", hub_config.url)
        pusher = HubMarketPusher(client=hub, log=hub_logger.info)
        watch_recent_markets(
            recent_markets_file, 5.0, pusher.push_changes, stop=stop_hub_push, log=hub_logger.warning, name="hub-markets"
        )
    elif eddn is not None:
        eddn.import_game_markets_every(recent_markets_file, 5.0, logging.getLogger("edap.eddn").info)
    broker.server_state.set_selected_trade_route(runtime_host._saved_state.selected_trade_route)
    broker.server_state.set_running_trade_route(runtime_host._saved_state.running_trade_route)
    app = build_observer_server_app(
        data_provider=data_provider,
        command_handler=runtime_host,
        broker=broker,
        auth=SharedAccessTokenAuth(access_token),
        web_default_access_token=web_default_access_token,
        journal_dir=journal_dir,
        haul_runs_file=loaded.config.control_room.haul_runs_file,
        recent_markets_file=recent_markets_file,
        eddn_status=eddn.status if eddn is not None else None,
        eddn_database_file=eddn_config.database_file if eddn is not None else None,
        import_markets=(lambda markets: import_markets(eddn.store, markets)) if eddn is not None else None,
        hub=hub,
        route_compare_navroute_wait_seconds=loaded.config.control_room.route_compare_navroute_wait_seconds,
        route_compare_compare_retry_attempts=loaded.config.control_room.route_compare_compare_retry_attempts,
    )
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    finally:
        stop_hub_push.set()
        if eddn is not None:
            eddn.close()
        runtime_host.close()
