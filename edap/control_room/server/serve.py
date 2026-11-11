from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path
import socket
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
from edap.eddn.game_markets import import_game_markets_every
from edap.eddn.listener import open_zmq_socket
from edap.eddn.service import EddnService, start_eddn_service
from edap.haul_history import load_runs
from edap.hub.discovery import (
    BROWSE_S, KNOWN_HUB_FILE_NAME, DiscoveredHub, KnownHub, advert_properties, lan_browse, zeroconf_advertise,
)
from edap.hub.history import CentralHistory, HubRuns
from edap.hub.nodes import HubSide, NodeRegistry, store_link_item
from edap.hub.outbox import Outbox
from edap.hub.peer import NODE_ID_FILE_NAME, NodeHello, PeerLink, load_node_id, new_node_id, websocket_dialer
from edap.hub.relay import HubRelay, PeerRelay, node_state
from edap.hub.voice import HubVoice, callout_text, node_muter
from edap.recent_markets import load_recent_markets, watch_file
from edap.market_db import open_market_store, station_facts_writer
from edap.runtime import build_runtime_context, load_config_with_fallback
from edap.tts import NullSpeechBackend, PiperSpeechBackend, build_speech_backend
from edap.version import REPOSITORY_NAME, get_current_version


def serve_observer_mode(
    *,
    config_path: str,
    host: str,
    port: int,
    advertise_host: str,
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
    hub_logger = logging.getLogger("edap.hub")
    # Hub and standalone own the market and station database, with or without the EDDN listener.
    store = open_market_store(loaded.config)
    node: NodeHello | None = None
    if hub_config.role != "standalone":
        node = NodeHello(
            node_id=load_node_id(Path(loaded.config_path).parent / NODE_ID_FILE_NAME, new_node_id),
            name=hub_config.name or socket.gethostname(),
            version=get_current_version(),
        )
    peer_link: PeerLink | None = None

    def mute_own_callouts(muted: bool) -> None:
        # The hub voices this node: its speaker, pages and TUIs stay quiet but callouts still go up the link.
        runtime_host.mute_callouts(muted)
        broker.mute_callouts(muted)

    if node is not None and hub_config.enabled:
        # Hub pages looking at this peer. The app is built further down; these run only once the link is up.
        peer_relay = PeerRelay(
            open_session=lambda channel_id: app.state.open_node_session(channel_id),
            add_listener=broker.add_listener,
            answer_command=lambda channel_id, message: app.state.answer_node_command(channel_id, message),
            answer_read=lambda path, params: app.state.answer_node_read(path, params),
            answer_action=lambda path, body: app.state.answer_node_action(path, body),
            state=lambda: node_state(data_provider()),
            set_muted=mute_own_callouts,
            run_in_background=lambda work: threading.Thread(target=work, name="hub-relay", daemon=True).start(),
            log=hub_logger.info,
        )
        dial = websocket_dialer(hub_config.token, timeout_s=hub_config.timeout_s)
        if hub_config.url:
            # A hub the user named is trusted as named.
            hub_url = lambda: hub_config.url
            connect = lambda: dial(hub_config.url)
            accept_hub = lambda hub_id, name, url: ""
        else:
            # Found over mDNS; the first hub that welcomes this peer is remembered and the only one dialled.
            known_hub = KnownHub(Path(loaded.config_path).parent / KNOWN_HUB_FILE_NAME, hub_logger.warning)
            discovered = DiscoveredHub(browse=lan_browse(sys.platform, BROWSE_S), known=known_hub, dial=dial,
                                       log=hub_logger.warning)
            hub_url = lambda: discovered.url
            connect = discovered
            accept_hub = known_hub.accept
        peer_link = PeerLink(
            hello=node,
            hub_url=hub_url,
            outbox=Outbox.open(hub_config.outbox_file, now=time.time()),
            relay=peer_relay,
            connect=connect,
            accept_hub=accept_hub,
            now=time.time,
            log=hub_logger.info,
            heartbeat_s=hub_config.heartbeat_s,
            request_timeout_s=hub_config.timeout_s,
            search_timeout_s=hub_config.search_timeout_s,
        )
    # A peer sends its journal's station facts up the link; a hub or standalone keeps them.
    record_station_facts = (
        peer_link.enqueue_station_facts if peer_link is not None
        else station_facts_writer(store, logging.getLogger("edap.market_db").warning)
    )
    runtime_host = HeadlessControlRoomHost(
        ctx,
        speech_backend=speech_backend,
        version_source=DefaultVersionSource(),
        record_station_facts=record_station_facts,
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
    haul_runs_file = loaded.config.control_room.haul_runs_file
    stop_background = threading.Event()
    # Recent markets are recorded by the Control Room whenever Market.json changes; a peer queues
    # them for the hub, a hub or standalone writes them into its own database.
    if peer_link is not None:
        hub_logger.info("Hub link: %s as %s (node %s)", hub_config.url or "found on the LAN over mDNS",
                        node.name, node.node_id)
        watch_file(
            recent_markets_file, 5.0, lambda path: peer_link.enqueue_markets(load_recent_markets(path)),
            stop=stop_background, log=hub_logger.warning, name="hub-markets",
        )
        # Every finished haul run goes up too; the first link backfills the whole file once.
        watch_file(
            haul_runs_file, 5.0, lambda path: peer_link.enqueue_runs(load_runs(path)[0]),
            stop=stop_background, log=hub_logger.warning, name="hub-runs",
        )
    hub_side: HubSide | None = None
    if store is not None and node is not None:
        hub_logger.info("Hub %s (node %s): peers link at /api/peer-link", node.name, node.node_id)
        hub_runs = HubRuns.open(hub_config.runs_file, hub_logger.warning)
        hub_logger.info("Hub haul history: own runs %s, peer runs %s", haul_runs_file, hub_config.runs_file)
        hub_relay = HubRelay(log=hub_logger.info, read_timeout_s=hub_config.timeout_s,
                             slow_read_timeout_s=hub_config.search_timeout_s)
        local_node = node
        # Piper clips for listening pages, made one at a time in callout order.
        voice_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hub-voice")
        hub_voice = HubVoice(
            local_node_id=node.node_id,
            settings_file=hub_config.voice_file,
            # The hub's own speaker queue, so a voiced node never talks over the hub's own callouts.
            speak=runtime_host.say,
            # Piper only: the platform voices cannot write a file, so pages then speak the text themselves.
            synthesize=speech_backend.synthesize_wav if isinstance(speech_backend, PiperSpeechBackend) else None,
            names=lambda node_id: local_node.name if node_id == local_node.node_id else hub_relay.name(node_id),
            set_muted=node_muter(node.node_id, mute_own_callouts, hub_relay.send),
            run_in_background=voice_worker.submit,
            log=hub_logger.info,
        )
        voice_settings = hub_voice.settings()
        hub_logger.info("Hub voice: %s, hub speakers %s, mute %s (%s)", voice_settings["node_name"],
                        "on" if voice_settings["speakers"] else "off", "on" if voice_settings["mute"] else "off",
                        hub_config.voice_file)
        # The hub's own game reaches the voice through its broker; a peer's through its link.
        broker.add_listener(lambda message: hub_voice.callout(local_node.node_id, callout_text(message) or ""))
        hub_side = HubSide(registry=NodeRegistry(node, time.time),
                           store_item=store_link_item(store, hub_runs, hub_logger.info),
                           token=hub_config.token,
                           history=CentralHistory(local=node, local_file=haul_runs_file, runs=hub_runs),
                           relay=hub_relay,
                           voice=hub_voice)
    stop_advert = None
    if hub_side is not None:
        if advertise_host:
            try:
                stop_advert = zeroconf_advertise(address=advertise_host, port=port, properties=advert_properties(
                    hub_id=node.node_id, name=node.name, version=node.version))
                hub_logger.info("Hub advertised over mDNS as %s at %s:%s", node.name, advertise_host, port)
            except Exception as exc:  # No multicast: peers can still use `[hub] url`.
                hub_logger.warning("Hub not advertised over mDNS (%s); peers need `[hub] url`", exc)
        else:
            hub_logger.info("Hub not advertised over mDNS: bound to %s; serve with `lan` so peers find it", host)
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
        haul_runs_file=haul_runs_file,
        recent_markets_file=recent_markets_file,
        eddn_status=eddn.status if eddn is not None else None,
        market_database_file=eddn_config.database_file if store is not None else None,
        ardent_lookup=ardent_lookup,
        peer_link=peer_link,
        hub_side=hub_side,
        route_compare_navroute_wait_seconds=loaded.config.control_room.route_compare_navroute_wait_seconds,
        route_compare_compare_retry_attempts=loaded.config.control_room.route_compare_compare_retry_attempts,
    )
    if peer_link is not None:
        # Started once the app exists: hub page channels and reads answer through it.
        threading.Thread(target=lambda: peer_link.run(stop_background.wait), name="hub-link", daemon=True).start()
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    finally:
        stop_background.set()
        if stop_advert is not None:
            stop_advert()
        if eddn is not None:
            eddn.close()
        runtime_host.close()
        if store is not None:
            store.close()
