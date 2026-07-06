from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edap.actions import ActionDispatchResult
from edap.config import default_haul_routine_defaults
from edap.control_room.routines_travel import parse_travel_command
from edap.routines._base import RoutineResult
from edap.routines.callbacks import noop_progress
from edap.routines.haul_support import HaulMarketSettings, HaulRuntime, HaulTiming, HaulTravelSettings
from edap.routines.travel import TravelDestination, travel_to_station
from edap.tts import AnnouncementId
from tests.fakes import FakeShipControls, FakeWatcher


_DEFAULTS = default_haul_routine_defaults()


def _runtime(
    journal_dir: Path,
    *,
    controls: FakeShipControls | None = None,
    watcher: FakeWatcher | None = None,
    progress: list[str] | None = None,
    announcements: list[tuple[AnnouncementId, dict[str, object]]] | None = None,
) -> HaulRuntime:
    return HaulRuntime(
        controls=controls or FakeShipControls(),
        watcher=watcher or FakeWatcher([]),
        journal_dir=journal_dir,
        market_path=journal_dir / "Market.json",
        timing=HaulTiming(
            step_delay_s=0.0,
            max_hold_s=1.0,
            dock_timeout_s=30.0,
            request_timeout_s=10.0,
            undock_timeout_s=10.0,
            undock_no_track_timeout_s=10.0,
            trade_timeout_s=10.0,
            settle_s=0.0,
            galaxy_map_settle_s=0.0,
            supercruise_exit_settle_s=0.0,
            boost_settle_s=0.0,
            deny_retry_delay_s=0.0,
            mass_lock_boost_delay_s=0.0,
            post_sell_settle_s=0.0,
            nav_panel_open_delay_s=0.0,
        ),
        market=HaulMarketSettings(
            buy_hold_segments=_DEFAULTS.market_buy_hold_segments,
            sell_quantity_restore_taps=0,
            sell_quantity_restore_tap_delay_s=0.0,
            critical_level_multiplier=1.0,
        ),
        travel=HaulTravelSettings(
            auto_hyperspace_engage=True,
            open_nav_panel_after_hyperspace_arrival=True,
            max_dock_retries=3,
        ),
        time_fn=_ticking_clock(),
        sleeper=lambda _seconds: None,
        progress_fn=progress.append if progress is not None else noop_progress,
        announce_fn=(
            lambda message_id, **values: announcements.append((message_id, values))
            if announcements is not None
            else None
        ),
    )


def _ticking_clock(start: float = 0.0, step: float = 1.0):
    current = start

    def _now() -> float:
        nonlocal current
        current += step
        return current

    return _now


class TravelRoutineTests(unittest.TestCase):
    def test_parse_travel_command_accepts_optional_station(self) -> None:
        self.assertEqual(parse_travel_command("Sol"), ("Sol", ""))
        self.assertEqual(parse_travel_command("Sol / Abraham Lincoln"), ("Sol", "Abraham Lincoln"))
        self.assertEqual(parse_travel_command("Sol / "), ("Sol", ""))
        self.assertIsNone(parse_travel_command(""))
        self.assertIsNone(parse_travel_command(" / Abraham Lincoln"))

    def test_same_system_supercruise_announces_station_and_opens_nav_panel(self) -> None:
        controls = FakeShipControls()
        announcements: list[tuple[AnnouncementId, dict[str, object]]] = []

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                "\n".join(
                    [
                        '{"event":"Location","Docked":false,"StarSystem":"Sol"}',
                        '{"event":"SupercruiseEntry","StarSystem":"Sol"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            runtime = _runtime(journal_dir, controls=controls, announcements=announcements)

            with patch("edap.routines.transit.dock") as dock_mock:
                dock_mock.return_value = RoutineResult(
                    action="dock",
                    dispatch=ActionDispatchResult(action="dock", status="ok"),
                )
                result = travel_to_station(
                    runtime,
                    destination=TravelDestination(system="Sol", station="Abraham Lincoln"),
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertIn({"action": "FocusLeftPanel", "repeat": 1, "hold_s": 0.0}, controls.calls)
        self.assertIn(
            (AnnouncementId.ARRIVAL_NEXT_STATION, {"station_name": "Abraham Lincoln"}),
            announcements,
        )
        dock_mock.assert_called_once()

    def test_docked_start_uses_shared_undock_route_then_transit(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": "Jameson Memorial"}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"Location","Docked":true,"StarSystem":"Shinrarta Dezhra","StationName":"Jameson Memorial"}\n',
                encoding="utf-8",
            )
            runtime = _runtime(journal_dir, controls=controls, watcher=watcher)

            with (
                patch("edap.routines.transit.set_gal_map_destination") as set_route_mock,
                patch("edap.routines.travel._travel_transit") as transit_mock,
            ):
                set_route_mock.return_value = RoutineResult(
                    action="set_dest",
                    dispatch=ActionDispatchResult(action="set_dest", status="ok"),
                )
                transit_mock.return_value = RoutineResult(
                    action="travel",
                    dispatch=ActionDispatchResult(action="travel", status="ok"),
                )
                result = travel_to_station(
                    runtime,
                    destination=TravelDestination(system="Sol", station="Abraham Lincoln"),
                )

        self.assertEqual(result.dispatch.status, "ok")
        set_route_mock.assert_called_once()
        transit_mock.assert_called_once()

    def test_system_only_travel_completes_after_arrival_without_station_docking(self) -> None:
        progress: list[str] = []
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": "Sol"}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            runtime = _runtime(journal_dir, watcher=watcher, progress=progress)

            with patch("edap.routines.transit.dock") as dock_mock:
                result = travel_to_station(
                    runtime,
                    destination=TravelDestination(system="Sol"),
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(result.details, {"system": "Sol", "station": ""})
        self.assertIn("Arrived in Sol system; travel complete.", progress)
        dock_mock.assert_not_called()

    def test_system_only_travel_already_in_system_does_not_undock(self) -> None:
        controls = FakeShipControls()
        progress: list[str] = []

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"Location","Docked":true,"StarSystem":"Sol","StationName":"Abraham Lincoln"}\n',
                encoding="utf-8",
            )
            runtime = _runtime(journal_dir, controls=controls, progress=progress)

            result = travel_to_station(
                runtime,
                destination=TravelDestination(system="Sol"),
            )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(controls.calls, [])
        self.assertIn("Already in Sol system; travel complete.", progress)


if __name__ == "__main__":
    unittest.main()
