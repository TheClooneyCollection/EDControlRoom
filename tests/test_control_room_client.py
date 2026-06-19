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

    def test_remote_backend_updates_cached_snapshot(self) -> None:
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

        self.assertEqual(backend.current_snapshot().ship.system_name, "Achenar")
        self.assertIsInstance(received[0], SnapshotUpdatedEvent)

    def test_remote_backend_surfaces_response_error_messages(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)

        backend._handle_response_message(
            {
                "message_type": "response.error",
                "payload": {"error_message": "Observer clients cannot issue operator commands."},
            }
        )

        self.assertIsInstance(received[0], ActivityLogAppendedEvent)
        self.assertEqual(
            received[0].entry.message_text,
            "Observer clients cannot issue operator commands.",
        )

    def test_remote_backend_enqueues_snapshot_request_and_submit_input(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
        )

        backend.request_snapshot()
        backend.dispatch_command("dock")

        first = backend._outgoing_messages.get_nowait()
        second = backend._outgoing_messages.get_nowait()
        self.assertEqual(first["message_type"], "command.request_snapshot")
        self.assertEqual(second["message_type"], "command.submit_input")
        self.assertEqual(second["payload"]["raw_input"], "dock")

    def test_remote_backend_enqueues_replay_commands(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
        )

        backend.open_replay_browser()
        backend.set_replay_filter("haul")
        backend.replay_history_entry(
            entry=type("Entry", (), {
                "raw": "haul gold",
                "command": "haul",
                "params": {"station_1_buying": "gold"},
                "timestamp": "2026-06-18T13:00:00Z",
            })(),
            edit=True,
            skip_delay=True,
        )
        backend.toggle_replay_default_haul(
            type("Entry", (), {
                "raw": "haul gold",
                "command": "haul",
                "params": {"station_1_buying": "gold"},
                "timestamp": "2026-06-18T13:00:00Z",
            })()
        )
        backend.close_replay_browser()

        self.assertEqual(backend._outgoing_messages.get_nowait()["message_type"], "command.open_replay_browser")
        self.assertEqual(backend._outgoing_messages.get_nowait()["payload"]["filter_text"], "haul")
        replay_message = backend._outgoing_messages.get_nowait()
        self.assertEqual(replay_message["message_type"], "command.replay_history_entry")
        self.assertTrue(replay_message["payload"]["edit"])
        self.assertTrue(replay_message["payload"]["skip_delay"])
        toggle_message = backend._outgoing_messages.get_nowait()
        self.assertEqual(toggle_message["message_type"], "command.toggle_replay_default_haul")
        self.assertEqual(backend._outgoing_messages.get_nowait()["message_type"], "command.close_replay_browser")

    def test_remote_backend_marks_snapshot_disconnected_on_connection_loss(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        snapshot = ControlRoomSnapshot(
            session=SessionSnapshot(session_id="observer-1", client_role="active_operator"),
            connected_clients=[],
            active_operator=ActiveOperatorSnapshot(
                session_id="observer-1",
                client_name="observer-ipad",
            ),
            ship=_snapshot().ship,
            market=_snapshot().market,
            haul_session=_snapshot().haul_session,
            ui_state=UiStateSnapshot(
                routine_active=True,
                active_routine_name="dock",
                haul_stop_requested=False,
                verbose_controls=False,
                instant_mode=False,
                activity_auto_follow_paused=False,
                replay_browser_open=True,
                shutdown_requested=False,
                shutdown_finalized=False,
            ),
            command_history=_snapshot().command_history,
            prompt_state=_snapshot().prompt_state,
            replay_browser=_snapshot().replay_browser,
            activity_log=_snapshot().activity_log,
            server_status=_snapshot().server_status,
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=snapshot,
        )
        received: list[object] = []
        backend.subscribe_events(received.append)
        backend._has_connected_once = True

        backend._handle_connection_lost("Observer connection lost: ping timeout")

        current = backend.current_snapshot()
        self.assertEqual(current.connected_clients, [])
        self.assertIsNone(current.active_operator)
        self.assertFalse(current.ui_state.routine_active)
        self.assertIsNone(current.ui_state.active_routine_name)
        self.assertFalse(current.ui_state.replay_browser_open)
        self.assertIsInstance(received[0], SnapshotUpdatedEvent)
        self.assertIsInstance(received[1], ActivityLogAppendedEvent)
        self.assertEqual(received[1].entry.message_text, "Observer connection lost: ping timeout")

    def test_remote_backend_rejects_commands_when_disconnected(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)
        backend._has_connected_once = True

        backend.dispatch_command("dock")

        self.assertTrue(backend._outgoing_messages.empty())
        self.assertIsInstance(received[0], ActivityLogAppendedEvent)
        self.assertEqual(received[0].entry.message_text, "Observer connection unavailable.")

    def test_remote_backend_reconnect_delay_doubles_and_caps(self) -> None:
        backend = RemoteObserverBackend(
            server_target=ObserverServerTarget(
                host="bridge.local",
                port=8765,
                http_base_url="http://bridge.local:8765",
                websocket_url="ws://bridge.local:8765/session",
            ),
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
        )

        self.assertEqual(backend._next_reconnect_delay(1.0), 2.0)
        self.assertEqual(backend._next_reconnect_delay(2.0), 4.0)
        self.assertEqual(backend._next_reconnect_delay(16.0), 30.0)
        self.assertEqual(backend._next_reconnect_delay(30.0), 30.0)

    def test_remote_backend_logs_reconnect_backoff_and_restore(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
        )
        received: list[object] = []
        backend.subscribe_events(received.append)
        backend._has_connected_once = True

        backend._handle_connection_lost("Observer connection lost: ping timeout")
        backend._emit_local_message("Reconnecting in 1.0s...")
        backend._connected = True
        backend.request_snapshot()
        backend._emit_local_message("Observer connection restored.")

        messages = [
            event.entry.message_text
            for event in received
            if isinstance(event, ActivityLogAppendedEvent)
        ]
        self.assertIn("Observer connection lost: ping timeout", messages)
        self.assertIn("Reconnecting in 1.0s...", messages)
        self.assertIn("Observer connection restored.", messages)
        reconnect_request = backend._outgoing_messages.get_nowait()
        self.assertEqual(reconnect_request["message_type"], "command.request_snapshot")

    def test_remote_backend_enqueues_active_operator_claim(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
        )

        backend.request_active_operator()

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.request_active_operator")

    def test_remote_backend_enqueues_cancel_active_routine(self) -> None:
        target = ObserverServerTarget(
            host="bridge.local",
            port=8765,
            http_base_url="http://bridge.local:8765",
            websocket_url="ws://bridge.local:8765/session",
        )
        backend = RemoteObserverBackend(
            server_target=target,
            access_token="secret-token",
            client_name="observer-ipad",
            initial_snapshot=_snapshot(),
        )

        backend.interrupt_active_routine()

        message = backend._outgoing_messages.get_nowait()
        self.assertEqual(message["message_type"], "command.cancel_active_routine")


if __name__ == "__main__":
    unittest.main()
