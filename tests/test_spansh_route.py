from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edap.actions import ActionDispatchResult
from edap.routines._base import RoutineResult
from edap.routines.callbacks import noop_announce, noop_progress
from edap.routines.runtime import RoutineRuntime, RoutineTiming, RoutineTravelSettings
from edap.routines.spansh_route import fly_spansh_route
from edap.routing.types import Route, RouteWaypoint, SpanshMetadata
from edap.tts import AnnouncementId
from tests.fakes import FakeShipControls, FakeWatcher


_TIMING = RoutineTiming(
    step_delay_s=0.0,
    dock_timeout_s=1.0,
    request_timeout_s=1.0,
    undock_timeout_s=1.0,
    undock_no_track_timeout_s=1.0,
    settle_s=0.0,
    galaxy_map_settle_s=0.0,
    supercruise_exit_settle_s=0.0,
    boost_settle_s=0.0,
    deny_retry_delay_s=0.0,
    mass_lock_boost_delay_s=0.0,
    nav_panel_open_delay_s=0.0,
)


def _waypoint(system: str, *, neutron: bool = False) -> RouteWaypoint:
    return RouteWaypoint(
        system=system,
        star_class=None,
        neutron_boost=neutron,
        x=0.0, y=0.0, z=0.0,
        ly_from_prev=0.0,
        jumps_from_prev=1,
    )


def _route(systems: list[tuple[str, bool]]) -> Route:
    waypoints = tuple(_waypoint(sys, neutron=neu) for sys, neu in systems)
    return Route(
        waypoints=waypoints,
        total_ly=0.0,
        total_jumps=len(systems) - 1,
        neutron_count=sum(1 for _, neu in systems if neu),
        source="spansh",
        source_system=systems[0][0],
        destination_system=systems[-1][0],
        metadata=SpanshMetadata(efficiency=60, supercharge_multiplier=6, galaxy_map_visits=len(systems) - 1),
    )


def _clock():
    t = [0.0]

    def now() -> float:
        value = t[0]
        t[0] += 0.01
        return value

    return now


def _runtime(
    journal_dir: Path,
    controls: FakeShipControls,
    watcher: FakeWatcher,
    *,
    progress=None,
    announcements=None,
) -> RoutineRuntime:
    return RoutineRuntime(
        controls=controls,
        watcher=watcher,
        journal_dir=journal_dir,
        timing=_TIMING,
        travel=RoutineTravelSettings(
            auto_hyperspace_engage=False,
            open_nav_panel_after_hyperspace_arrival=False,
            max_dock_retries=1,
        ),
        time_fn=_clock(),
        sleeper=lambda _s: None,
        progress_fn=progress.append if progress is not None else noop_progress,
        announce_fn=(
            (lambda mid, **v: announcements.append((mid, v)))
            if announcements is not None
            else noop_announce
        ),
    )


def _write_market_json(journal_dir: Path, *, station: str, system: str) -> None:
    (journal_dir / "Market.json").write_text(
        json.dumps({"StationName": station, "StarSystem": system}),
        encoding="utf-8",
    )


def _ok_result(action: str) -> RoutineResult:
    return RoutineResult(
        action=action,
        dispatch=ActionDispatchResult(action=action, status="ok"),
    )


class SpanshRouteTests(unittest.TestCase):
    def test_rejects_route_with_only_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            runtime = _runtime(journal_dir, FakeShipControls(), FakeWatcher([]))
            result = fly_spansh_route(runtime, route=_route([("Sol", False)]))
        self.assertEqual(result.dispatch.status, "error")

    def test_happy_path_two_hops_announces_neutron(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            watcher = FakeWatcher([
                [{"event": "FSDJump", "StarSystem": "Neutron A"}],
                [{"event": "FSDJump", "StarSystem": "Xinca"}],
            ])
            announcements: list[tuple[AnnouncementId, dict]] = []
            runtime = _runtime(
                journal_dir,
                FakeShipControls(),
                watcher,
                announcements=announcements,
            )
            result = fly_spansh_route(
                runtime,
                route=_route([("Sol", False), ("Neutron A", True), ("Xinca", False)]),
            )
        self.assertEqual(result.dispatch.status, "ok")
        neutron_events = [a for a in announcements if a[0] == AnnouncementId.SPANSH_NEUTRON_WAYPOINT_SET]
        self.assertEqual(len(neutron_events), 1)
        self.assertEqual(neutron_events[0][1]["system_name"], "Neutron A")
        completes = [a for a in announcements if a[0] == AnnouncementId.SPANSH_ROUTE_COMPLETE]
        self.assertEqual(len(completes), 1)
        self.assertEqual(completes[0][1]["system_name"], "Xinca")

    def test_arrival_short_circuits_regardless_of_elapsed_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            # time_fn jumps forward by an hour per tick to prove there is no
            # per-hop deadline gating the arrival wait.
            def fast_time():
                t = [0.0]
                def now() -> float:
                    value = t[0]
                    t[0] += 3600.0
                    return value
                return now
            watcher = FakeWatcher([
                [{"event": "FSDJump", "StarSystem": "Xinca"}],
            ])
            runtime = RoutineRuntime(
                controls=FakeShipControls(),
                watcher=watcher,
                journal_dir=journal_dir,
                timing=_TIMING,
                travel=RoutineTravelSettings(
                    auto_hyperspace_engage=False,
                    open_nav_panel_after_hyperspace_arrival=False,
                    max_dock_retries=1,
                ),
                time_fn=fast_time(),
                sleeper=lambda _s: None,
                progress_fn=noop_progress,
                announce_fn=noop_announce,
            )
            result = fly_spansh_route(
                runtime,
                route=_route([("Sol", False), ("Xinca", False)]),
            )
        self.assertEqual(result.dispatch.status, "ok")

    def test_docked_start_uses_undock_primitive_for_first_hop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market_json(journal_dir, station="Jameson Memorial", system="Sol")
            watcher = FakeWatcher([
                [{"event": "FSDJump", "StarSystem": "Neutron A"}],
                [{"event": "FSDJump", "StarSystem": "Xinca"}],
            ])
            runtime = _runtime(journal_dir, FakeShipControls(), watcher)
            with patch(
                "edap.routines.spansh_route.undock_and_route_to_system",
                return_value=_ok_result("undock_and_route_to_system"),
            ) as undock_mock, patch(
                "edap.routines.spansh_route.depart_system_to_route"
            ) as depart_mock, patch(
                "edap.routines.spansh_route.set_galaxy_map_destination_for_transit",
                return_value=True,
            ) as set_map_mock:
                result = fly_spansh_route(
                    runtime,
                    route=_route([("Sol", False), ("Neutron A", False), ("Xinca", False)]),
                )
        self.assertEqual(result.dispatch.status, "ok")
        undock_mock.assert_called_once()
        self.assertEqual(undock_mock.call_args.kwargs["destination_system"], "Neutron A")
        depart_mock.assert_not_called()
        # Waypoint 1 should not be double-set via the galaxy-map primitive;
        # only remaining waypoints (index 2+) get set here.
        set_systems = [call.kwargs["destination_system"] for call in set_map_mock.call_args_list]
        self.assertEqual(set_systems, ["Xinca"])

    def test_normal_space_start_uses_depart_primitive_for_first_hop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            # Build a minimal journal.log so read_ship_state can classify as
            # in_space -> normal_space.
            log = journal_dir / "Journal.2026-07-13T000000.01.log"
            log.write_text(
                json.dumps({"event": "Location", "StarSystem": "Sol", "Docked": False}) + "\n",
                encoding="utf-8",
            )
            watcher = FakeWatcher([
                [{"event": "FSDJump", "StarSystem": "Neutron A"}],
                [{"event": "FSDJump", "StarSystem": "Xinca"}],
            ])
            runtime = _runtime(journal_dir, FakeShipControls(), watcher)
            with patch(
                "edap.routines.spansh_route.read_ship_position"
            ) as position_mock, patch(
                "edap.routines.spansh_route.undock_and_route_to_system"
            ) as undock_mock, patch(
                "edap.routines.spansh_route.depart_system_to_route",
                return_value=_ok_result("depart_system"),
            ) as depart_mock, patch(
                "edap.routines.spansh_route.set_galaxy_map_destination_for_transit",
                return_value=True,
            ) as set_map_mock:
                from edap.routines.transit import ShipPosition
                position_mock.return_value = ShipPosition(status="normal_space", station="", system="Sol")
                result = fly_spansh_route(
                    runtime,
                    route=_route([("Sol", False), ("Neutron A", False), ("Xinca", False)]),
                )
        self.assertEqual(result.dispatch.status, "ok")
        depart_mock.assert_called_once()
        self.assertEqual(depart_mock.call_args.kwargs["destination_system"], "Neutron A")
        undock_mock.assert_not_called()
        set_systems = [call.kwargs["destination_system"] for call in set_map_mock.call_args_list]
        self.assertEqual(set_systems, ["Xinca"])

    def test_docked_start_propagates_undock_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market_json(journal_dir, station="Jameson Memorial", system="Sol")
            runtime = _runtime(journal_dir, FakeShipControls(), FakeWatcher([]))
            failure = RoutineResult(
                action="undock",
                dispatch=ActionDispatchResult(action="undock", status="error", reason="stuck"),
            )
            with patch(
                "edap.routines.spansh_route.undock_and_route_to_system",
                return_value=failure,
            ):
                result = fly_spansh_route(
                    runtime,
                    route=_route([("Sol", False), ("Neutron A", False)]),
                )
        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(result.dispatch.reason, "stuck")


if __name__ == "__main__":
    unittest.main()
