from __future__ import annotations

from dataclasses import asdict
import unittest

from edap.control_room.client.backend import RemoteObserverBackend
from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.protocol import (
    ActivityLogAppendedEvent,
    SnapshotUpdatedEvent,
    event_from_message,
)
from edap.control_room.protocol.snapshot import (
    ActivityLogEntry,
    ActiveOperatorSnapshot,
    CommandHistorySnapshot,
    ControlRoomSnapshot,
    HaulSessionSnapshot,
    MarketSnapshot,
    PromptStateSnapshot,
    ReplayBrowserSnapshot,
    ServerStatusSnapshot,
    SessionSnapshot,
    ShipSnapshot,
    UiStateSnapshot,
)


def _snapshot() -> ControlRoomSnapshot:
    return ControlRoomSnapshot(
        session=SessionSnapshot(session_id="observer-1", client_role="observer"),
        connected_clients=[],
        active_operator=ActiveOperatorSnapshot(session_id="local-server", client_name="local-server"),
        ship=ShipSnapshot(
            commander_name="CMDR TEST",
            ship_type="Type-9",
            system_name="Sol",
            station_name="Jameson Memorial",
            status="in_station",
            fuel_level=10.0,
            fuel_capacity=32.0,
            credits=1000,
            cargo_count=2,
            cargo_capacity=100,
            cargo_inventory=[],
        ),
        market=MarketSnapshot(
            station_name="Jameson Memorial",
            system_name="Sol",
            market_timestamp="2026-06-18T13:00:00Z",
            market_filter_text=None,
            locked=False,
            items=[],
        ),
        haul_session=HaulSessionSnapshot(
            station_1_buying="",
            station_2_buying="",
            station_1="",
            station_2="",
            active=False,
            clean_run_active=False,
            waiting_for_station_1_departure=False,
            resumed_mid_run=False,
            docked_back_at_station_1=False,
            current_run_started_at=None,
            current_run_elapsed_seconds=None,
            current_run_profit=0,
            completed_runs=0,
            accumulated_profit=0,
            last_run_profit=None,
            last_run_elapsed_seconds=None,
            total_run_elapsed_seconds=0.0,
        ),
        ui_state=UiStateSnapshot(
            routine_active=False,
            active_routine_name=None,
            haul_stop_requested=False,
            verbose_controls=False,
            instant_mode=False,
            activity_auto_follow_paused=False,
            replay_browser_open=False,
            shutdown_requested=False,
            shutdown_finalized=False,
        ),
        command_history=CommandHistorySnapshot(history_limit=20),
        prompt_state=PromptStateSnapshot(),
        replay_browser=ReplayBrowserSnapshot(open=False, filter_text=""),
        activity_log=[
            ActivityLogEntry(
                entry_id="activity-1",
                timestamp="2026-06-18T13:00:00Z",
                message_text="Observer ready",
            )
        ],
        server_status=ServerStatusSnapshot(
            server_name="ED Control Room",
            server_version="1.2.3",
            runtime_platform="macos",
            journal_source_status="configured",
            bindings_source_status="configured",
            bindings_loaded=False,
            capability_names=["observer_http", "observer_websocket", "announcement_stream"],
            operator_mode="observer_only",
        ),
    )


class ControlRoomClientTests(unittest.TestCase):
    def test_parse_target_defaults_to_http_and_default_port(self) -> None:
        target = parse_observer_server_target("192.168.1.44")

        self.assertEqual(target.host, "192.168.1.44")
        self.assertEqual(target.port, 8765)
        self.assertEqual(target.http_base_url, "http://192.168.1.44:8765")
        self.assertEqual(target.websocket_url, "ws://192.168.1.44:8765/session")

    def test_parse_target_keeps_explicit_https_port(self) -> None:
        target = parse_observer_server_target("https://bridge.local:9443")

        self.assertEqual(target.host, "bridge.local")
        self.assertEqual(target.port, 9443)
        self.assertEqual(target.http_base_url, "https://bridge.local:9443")
        self.assertEqual(target.websocket_url, "wss://bridge.local:9443/session")

    def test_event_from_message_parses_snapshot_message(self) -> None:
        snapshot = _snapshot()
        event = event_from_message(
            {
                "message_type": "state.snapshot",
                "payload": asdict(snapshot),
            }
        )

        self.assertIsInstance(event, SnapshotUpdatedEvent)
        self.assertEqual(event.snapshot.ship.system_name, "Sol")

    def test_remote_backend_updates_cached_snapshot_and_emits_read_only_message(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        snapshot = _snapshot()
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=snapshot,
        )
        received: list[object] = []
        backend.subscribe_events(received.append)

        updated_snapshot = ControlRoomSnapshot(
            session=snapshot.session,
            connected_clients=snapshot.connected_clients,
            active_operator=snapshot.active_operator,
            ship=ShipSnapshot(**{**asdict(snapshot.ship), "system_name": "Achenar"}),
            market=snapshot.market,
            haul_session=snapshot.haul_session,
            ui_state=snapshot.ui_state,
            command_history=snapshot.command_history,
            prompt_state=snapshot.prompt_state,
            replay_browser=snapshot.replay_browser,
            activity_log=snapshot.activity_log,
            server_status=snapshot.server_status,
        )

        backend.publish_snapshot(updated_snapshot)
        backend.dispatch_command("dock")

        self.assertEqual(backend.current_snapshot().ship.system_name, "Achenar")
        self.assertIsInstance(received[0], SnapshotUpdatedEvent)
        self.assertIsInstance(received[1], ActivityLogAppendedEvent)
        self.assertEqual(received[1].entry.message_text, "Observer session is read-only.")


if __name__ == "__main__":
    unittest.main()
