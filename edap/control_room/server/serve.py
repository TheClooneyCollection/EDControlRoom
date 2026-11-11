from __future__ import annotations

import logging
import sys
import threading
import time

import uvicorn

from edap.control_room import error_text
from edap.control_room.app import _ALL_ROUTINE_ACTIONS, DefaultVersionSource
from edap.control_room.server.app import build_observer_server_app, _server_hydrate_data
from edap.control_room.server.auth import SharedAccessTokenAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.control_room.server.host import HeadlessControlRoomHost
from edap.control_room.server.sink import (
    DataHydrateFanoutSink,
    FanoutControlRoomEventSink,
    ServerActivityLogSink,
)
from edap.ardent import ArdentLookup, httpx_fetch_json
from edap.eddn.game_markets import import_game_markets_every, import_markets
from edap.eddn.listener import open_zmq_socket
from edap.eddn.service import EddnService, start_eddn_service
from edap.hub import HubClient, HubMarketPusher, HubStatus, httpx_transport, run_hub_heartbeat, watch_recent_markets
from edap.market_db import open_market_store, station_facts_writer
from edap.runtime import build_runtime_context, load_config_with_fallback
from edap.tts import NullSpeechBackend, build_speech_backend
from edap.version import REPOSITORY_NAME, get_current_version


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
    hub_config = loaded.config.hub
    # Hub and standalone own the market and station database, with or without the EDDN listener.
    store = open_market_store(loaded.config)
    runtime_host = HeadlessControlRoomHost(
        ctx,
        speech_backend=speech_backend,
        version_source=DefaultVersionSource(),
        record_station_facts=station_facts_writer(store, logging.getLogger("edap.market_db").warning),
    )

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
    db_logger = logging.getLogger("edap.market_db")
    if store is not None:
        db_logger.info("Market DB (role %s): %s", hub_config.role, eddn_config.database_file)
    else:
        db_logger.info("Market DB: none on a peer; the hub owns market and station data")
    if store is not None and eddn_config.enabled:
        eddn_logger = logging.getLogger("edap.eddn")
        eddn = start_eddn_service(
            eddn_config,
            store=store,
            open_socket=lambda: open_zmq_socket(eddn_config.relay),
            time_fn=time.time,
            log=eddn_logger.info,
        )
        eddn_logger.info("EDDN listener started: %s -> %s", eddn_config.relay, eddn_config.database_file)
    elif eddn_config.enabled:
        logging.getLogger("edap.eddn").info("EDDN listener off: a peer never listens; the hub does")
    recent_markets_file = loaded.config.control_room.recent_markets_file
    hub = HubClient(hub_config, httpx_transport) if hub_config.enabled else None
    hub_status: HubStatus | None = None
    stop_background = threading.Event()
    # Recent markets are recorded by the Control Room whenever Market.json changes; a peer sends
    # them only to the hub, a hub or standalone writes them into its own database.
    if hub is not None:
        hub_logger = logging.getLogger("edap.hub")
        hub_logger.info("Hub: searches and market pushes go to %s", hub_config.url)
        hub_status = HubStatus(hub, time.time)
        pusher = HubMarketPusher(client=hub, log=hub_logger.info, status=hub_status)
        watch_recent_markets(
            recent_markets_file, 5.0, pusher.push_changes, stop=stop_background, log=hub_logger.warning,
            name="hub-markets",
        )
        threading.Thread(
            target=lambda: run_hub_heartbeat(
                hub_status, perf_counter=time.perf_counter, wait=stop_background.wait, log=hub_logger.info
            ),
            name="hub-heartbeat",
            daemon=True,
        ).start()
    if store is not None:
        import_game_markets_every(store, recent_markets_file, 5.0, db_logger.info, stop=stop_background)
    ardent_lookup: ArdentLookup | None = None
    if store is not None:
        ardent_lookup = ArdentLookup(
            httpx_fetch_json(f"{REPOSITORY_NAME}/{get_current_version()} (Best deal lookups)"),
            now=time.time,
            # Rows land in the store, so /routes gains them too.
            save=store.save,
            log=logging.getLogger("edap.ardent").info,
        )
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
        market_database_file=eddn_config.database_file if store is not None else None,
        import_markets=(lambda markets: import_markets(store, markets)) if store is not None else None,
        ardent_lookup=ardent_lookup,
        hub=hub,
        hub_status=hub_status,
        route_compare_navroute_wait_seconds=loaded.config.control_room.route_compare_navroute_wait_seconds,
        route_compare_compare_retry_attempts=loaded.config.control_room.route_compare_compare_retry_attempts,
    )
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    finally:
        stop_background.set()
        if eddn is not None:
            eddn.close()
        runtime_host.close()
        if store is not None:
            store.close()
