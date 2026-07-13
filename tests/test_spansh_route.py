from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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
            # First hop lands in "Neutron A"; second hop lands in "Xinca".
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

    def test_timeout_returns_error_naming_failed_waypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            watcher = FakeWatcher([])
            runtime = _runtime(journal_dir, FakeShipControls(), watcher)
            result = fly_spansh_route(
                runtime,
                route=_route([("Sol", False), ("Xinca", False)]),
                per_hop_timeout_s=0.0,
            )
        self.assertEqual(result.dispatch.status, "error")
        self.assertIn("Xinca", result.dispatch.reason or "")
        self.assertEqual(result.details, {"waypoint_index": 1, "waypoint_system": "Xinca"})


if __name__ == "__main__":
    unittest.main()
