from __future__ import annotations

from types import SimpleNamespace
import unittest

from edap.control_room.dependencies import (
    LocalControlRoomDataSource,
    LocalControlRoomExecution,
)
from edap.control_room.backend import LocalControlRoomBackend
from edap.control_room.models import HaulStats, MarketData, RuntimeUIState, ShipState
from edap.control_room.protocol import build_activity_log_entry
from edap.control_room_state import ControlRoomState, CommandHistoryEntry


class _FakeFacade:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def dispatch_command(self, *args, **kwargs) -> None:
        self.calls.append(("dispatch_command", args, kwargs))

    def dispatch_dest(self, *args, **kwargs) -> None:
        self.calls.append(("dispatch_dest", args, kwargs))

    def dispatch_haul_loop(self, *args, **kwargs) -> None:
        self.calls.append(("dispatch_haul_loop", args, kwargs))

    def load_trade_route(self, *args, **kwargs) -> None:
        self.calls.append(("load_trade_route", args, kwargs))

    def handle_haul_prompt(self, *args, **kwargs) -> None:
        self.calls.append(("handle_haul_prompt", args, kwargs))

    def handle_haul_confirm_prompt(self, *args, **kwargs) -> None:
        self.calls.append(("handle_haul_confirm_prompt", args, kwargs))


class _FakeExecution:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def submit_command(self, *args, **kwargs) -> None:
        self.calls.append(("submit_command", args, kwargs))

    def dispatch_destination(self, *args, **kwargs) -> None:
        self.calls.append(("dispatch_destination", args, kwargs))

    def dispatch_haul_loop(self, *args, **kwargs) -> None:
        self.calls.append(("dispatch_haul_loop", args, kwargs))

    def load_trade_route(self, *args, **kwargs) -> None:
        self.calls.append(("load_trade_route", args, kwargs))

    def handle_haul_prompt(self, *args, **kwargs) -> None:
        self.calls.append(("handle_haul_prompt", args, kwargs))

    def handle_haul_confirm_prompt(self, *args, **kwargs) -> None:
        self.calls.append(("handle_haul_confirm_prompt", args, kwargs))

    def cancel_active_routine(self) -> None:
        self.calls.append(("cancel_active_routine", (), {}))


class ControlRoomDependenciesTests(unittest.TestCase):
    def test_local_data_source_returns_copied_read_model(self) -> None:
        app = SimpleNamespace(
            _ship=ShipState(system="Sol", cargo_inventory=[{"Name": "gold"}]),
            _market=MarketData(station="Galileo", items=[{"name": "Gold"}]),
            _haul_stats=HaulStats(station_1="Galileo", completed_runs=2),
            _saved_state=ControlRoomState(
                history=[
                    CommandHistoryEntry(
                        raw="dest sol",
                        command="dest",
                        params={"destination": "Sol"},
                        timestamp="2026-06-30T17:00:00Z",
                    )
                ],
                default_haul={"station_1": "Galileo"},
            ),
            _config=SimpleNamespace(
                control_room=SimpleNamespace(history_limit=20),
                runtime=SimpleNamespace(platform="macos"),
            ),
            _protocol_activity_log=[build_activity_log_entry("Observer ready")],
            _runtime_state=RuntimeUIState(routine_active=True, active_routine_name="haul"),
            _current_version="1.2.3",
            _ctx=SimpleNamespace(
                journal=SimpleNamespace(cli_source_status=lambda: "configured"),
                bindings=SimpleNamespace(cli_source_status=lambda: "configured"),
                binding_lookup=object(),
            ),
        )

        data = LocalControlRoomDataSource(app).current()

        self.assertEqual(data.ship.system, "Sol")
        self.assertEqual(data.market.station, "Galileo")
        self.assertEqual(data.haul_session.completed_runs, 2)
        self.assertEqual(data.command_history.default_haul["station_1"], "Galileo")
        self.assertEqual(data.command_history.history_entries[0].raw, "dest sol")
        self.assertEqual(data.activity_log.entries[0].message_text, "Observer ready")
        self.assertTrue(data.routine.routine_active)
        self.assertEqual(data.server_status.runtime_platform, "macos")

        app._ship.cargo_inventory.append({"Name": "silver"})
        app._market.items.append({"name": "Silver"})

        self.assertEqual(data.ship.cargo_inventory, [{"Name": "gold"}])
        self.assertEqual(data.market.items, [{"name": "Gold"}])

    def test_local_data_source_exports_haul_elapsed_without_local_clock_start_times(self) -> None:
        app = SimpleNamespace(
            _ship=ShipState(system="Sol"),
            _market=MarketData(station="Galileo"),
            _haul_stats=HaulStats(
                station_1_buying="Gallium",
                station_2_buying="Bauxite",
                session_started_at=100.0,
                session_elapsed_s=0.0,
                active=True,
                clean_run_active=True,
                current_run_started_at=160.0,
                current_run_elapsed_s=None,
            ),
            _saved_state=ControlRoomState(),
            _config=SimpleNamespace(
                control_room=SimpleNamespace(history_limit=20),
                runtime=SimpleNamespace(platform="macos"),
            ),
            _protocol_activity_log=[],
            _runtime_state=RuntimeUIState(),
            _current_version="1.2.3",
            _ctx=SimpleNamespace(
                journal=SimpleNamespace(cli_source_status=lambda: "configured"),
                bindings=SimpleNamespace(cli_source_status=lambda: "configured"),
                binding_lookup=object(),
            ),
            _time_fn=lambda: 400.0,
        )

        data = LocalControlRoomDataSource(app).current()

        self.assertIsNone(data.haul_session.session_started_at)
        self.assertEqual(data.haul_session.session_elapsed_s, 300.0)
        self.assertIsNone(data.haul_session.current_run_started_at)
        self.assertEqual(data.haul_session.current_run_elapsed_s, 240.0)

    def test_local_execution_delegates_to_facade(self) -> None:
        facade = _FakeFacade()
        app = SimpleNamespace(
            _facade=facade,
            _haul_params={},
            _handle_interrupt=lambda source: facade.calls.append(
                ("interrupt", (source,), {})
            ),
        )

        execution = LocalControlRoomExecution(app)

        execution.submit_command("dest sol", skip_delay=True)
        execution.dispatch_destination("Sol", 2.0, raw_command="dest sol")
        execution.dispatch_haul_loop(params={"commodity": "gold"}, raw_command="haul")
        execution.handle_haul_prompt("gold")
        execution.handle_haul_confirm_prompt("yes")
        execution.cancel_active_routine()

        self.assertEqual(
            [call[0] for call in facade.calls],
            [
                "dispatch_command",
                "dispatch_dest",
                "dispatch_haul_loop",
                "handle_haul_prompt",
                "handle_haul_confirm_prompt",
                "interrupt",
            ],
        )
        self.assertEqual(app._haul_params, {"commodity": "gold"})

    def test_local_backend_dispatches_through_execution_dependency(self) -> None:
        execution = _FakeExecution()
        host = SimpleNamespace(
            dependencies=SimpleNamespace(execution=execution),
        )
        backend = LocalControlRoomBackend(host)
        route = object()

        backend.dispatch_command("dest sol", skip_delay=True)
        backend.dispatch_destination("Sol", 2.0, raw_command="dest sol")
        backend.dispatch_haul_loop(params={"commodity": "gold"}, raw_command="haul")
        backend.load_trade_route(route)
        backend.handle_haul_prompt("gold")
        backend.handle_haul_confirm_prompt("yes")

        self.assertEqual(
            [call[0] for call in execution.calls],
            [
                "submit_command",
                "dispatch_destination",
                "dispatch_haul_loop",
                "load_trade_route",
                "handle_haul_prompt",
                "handle_haul_confirm_prompt",
            ],
        )
        self.assertEqual(
            execution.calls[2],
            (
                "dispatch_haul_loop",
                (),
                {
                    "params": {"commodity": "gold"},
                    "skip_delay": False,
                    "raw_command": "haul",
                },
            ),
        )
