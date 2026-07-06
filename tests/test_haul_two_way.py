from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edap.config import default_haul_routine_defaults
from edap.routines.callbacks import noop_announce, noop_progress
from edap.routines.haul_support import HaulMarketSettings, HaulRuntime, HaulTiming, HaulTravelSettings
from edap.routines.haul_two_way import (
    _HaulCtx,
    Phase,
    StationLeg,
    TwoWayHaulRoute,
    _detect_start_phase,
    _run_market_buy,
    _wait_for_arrival_or_approach_event,
    haul_loop_two_way as _haul_loop_two_way,
)
from edap.routines._base import ActionDispatchResult, RoutineResult
from edap.tts import AnnouncementId
from tests.fakes import FakeShipControls, FakeWatcher

_STATION_1 = "Pawelczyk Dock"
_STATION_2 = "Trevithick Dock"
_SYSTEM_1 = "Sol"
_SYSTEM_2 = "Achenar"
_CARGO_1 = "Aluminium"
_CARGO_2 = "Bertrandite"
_DEFAULTS = default_haul_routine_defaults()


def haul_loop_two_way(*args, **kwargs):
    controls, watcher = args
    journal_dir = kwargs.pop("journal_dir")
    station_1_buying = kwargs.pop("station_1_buying")
    station_2_buying = kwargs.pop("station_2_buying")
    runtime = HaulRuntime(
        controls=controls,
        watcher=watcher,
        journal_dir=journal_dir,
        market_path=journal_dir / "Market.json",
        timing=HaulTiming(
            step_delay_s=kwargs.pop("step_delay_s", 1.0),
            max_hold_s=kwargs.pop("max_hold_s", 10.0),
            dock_timeout_s=kwargs.pop("dock_timeout_s", _DEFAULTS.dock_timeout_seconds),
            request_timeout_s=kwargs.pop("request_timeout_s", 20.0),
            undock_timeout_s=kwargs.pop("undock_timeout_s", _DEFAULTS.undock_timeout_seconds),
            undock_no_track_timeout_s=kwargs.pop(
                "undock_no_track_timeout_s",
                _DEFAULTS.undock_no_track_timeout_seconds,
            ),
            trade_timeout_s=kwargs.pop("trade_timeout_s", 30.0),
            settle_s=kwargs.pop("settle_s", 2.0),
            galaxy_map_settle_s=kwargs.pop("galaxy_map_settle_s", _DEFAULTS.galaxy_map_settle_seconds),
            supercruise_exit_settle_s=kwargs.pop(
                "supercruise_exit_settle_s",
                _DEFAULTS.dock_supercruise_exit_settle_seconds,
            ),
            boost_settle_s=kwargs.pop("boost_settle_s", 3.0),
            deny_retry_delay_s=kwargs.pop("deny_retry_delay_s", 5.0),
            mass_lock_boost_delay_s=kwargs.pop(
                "mass_lock_boost_delay_s",
                _DEFAULTS.mass_lock_boost_delay_seconds,
            ),
            post_sell_settle_s=kwargs.pop("post_sell_settle_s", _DEFAULTS.haul_post_sell_settle_seconds),
            nav_panel_open_delay_s=kwargs.pop(
                "nav_panel_open_delay_s",
                _DEFAULTS.haul_two_way_nav_panel_open_delay_seconds,
            ),
        ),
        market=HaulMarketSettings(
            buy_hold_segments=kwargs.pop("market_buy_hold_segments", _DEFAULTS.market_buy_hold_segments),
            sell_quantity_restore_taps=kwargs.pop(
                "market_sell_quantity_restore_taps",
                _DEFAULTS.market_sell_quantity_restore_taps,
            ),
            sell_quantity_restore_tap_delay_s=kwargs.pop(
                "market_sell_quantity_restore_tap_delay_s",
                _DEFAULTS.market_sell_quantity_restore_tap_delay_seconds,
            ),
            critical_level_multiplier=kwargs.pop(
                "market_critical_level_multiplier",
                _DEFAULTS.market_critical_level_multiplier,
            ),
        ),
        travel=HaulTravelSettings(
            auto_hyperspace_engage=kwargs.pop(
                "auto_hyperspace_engage",
                _DEFAULTS.haul_two_way_auto_hyperspace_engage,
            ),
            open_nav_panel_after_hyperspace_arrival=kwargs.pop(
                "open_nav_panel_after_hyperspace_arrival",
                _DEFAULTS.haul_two_way_open_nav_panel_after_hyperspace_arrival,
            ),
            max_dock_retries=kwargs.pop("max_dock_retries", 3),
        ),
        time_fn=kwargs.pop("time_fn", _ticking_clock()),
        sleeper=kwargs.pop("sleeper", lambda _seconds: None),
        progress_fn=kwargs.pop("progress_fn", noop_progress),
        announce_fn=kwargs.pop("announce_fn", noop_announce),
    )
    route = TwoWayHaulRoute(
        station_1=StationLeg(
            index=1,
            station=kwargs.pop("station_1"),
            system=kwargs.pop("station_1_system", ""),
            on_land=kwargs.pop("station_1_on_land", False),
            buy_commodity=station_1_buying,
            sell_commodity=station_2_buying,
        ),
        station_2=StationLeg(
            index=2,
            station=kwargs.pop("station_2"),
            system=kwargs.pop("station_2_system", ""),
            on_land=kwargs.pop("station_2_on_land", False),
            buy_commodity=station_2_buying,
            sell_commodity=station_1_buying,
        ),
    )
    iterations = kwargs.pop("iterations", 0)
    start_phase = kwargs.pop("start_phase", None)
    stop_requested_fn = kwargs.pop("stop_requested_fn", None)
    pause_requested_fn = kwargs.pop("pause_requested_fn", None)
    pause_fn = kwargs.pop("pause_fn", None)
    phase_updated_fn = kwargs.pop("phase_updated_fn", None)
    if kwargs:
        raise AssertionError(f"Unhandled haul test kwargs: {sorted(kwargs)}")
    return _haul_loop_two_way(
        runtime,
        route=route,
        iterations=iterations,
        start_phase=start_phase,
        stop_requested_fn=stop_requested_fn,
        pause_requested_fn=pause_requested_fn,
        pause_fn=pause_fn,
        phase_updated_fn=phase_updated_fn,
    )


def _ticking_clock(step: float = 0.01):
    t = [0.0]

    def fn() -> float:
        value = t[0]
        t[0] += step
        return value

    return fn


def _write_market(journal_dir: Path, station_name: str, items: list[dict]) -> None:
    (journal_dir / "Market.json").write_text(
        json.dumps({"StationName": station_name, "Items": items}),
        encoding="utf-8",
    )


def _write_cargo(journal_dir: Path, inventory: list[dict]) -> None:
    (journal_dir / "Cargo.json").write_text(
        json.dumps({"Inventory": inventory}),
        encoding="utf-8",
    )


def _write_journal(journal_dir: Path, *events: dict[str, object]) -> None:
    lines = "\n".join(json.dumps(event) for event in events)
    (journal_dir / "Journal.240101000000.01.log").write_text(f"{lines}\n", encoding="utf-8")


def _write_navroute(journal_dir: Path, destination: str) -> None:
    (journal_dir / "NavRoute.json").write_text(
        json.dumps({"Route": [{"StarSystem": destination}]}),
        encoding="utf-8",
    )


def _station_1_leg() -> StationLeg:
    return StationLeg(index=1, station=_STATION_1, system=_SYSTEM_1, buy_commodity=_CARGO_1, sell_commodity=_CARGO_2)


def _station_2_leg() -> StationLeg:
    return StationLeg(index=2, station=_STATION_2, system=_SYSTEM_2, buy_commodity=_CARGO_2, sell_commodity=_CARGO_1)


def _test_haul_runtime(
    journal_dir: Path,
    controls: FakeShipControls,
    watcher: FakeWatcher,
    *,
    progress_fn=noop_progress,
    announce_fn=noop_announce,
) -> HaulRuntime:
    return HaulRuntime(
        controls=controls,
        watcher=watcher,
        journal_dir=journal_dir,
        market_path=journal_dir / "Market.json",
        timing=HaulTiming(
            step_delay_s=0.0,
            max_hold_s=10.0,
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
            sell_quantity_restore_taps=_DEFAULTS.market_sell_quantity_restore_taps,
            sell_quantity_restore_tap_delay_s=_DEFAULTS.market_sell_quantity_restore_tap_delay_seconds,
            critical_level_multiplier=_DEFAULTS.market_critical_level_multiplier,
        ),
        travel=HaulTravelSettings(
            auto_hyperspace_engage=False,
            open_nav_panel_after_hyperspace_arrival=False,
            max_dock_retries=1,
        ),
        time_fn=_ticking_clock(),
        sleeper=lambda _seconds: None,
        progress_fn=progress_fn,
        announce_fn=announce_fn,
    )


class TwoWayHaulLoopTests(unittest.TestCase):
    def test_detect_start_phase_docked_at_station_1_with_full_station_1_cargo_undocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {
                    "event": "Docked",
                    "StationName": _STATION_1,
                    "StarSystem": _SYSTEM_1,
                    "CargoCapacity": 64,
                },
            )
            _write_cargo(journal_dir, [{"Name": "aluminium", "Count": 64, "Stolen": 0}])

            phase = _detect_start_phase(
                journal_dir,
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
                progress_fn=noop_progress,
            )

        self.assertEqual(phase, Phase.UNDOCK_STATION_1)

    def test_detect_start_phase_docked_at_station_2_with_full_station_2_cargo_undocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {
                    "event": "Docked",
                    "StationName": _STATION_2,
                    "StarSystem": _SYSTEM_2,
                    "CargoCapacity": 64,
                },
            )
            _write_cargo(journal_dir, [{"Name": "bertrandite", "Count": 64, "Stolen": 0}])

            phase = _detect_start_phase(
                journal_dir,
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
                progress_fn=noop_progress,
            )

        self.assertEqual(phase, Phase.UNDOCK_STATION_2)

    def test_detect_start_phase_matches_elite_raw_cargo_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {
                    "event": "Docked",
                    "StationName": _STATION_2,
                    "StarSystem": _SYSTEM_2,
                    "CargoCapacity": 64,
                },
            )
            _write_cargo(journal_dir, [{"Name": "$aluminium_name;", "Count": 64, "Stolen": 0}])

            phase = _detect_start_phase(
                journal_dir,
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
                progress_fn=noop_progress,
            )

        self.assertEqual(phase, Phase.AT_STATION_2_SELL)

    def test_detect_start_phase_docked_at_station_1_with_partial_station_1_cargo_stays_in_buy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {
                    "event": "Docked",
                    "StationName": _STATION_1,
                    "StarSystem": _SYSTEM_1,
                    "CargoCapacity": 64,
                },
            )
            _write_cargo(journal_dir, [{"Name": "aluminium", "Count": 20, "Stolen": 0}])

            phase = _detect_start_phase(
                journal_dir,
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
                progress_fn=noop_progress,
            )

        self.assertEqual(phase, Phase.AT_STATION_1_BUY)

    def test_detect_start_phase_docked_at_station_2_without_buy_commodity_undocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {
                    "event": "Docked",
                    "StationName": _STATION_2,
                    "StarSystem": _SYSTEM_2,
                    "CargoCapacity": 64,
                },
            )
            _write_cargo(journal_dir, [])

            phase = _detect_start_phase(
                journal_dir,
                station_1=_station_1_leg(),
                station_2=StationLeg(
                    index=2,
                    station=_STATION_2,
                    system=_SYSTEM_2,
                    buy_commodity="",
                    sell_commodity=_CARGO_1,
                ),
                progress_fn=noop_progress,
            )

        self.assertEqual(phase, Phase.UNDOCK_STATION_2)

    def test_detect_start_phase_in_station_1_system_supercruise_with_empty_hold_returns_to_station_1_buy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "Location", "Docked": False, "StarSystem": _SYSTEM_1},
                {"event": "SupercruiseEntry", "StarSystem": _SYSTEM_1},
            )
            _write_cargo(journal_dir, [])

            phase = _detect_start_phase(
                journal_dir,
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
                progress_fn=noop_progress,
            )

        self.assertEqual(phase, Phase.TRANSIT_TO_STATION_1)

    def test_detect_start_phase_in_station_2_system_supercruise_with_empty_hold_returns_to_station_2_buy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "Location", "Docked": False, "StarSystem": _SYSTEM_2},
                {"event": "SupercruiseEntry", "StarSystem": _SYSTEM_2},
            )
            _write_cargo(journal_dir, [])

            phase = _detect_start_phase(
                journal_dir,
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
                progress_fn=noop_progress,
            )

        self.assertEqual(phase, Phase.TRANSIT_TO_STATION_2)

    def test_detect_start_phase_in_station_1_system_supercruise_without_station_1_buy_continues_to_station_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "Location", "Docked": False, "StarSystem": _SYSTEM_1},
                {"event": "SupercruiseEntry", "StarSystem": _SYSTEM_1},
            )
            _write_cargo(journal_dir, [])

            phase = _detect_start_phase(
                journal_dir,
                station_1=StationLeg(
                    index=1,
                    station=_STATION_1,
                    system=_SYSTEM_1,
                    buy_commodity="",
                    sell_commodity=_CARGO_2,
                ),
                station_2=_station_2_leg(),
                progress_fn=noop_progress,
            )

        self.assertEqual(phase, Phase.TRANSIT_TO_STATION_2)

    def test_detect_start_phase_docked_at_unknown_station_returns_error_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {
                    "event": "Docked",
                    "StationName": "Jameson Memorial",
                    "StarSystem": "Shinrarta Dezhra",
                    "CargoCapacity": 64,
                },
            )
            _write_cargo(journal_dir, [])

            result = _detect_start_phase(
                journal_dir,
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
                progress_fn=noop_progress,
            )

        self.assertIsInstance(result, RoutineResult)
        assert isinstance(result, RoutineResult)
        self.assertEqual(result.dispatch.status, "error")
        self.assertIn("Docked at unknown station", result.dispatch.reason)
        self.assertIn(_STATION_1, result.dispatch.reason)
        self.assertIn(_STATION_2, result.dispatch.reason)

    def test_one_iteration_happy_path(self) -> None:
        controls = FakeShipControls()
        market_calls: list[tuple[str, str]] = []
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(
                journal_dir,
                [{"Name": "bertrandite", "Count": 64, "Stolen": 0}],
            )
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                def fake_sell(controls, watcher, **kwargs):
                    market_calls.append(("sell", kwargs["target"]))
                    _write_cargo(journal_dir, [])
                    return RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )

                market_sell_mock.side_effect = fake_sell

                def fake_buy(controls, watcher, **kwargs):
                    market_calls.append(("buy", kwargs["target"]))
                    _write_cargo(journal_dir, [{"Name": kwargs["target"], "Count": 64, "Stolen": 0}])
                    return RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )

                market_buy_mock.side_effect = fake_buy
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(
            market_calls,
            [
                ("sell", _CARGO_2),
                ("buy", _CARGO_1),
                ("sell", _CARGO_1),
                ("buy", _CARGO_2),
            ],
        )
        self.assertEqual(
            [call["action"] for call in controls.calls if call["action"] in {"SetSpeed100", "UseBoostJuice"}].count("SetSpeed100"),
            2,
        )

    def test_one_iteration_skips_empty_station_2_buy_leg(self) -> None:
        controls = FakeShipControls()
        market_calls: list[tuple[str, str]] = []
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [{"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000}],
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                market_sell_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("sell", kwargs["target"])) or RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )
                )
                def fake_buy(controls, watcher, **kwargs):
                    market_calls.append(("buy", kwargs["target"]))
                    _write_cargo(journal_dir, [{"Name": kwargs["target"], "Count": 64, "Stolen": 0}])
                    return RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )

                market_buy_mock.side_effect = fake_buy
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying="",
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(
            market_calls,
            [
                ("buy", _CARGO_1),
                ("sell", _CARGO_1),
            ],
        )

    def test_buy_phase_sells_wrong_cargo_and_retries_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_cargo(journal_dir, [])
            controls = FakeShipControls()
            watcher = FakeWatcher([])
            progress: list[str] = []
            announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
            ctx = _HaulCtx(
                runtime=_test_haul_runtime(
                    journal_dir,
                    controls,
                    watcher,
                    progress_fn=progress.append,
                    announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
                ),
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
            )
            calls: list[tuple[str, str]] = []

            def fake_buy(controls, watcher, **kwargs):
                calls.append(("buy", kwargs["target"]))
                if len([call for call in calls if call[0] == "buy"]) == 1:
                    _write_cargo(journal_dir, [{"Name": "Gold", "Count": 64, "Stolen": 0}])
                    return RoutineResult(
                        action="MarketBuy",
                        dispatch=ActionDispatchResult(
                            action="MarketBuy",
                            status="error",
                            reason="wrong commodity bought: Gold (expected Aluminium)",
                        ),
                        details={
                            "phase": "wrong_item",
                            "wrong_commodity": "Gold",
                            "target": _CARGO_1,
                        },
                    )
                _write_cargo(journal_dir, [{"Name": _CARGO_1, "Count": 64, "Stolen": 0}])
                return RoutineResult(
                    action="MarketBuy",
                    dispatch=ActionDispatchResult(action="MarketBuy", status="ok"),
                )

            def fake_sell(controls, watcher, **kwargs):
                calls.append(("sell", kwargs["target"]))
                _write_cargo(journal_dir, [])
                return RoutineResult(
                    action="MarketSell",
                    dispatch=ActionDispatchResult(action="MarketSell", status="ok"),
                )

            with patch("edap.routines.haul_two_way.market_buy", side_effect=fake_buy), patch(
                "edap.routines.haul_two_way.market_sell",
                side_effect=fake_sell,
            ):
                result, next_phase = _run_market_buy(ctx, leg=ctx.station_1, next_phase=Phase.UNDOCK_STATION_1)

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(next_phase, Phase.UNDOCK_STATION_1)
        self.assertEqual(ctx.wrong_buy_count, 1)
        self.assertEqual(calls, [("buy", _CARGO_1), ("sell", "Gold"), ("buy", _CARGO_1)])
        self.assertIn("Wrong cargo sold; retrying intended buy.", progress)
        self.assertIn((AnnouncementId.SELLING_CARGO, {"commodity_name": "Gold"}), announcements)

    def test_buy_phase_aborts_when_unrelated_cargo_is_already_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_cargo(journal_dir, [{"Name": "Gold", "Count": 64, "Stolen": 0}])
            controls = FakeShipControls()
            watcher = FakeWatcher([])
            progress: list[str] = []
            announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
            ctx = _HaulCtx(
                runtime=_test_haul_runtime(
                    journal_dir,
                    controls,
                    watcher,
                    progress_fn=progress.append,
                    announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
                ),
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
            )

            with patch("edap.routines.haul_two_way.market_buy") as market_buy_mock, patch(
                "edap.routines.haul_two_way.market_sell"
            ) as market_sell_mock:
                result, next_phase = _run_market_buy(ctx, leg=ctx.station_1, next_phase=Phase.UNDOCK_STATION_1)

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(next_phase, Phase.UNDOCK_STATION_1)
        market_buy_mock.assert_not_called()
        market_sell_mock.assert_not_called()
        self.assertIn("non-haul cargo (64t Gold)", result.dispatch.reason or "")
        self.assertIn("Clear or sell that cargo manually", result.dispatch.reason or "")
        self.assertTrue(any("non-haul cargo (64t Gold)" in line for line in progress))
        self.assertIn((AnnouncementId.HAUL_ABORTED, {}), announcements)

    def test_buy_phase_allows_existing_expected_cargo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_cargo(journal_dir, [{"Name": _CARGO_1, "Count": 20, "Stolen": 0}])
            controls = FakeShipControls()
            watcher = FakeWatcher([])
            ctx = _HaulCtx(
                runtime=_test_haul_runtime(journal_dir, controls, watcher),
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
            )
            calls: list[tuple[str, str]] = []

            def fake_buy(controls, watcher, **kwargs):
                calls.append(("buy", kwargs["target"]))
                _write_cargo(journal_dir, [{"Name": _CARGO_1, "Count": 64, "Stolen": 0}])
                return RoutineResult(
                    action="MarketBuy",
                    dispatch=ActionDispatchResult(action="MarketBuy", status="ok"),
                )

            with patch("edap.routines.haul_two_way.market_buy", side_effect=fake_buy), patch(
                "edap.routines.haul_two_way.market_sell"
            ) as market_sell_mock:
                result, next_phase = _run_market_buy(ctx, leg=ctx.station_1, next_phase=Phase.UNDOCK_STATION_1)

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(next_phase, Phase.UNDOCK_STATION_1)
        self.assertEqual(calls, [("buy", _CARGO_1)])
        market_sell_mock.assert_not_called()

    def test_buy_phase_aborts_when_status_reports_cargo_but_manifest_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_cargo(journal_dir, [])
            (journal_dir / "Status.json").write_text(
                json.dumps({"Flags": 0, "Cargo": 429}),
                encoding="utf-8",
            )
            controls = FakeShipControls()
            watcher = FakeWatcher([])
            progress: list[str] = []
            announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
            ctx = _HaulCtx(
                runtime=_test_haul_runtime(
                    journal_dir,
                    controls,
                    watcher,
                    progress_fn=progress.append,
                    announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
                ),
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
            )

            with patch("edap.routines.haul_two_way._read_cargo_json", return_value=[]), patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                result, next_phase = _run_market_buy(ctx, leg=ctx.station_1, next_phase=Phase.UNDOCK_STATION_1)

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(next_phase, Phase.UNDOCK_STATION_1)
        market_buy_mock.assert_not_called()
        self.assertIn("cargo hold already reports 429t loaded", result.dispatch.reason or "")
        self.assertIn("relog", result.dispatch.reason or "")
        self.assertTrue(any("cargo hold already reports 429t loaded" in line for line in progress))
        self.assertIn((AnnouncementId.HAUL_CARGO_STATE_STALE, {"cargo_count": 429}), announcements)

    def test_buy_phase_aborts_after_second_wrong_cargo_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_cargo(journal_dir, [])
            controls = FakeShipControls()
            watcher = FakeWatcher([])
            progress: list[str] = []
            announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
            ctx = _HaulCtx(
                runtime=_test_haul_runtime(
                    journal_dir,
                    controls,
                    watcher,
                    progress_fn=progress.append,
                    announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
                ),
                station_1=_station_1_leg(),
                station_2=_station_2_leg(),
            )
            wrong_cargos = ["Gold", "Silver"]
            calls: list[tuple[str, str]] = []

            def fake_buy(controls, watcher, **kwargs):
                calls.append(("buy", kwargs["target"]))
                wrong_cargo = wrong_cargos.pop(0)
                _write_cargo(journal_dir, [{"Name": wrong_cargo, "Count": 64, "Stolen": 0}])
                return RoutineResult(
                    action="MarketBuy",
                    dispatch=ActionDispatchResult(
                        action="MarketBuy",
                        status="error",
                        reason=f"wrong commodity bought: {wrong_cargo} (expected Aluminium)",
                    ),
                    details={
                        "phase": "wrong_item",
                        "wrong_commodity": wrong_cargo,
                        "target": _CARGO_1,
                    },
                )

            def fake_sell(controls, watcher, **kwargs):
                calls.append(("sell", kwargs["target"]))
                _write_cargo(journal_dir, [])
                return RoutineResult(
                    action="MarketSell",
                    dispatch=ActionDispatchResult(action="MarketSell", status="ok"),
                )

            with patch("edap.routines.haul_two_way.market_buy", side_effect=fake_buy), patch(
                "edap.routines.haul_two_way.market_sell",
                side_effect=fake_sell,
            ):
                result, next_phase = _run_market_buy(ctx, leg=ctx.station_1, next_phase=Phase.UNDOCK_STATION_1)

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(next_phase, Phase.UNDOCK_STATION_1)
        self.assertEqual(ctx.wrong_buy_count, 2)
        self.assertIn("Wrong cargo bought twice", result.dispatch.reason or "")
        self.assertEqual(
            calls,
            [
                ("buy", _CARGO_1),
                ("sell", "Gold"),
                ("buy", _CARGO_1),
                ("sell", "Silver"),
            ],
        )
        self.assertIn((AnnouncementId.HAUL_WRONG_CARGO_ABORTED, {}), announcements)
        self.assertTrue(any(line.startswith("Error: Wrong cargo bought twice") for line in progress))

    def test_stop_requested_halts_at_station_1_sale_boundary_before_buy(self) -> None:
        controls = FakeShipControls()
        market_calls: list[tuple[str, str]] = []
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(
                journal_dir,
                [{"Name": "bertrandite", "Count": 64, "Stolen": 0}],
            )
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                market_sell_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("sell", kwargs["target"])) or RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )
                )
                market_buy_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("buy", kwargs["target"])) or RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                    stop_requested_fn=lambda: True,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(
            market_calls,
            [
                ("sell", _CARGO_2),
            ],
        )

    def test_stop_requested_halts_immediately_when_resumed_at_station_1_buy(self) -> None:
        controls = FakeShipControls()
        market_calls: list[tuple[str, str]] = []
        watcher = FakeWatcher([])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {
                    "event": "Docked",
                    "StationName": _STATION_1,
                    "StarSystem": _SYSTEM_1,
                    "CargoCapacity": 64,
                },
            )
            _write_cargo(journal_dir, [{"Name": "aluminium", "Count": 20, "Stolen": 0}])
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                ],
            )

            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                market_sell_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("sell", kwargs["target"])) or RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )
                )
                market_buy_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("buy", kwargs["target"])) or RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                    stop_requested_fn=lambda: True,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(market_calls, [])

    def test_pause_requested_waits_at_station_2_before_buy(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([])
        paused_phases: list[Phase] = []
        pause_requested = [True]

        def fake_phase_runner(_ctx):
            return RoutineResult(
                action="phase",
                dispatch=ActionDispatchResult(action="phase", status="ok"),
            ), Phase.TRANSIT_TO_STATION_1

        def fake_transit_runner(_ctx):
            return RoutineResult(
                action="transit",
                dispatch=ActionDispatchResult(action="transit", status="ok"),
            ), Phase.AT_STATION_1_SELL

        def pause_fn(phase: Phase) -> None:
            paused_phases.append(phase)
            pause_requested[0] = False

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {
                    "event": "Docked",
                    "StationName": _STATION_2,
                    "StarSystem": _SYSTEM_2,
                    "CargoCapacity": 64,
                },
            )
            _write_cargo(journal_dir, [])
            with patch.dict(
                "edap.routines.haul_two_way._PHASE_RUNNERS",
                {
                    Phase.AT_STATION_2_BUY: fake_phase_runner,
                    Phase.TRANSIT_TO_STATION_1: fake_transit_runner,
                },
                clear=True,
            ):
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.AT_STATION_2_BUY,
                    pause_requested_fn=lambda: pause_requested[0],
                    pause_fn=pause_fn,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(paused_phases, [Phase.AT_STATION_2_BUY])

    def test_can_start_from_station_2_phase(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])
        phases: list[Phase] = []

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_2,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_navroute(journal_dir, _SYSTEM_1)
            result = haul_loop_two_way(
                controls,
                watcher,
                journal_dir=journal_dir,
                station_1=_STATION_1,
                station_1_buying=_CARGO_1,
                station_1_system=_SYSTEM_1,
                station_2=_STATION_2,
                station_2_buying=_CARGO_2,
                station_2_system=_SYSTEM_2,
                iterations=1,
                start_phase=Phase.DEPART_STATION_2_SYSTEM,
                step_delay_s=0.0,
                settle_s=0.0,
                boost_settle_s=0.0,
                dock_timeout_s=30.0,
                request_timeout_s=10.0,
                undock_timeout_s=10.0,
                trade_timeout_s=10.0,
                time_fn=_ticking_clock(),
                sleeper=lambda _: None,
                phase_updated_fn=phases.append,
            )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(phases, [Phase.DEPART_STATION_2_SYSTEM, Phase.TRANSIT_TO_STATION_1])
        hyperspace_calls = [call for call in controls.calls if call["action"] == "HyperSuperCombination"]
        self.assertEqual(len(hyperspace_calls), 1)

    def test_departure_engages_hyper_super_combination_after_mass_lock_clears_by_default(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_navroute(journal_dir, _SYSTEM_2)
            _write_cargo(journal_dir, [])
            (journal_dir / "Status.json").write_text(json.dumps({"Flags": 0}), encoding="utf-8")

            with patch("edap.routines.haul_two_way.dock") as dock_mock:
                dock_mock.return_value = RoutineResult(
                    action="dock",
                    dispatch=ActionDispatchResult(action="dock", status="error", reason="stop after first transit"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.DEPART_STATION_1_SYSTEM,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "error")
        actions = [call["action"] for call in controls.calls]
        self.assertIn("HyperSuperCombination", actions)
        self.assertLess(actions.index("SetSpeed100"), actions.index("HyperSuperCombination"))

    def test_departure_skips_hyper_super_combination_when_auto_hyperspace_disabled(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            (journal_dir / "Status.json").write_text(json.dumps({"Flags": 0}), encoding="utf-8")

            with patch("edap.routines.haul_two_way.dock") as dock_mock:
                dock_mock.return_value = RoutineResult(
                    action="dock",
                    dispatch=ActionDispatchResult(action="dock", status="error", reason="stop after first transit"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.DEPART_STATION_1_SYSTEM,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    auto_hyperspace_engage=False,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "error")
        self.assertNotIn("HyperSuperCombination", [call["action"] for call in controls.calls])

    def test_departure_warns_and_continues_when_galaxy_map_route_is_unconfirmed(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "FSDJump", "StarSystem": _SYSTEM_2}],
        ])
        messages: list[str] = []
        announcements: list[tuple[AnnouncementId, dict[str, object]]] = []

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            (journal_dir / "Status.json").write_text(json.dumps({"Flags": 0}), encoding="utf-8")
            route_failure = RoutineResult(
                action="GalaxyMapOpen",
                dispatch=ActionDispatchResult(
                    action="GalaxyMapOpen",
                    status="error",
                    reason="route mismatch: expected 'Achenar', got 'Sol'",
                ),
            )

            with (
                patch("edap.routines.haul_support.set_gal_map_destination", side_effect=[route_failure, route_failure]) as route_mock,
                patch("edap.routines.haul_two_way.dock") as dock_mock,
            ):
                dock_mock.return_value = RoutineResult(
                    action="dock",
                    dispatch=ActionDispatchResult(action="dock", status="error", reason="stop after manual jump"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.UNDOCK_STATION_1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                    progress_fn=messages.append,
                    announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
                )

        self.assertEqual(result.dispatch.reason, "stop after manual jump")
        self.assertEqual(route_mock.call_count, 2)
        dock_mock.assert_called_once()
        self.assertTrue(any("route to Achenar is unconfirmed" in message for message in messages))
        self.assertTrue(any("Skipping automatic FSD engage" in message for message in messages))
        self.assertIn((AnnouncementId.ROUTE_UNCONFIRMED, {"system_name": _SYSTEM_2}), announcements)
        self.assertNotIn("HyperSuperCombination", [call["action"] for call in controls.calls])

    def test_transit_opens_nav_panel_after_hyperspace_arrival_by_default(self) -> None:
        controls = FakeShipControls()
        sleep_calls: list[float] = []
        announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": _SYSTEM_2}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock:
                market_sell_mock.return_value = RoutineResult(
                    action="market_sell",
                    dispatch=ActionDispatchResult(action="market_sell", status="error", reason="stop after transit"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.TRANSIT_TO_STATION_2,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda s: sleep_calls.append(s),
                    announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
                )

        self.assertEqual(result.dispatch.status, "error")
        actions = [call["action"] for call in controls.calls]
        self.assertEqual(actions.count("FocusLeftPanel"), 2)
        self.assertLess(actions.index("FocusLeftPanel"), actions.index("UseBoostJuice"))
        self.assertIn(3.0, sleep_calls)
        self.assertIn(
            (AnnouncementId.ARRIVAL_NEXT_STATION, {"station_name": _STATION_2}),
            announcements,
        )

    def test_transit_skips_nav_panel_when_disabled(self) -> None:
        controls = FakeShipControls()
        sleep_calls: list[float] = []
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": _SYSTEM_2}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock:
                market_sell_mock.return_value = RoutineResult(
                    action="market_sell",
                    dispatch=ActionDispatchResult(action="market_sell", status="error", reason="stop after transit"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.TRANSIT_TO_STATION_2,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    open_nav_panel_after_hyperspace_arrival=False,
                    time_fn=_ticking_clock(),
                    sleeper=lambda s: sleep_calls.append(s),
                )

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual([call["action"] for call in controls.calls].count("FocusLeftPanel"), 1)
        self.assertNotIn(3.0, sleep_calls)

    def test_transit_uses_configured_nav_panel_open_delay(self) -> None:
        controls = FakeShipControls()
        sleep_calls: list[float] = []
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": _SYSTEM_2}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock:
                market_sell_mock.return_value = RoutineResult(
                    action="market_sell",
                    dispatch=ActionDispatchResult(action="market_sell", status="error", reason="stop after transit"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.TRANSIT_TO_STATION_2,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    nav_panel_open_delay_s=1.5,
                    time_fn=_ticking_clock(),
                    sleeper=lambda s: sleep_calls.append(s),
                )

        self.assertEqual(result.dispatch.status, "error")
        self.assertIn(1.5, sleep_calls)
        self.assertNotIn(3.0, sleep_calls)

    def test_transit_aborts_docking_after_interdiction_drop(self) -> None:
        controls = FakeShipControls()
        messages: list[str] = []
        announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": _SYSTEM_2}],
            [
                {
                    "event": "ReceiveText",
                    "From_Localised": "Jeremy Linter",
                    "Message_Localised": "I'm coming for you.",
                },
                {
                    "event": "Interdicted",
                    "Submitted": True,
                    "Interdictor": "Jeremy Linter",
                    "IsPlayer": False,
                },
                {"event": "SupercruiseExit", "BodyType": "Planet", "StarSystem": _SYSTEM_2},
            ],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            result = haul_loop_two_way(
                controls,
                watcher,
                journal_dir=journal_dir,
                station_1=_STATION_1,
                station_1_buying=_CARGO_1,
                station_1_system=_SYSTEM_1,
                station_2=_STATION_2,
                station_2_buying=_CARGO_2,
                station_2_system=_SYSTEM_2,
                iterations=1,
                start_phase=Phase.TRANSIT_TO_STATION_2,
                step_delay_s=0.0,
                settle_s=0.0,
                supercruise_exit_settle_s=0.0,
                boost_settle_s=0.0,
                dock_timeout_s=30.0,
                request_timeout_s=10.0,
                undock_timeout_s=10.0,
                trade_timeout_s=10.0,
                time_fn=_ticking_clock(),
                sleeper=lambda _: None,
                progress_fn=messages.append,
                announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
            )

        self.assertEqual(result.action, "Interdicted")
        self.assertEqual(result.dispatch.status, "error")
        self.assertIn("interdicted by Jeremy Linter", result.dispatch.reason)
        self.assertNotIn("UI_Select", [call["action"] for call in controls.calls])
        self.assertTrue(any("Interdiction detected during haul transit" in message for message in messages))
        self.assertIn((AnnouncementId.HAUL_ABORTED, {}), announcements)

    def test_arrival_wait_ignores_intermediate_jump_systems(self) -> None:
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": _SYSTEM_1}],
            [{"event": "FSDJump", "StarSystem": _SYSTEM_2}],
        ])

        arrival_observed, pending_events = _wait_for_arrival_or_approach_event(
            watcher,
            destination_system=_SYSTEM_2,
            deadline=1.0,
            time_fn=_ticking_clock(),
        )

        self.assertTrue(arrival_observed)
        self.assertEqual(pending_events, [])

    def test_transit_hands_off_for_on_land_destination_after_supercruise_exit(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": _SYSTEM_2}],
            [{"event": "SupercruiseExit", "BodyType": "Planet", "StarSystem": _SYSTEM_2}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.dock") as dock_mock:
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    station_2_on_land=True,
                    iterations=1,
                    start_phase=Phase.TRANSIT_TO_STATION_2,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(result.dispatch.reason, "manual landing required")
        dock_mock.assert_not_called()

    def test_undock_skips_galaxy_map_destination_for_same_system_stations(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station", "StarSystem": _SYSTEM_1}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [{"Name": "bertrandite", "Count": 64, "Stolen": 0}])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock, patch("edap.routines.haul_support.set_gal_map_destination") as set_destination_mock:
                market_sell_mock.return_value = RoutineResult(
                    action="market_sell",
                    dispatch=ActionDispatchResult(action="market_sell", status="error", reason="stop after same-system undock transit"),
                )
                market_buy_mock.return_value = RoutineResult(
                    action="market_buy",
                    dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                )

                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_1,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    undock_no_track_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(result.dispatch.reason, "stop after same-system undock transit")
        set_destination_mock.assert_not_called()

    def test_depart_skips_galaxy_map_destination_for_same_system_stations(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [{"event": "SupercruiseExit", "BodyType": "Station", "StarSystem": _SYSTEM_1}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "Location", "Docked": False, "StarSystem": _SYSTEM_1},
                {"event": "Cargo", "Count": 64, "CargoCapacity": 64},
            )
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [{"Name": "aluminium", "Count": 64, "Stolen": 0}])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_support.set_gal_map_destination"
            ) as set_destination_mock:
                market_sell_mock.return_value = RoutineResult(
                    action="market_sell",
                    dispatch=ActionDispatchResult(action="market_sell", status="error", reason="stop after same-system transit"),
                )

                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_1,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    supercruise_exit_settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    undock_no_track_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(result.dispatch.reason, "stop after same-system transit")
        set_destination_mock.assert_not_called()

    def test_resume_in_destination_supercruise_opens_nav_without_waiting_for_new_jump(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "FSDJump", "StarSystem": _SYSTEM_2},
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock:
                market_sell_mock.return_value = RoutineResult(
                    action="market_sell",
                    dispatch=ActionDispatchResult(action="market_sell", status="error", reason="stop after transit"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.TRANSIT_TO_STATION_2,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual([call["action"] for call in controls.calls].count("FocusLeftPanel"), 2)

    def test_auto_detects_station_2_sell_when_docked_with_station_1_cargo(self) -> None:
        controls = FakeShipControls()
        market_calls: list[tuple[str, str]] = []
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "Location", "Docked": True, "StationName": _STATION_2, "StarSystem": _SYSTEM_2},
            )
            _write_market(
                journal_dir,
                _STATION_2,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [{"Name": "aluminium", "Count": 64, "Stolen": 0}])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                def fake_sell(controls, watcher, **kwargs):
                    market_calls.append(("sell", kwargs["target"]))
                    _write_cargo(journal_dir, [])
                    return RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )

                market_sell_mock.side_effect = fake_sell

                def fake_buy(controls, watcher, **kwargs):
                    market_calls.append(("buy", kwargs["target"]))
                    _write_cargo(journal_dir, [{"Name": "bertrandite", "Count": 64, "Stolen": 0}])
                    return RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )

                market_buy_mock.side_effect = fake_buy
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(market_calls[0:2], [("sell", _CARGO_1), ("buy", _CARGO_2)])

    def test_auto_detects_station_2_buy_when_docked_empty(self) -> None:
        controls = FakeShipControls()
        market_calls: list[tuple[str, str]] = []
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "Location", "Docked": True, "StationName": _STATION_2, "StarSystem": _SYSTEM_2},
            )
            _write_market(
                journal_dir,
                _STATION_2,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                market_sell_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("sell", kwargs["target"])) or RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )
                )
                market_buy_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("buy", kwargs["target"])) or RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(market_calls[0], ("buy", _CARGO_2))

    def test_auto_detects_station_2_drop_and_skips_supercruise_exit_wait(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "SupercruiseExit", "BodyType": "Station", "StarSystem": _SYSTEM_2},
            )
            _write_cargo(journal_dir, [{"Name": "aluminium", "Count": 64, "Stolen": 0}])

            with patch("edap.routines.haul_two_way.dock") as dock_mock:
                dock_mock.return_value = RoutineResult(
                    action="dock",
                    dispatch=ActionDispatchResult(action="dock", status="error", reason="stop after first dock call"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(dock_mock.call_count, 1)
        self.assertFalse(dock_mock.call_args.kwargs["wait_for_supercruise_exit"])

    def test_auto_detects_station_2_docking_grant_and_waits_for_docked(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_journal(
                journal_dir,
                {"event": "SupercruiseExit", "BodyType": "Station", "StarSystem": _SYSTEM_2},
                {"event": "DockingGranted", "StationName": _STATION_2, "LandingPad": 7},
            )
            _write_cargo(journal_dir, [{"Name": "aluminium", "Count": 64, "Stolen": 0}])

            with patch("edap.routines.haul_two_way.dock") as dock_mock, patch(
                "edap.routines.haul_two_way.station_refuel_menu"
            ) as station_refuel_menu_mock:
                station_refuel_menu_mock.return_value = RoutineResult(
                    action="UI_Down",
                    dispatch=ActionDispatchResult(action="UI_Down", status="error", reason="stop after wait-for-docked path"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "error")
        dock_mock.assert_not_called()
        station_refuel_menu_mock.assert_called_once()

    def test_auto_detects_station_2_from_market_json_when_journal_lacks_position(self) -> None:
        controls = FakeShipControls()
        market_calls: list[tuple[str, str]] = []
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_2,
                [
                    {
                        "Category": "Metals",
                        "Name": "aluminium",
                        "Name_Localised": _CARGO_1,
                        "DemandBracket": 1,
                        "Stock": 1000,
                        "StarSystem": _SYSTEM_2,
                    },
                    {
                        "Category": "Minerals",
                        "Name": "bertrandite",
                        "Name_Localised": _CARGO_2,
                        "DemandBracket": 1,
                        "Stock": 1000,
                        "StarSystem": _SYSTEM_2,
                    },
                ],
            )
            (journal_dir / "Market.json").write_text(
                json.dumps({
                    "StationName": _STATION_2,
                    "StarSystem": _SYSTEM_2,
                    "Items": [],
                }),
                encoding="utf-8",
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                market_sell_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("sell", kwargs["target"])) or RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )
                )
                market_buy_mock.side_effect = lambda controls, watcher, **kwargs: (
                    market_calls.append(("buy", kwargs["target"])) or RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(market_calls[0], ("buy", _CARGO_2))

    def test_detect_start_phase_prefers_journal_system_over_stale_market_system(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            progress: list[str] = []
            _write_journal(
                journal_dir,
                {"event": "FSDJump", "StarSystem": _SYSTEM_1},
                {"event": "Docked", "StationName": _STATION_1},
            )
            (journal_dir / "Market.json").write_text(
                json.dumps({
                    "StationName": _STATION_1,
                    "StarSystem": _SYSTEM_2,
                    "Items": [],
                }),
                encoding="utf-8",
            )
            _write_cargo(journal_dir, [{"Name": "aluminium", "Count": 64, "Stolen": 0}])
            phase = _detect_start_phase(
                journal_dir,
                station_1=StationLeg(
                    index=1,
                    station=_STATION_1,
                    system=_SYSTEM_1,
                    buy_commodity=_CARGO_1,
                    sell_commodity=_CARGO_2,
                ),
                station_2=StationLeg(
                    index=2,
                    station=_STATION_2,
                    system=_SYSTEM_2,
                    buy_commodity=_CARGO_2,
                    sell_commodity=_CARGO_1,
                ),
                progress_fn=progress.append,
            )

        self.assertEqual(phase, Phase.AT_STATION_1_BUY)
        self.assertTrue(progress)
        self.assertIn(f"system='{_SYSTEM_1}'", progress[-1])
        self.assertNotIn(f"system='{_SYSTEM_2}'", progress[-1])

    def test_undock_aborts_haul_on_no_track_timeout_and_logs_replay_hint(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
        ])
        announcements: list[tuple[object, dict[str, object]]] = []
        messages: list[str] = []

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])

            result = haul_loop_two_way(
                controls,
                watcher,
                journal_dir=journal_dir,
                station_1=_STATION_1,
                station_1_buying=_CARGO_1,
                station_1_system=_SYSTEM_1,
                station_2=_STATION_2,
                station_2_buying=_CARGO_2,
                station_2_system=_SYSTEM_2,
                iterations=1,
                start_phase=Phase.UNDOCK_STATION_1,
                step_delay_s=0.0,
                settle_s=0.0,
                boost_settle_s=0.0,
                dock_timeout_s=30.0,
                request_timeout_s=10.0,
                undock_timeout_s=10.0,
                undock_no_track_timeout_s=0.0,
                trade_timeout_s=10.0,
                time_fn=_ticking_clock(),
                sleeper=lambda _: None,
                progress_fn=messages.append,
                announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
            )

        self.assertEqual(result.dispatch.status, "error")
        self.assertTrue(any("replay / ctrl-r" in message for message in messages))
        self.assertIn((AnnouncementId.HAUL_ABORTED, {}), announcements)
        actions = [call["action"] for call in controls.calls]
        self.assertIn("GalaxyMapOpen", actions)
        self.assertNotIn("UseBoostJuice", actions)

    def test_carrier_exploration_allows_haul_departure_to_continue(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": "Stronghold Carrier", "StationType": "SurfaceStation"}],
            [{"event": "Music", "MusicTrack": "DockingComputer"}],
            [{"event": "Music", "MusicTrack": "Exploration"}],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                "Stronghold Carrier",
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_navroute(journal_dir, _SYSTEM_2)
            _write_cargo(journal_dir, [])
            (journal_dir / "Status.json").write_text(json.dumps({"Flags": 0}), encoding="utf-8")

            with patch("edap.routines.haul_two_way.dock") as dock_mock:
                dock_mock.return_value = RoutineResult(
                    action="dock",
                    dispatch=ActionDispatchResult(action="dock", status="error", reason="stop after first transit"),
                )
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1="Stronghold Carrier",
                    station_1_buying=_CARGO_1,
                    station_1_system="HIP 17597",
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    start_phase=Phase.UNDOCK_STATION_1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "error")
        actions = [call["action"] for call in controls.calls]
        self.assertIn("SetSpeed100", actions)
        self.assertIn("HyperSuperCombination", actions)

    def test_skips_sell_when_cargo_empty(self) -> None:
        controls = FakeShipControls()
        market_calls: list[tuple[str, str]] = []
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                def fake_sell(controls, watcher, **kwargs):
                    market_calls.append(("sell", kwargs["target"]))
                    _write_cargo(journal_dir, [])
                    return RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )

                market_sell_mock.side_effect = fake_sell

                def fake_buy(controls, watcher, **kwargs):
                    market_calls.append(("buy", kwargs["target"]))
                    _write_cargo(
                        journal_dir,
                        [{"Name": kwargs["target"].lower(), "Count": 64, "Stolen": 0}],
                    )
                    return RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )

                market_buy_mock.side_effect = fake_buy
                result = haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(
            market_calls,
            [
                ("buy", _CARGO_1),
                ("sell", _CARGO_1),
                ("buy", _CARGO_2),
            ],
        )

    def test_post_sell_settle_sleeps_between_sell_and_buy(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])
        sleep_calls: list[float] = []

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(
                journal_dir,
                [{"Name": "bertrandite", "Count": 64, "Stolen": 0}],
            )
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                def fake_sell(controls, watcher, **kwargs):
                    _write_cargo(journal_dir, [])
                    return RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )

                def fake_buy(controls, watcher, **kwargs):
                    _write_cargo(journal_dir, [{"Name": kwargs["target"], "Count": 64, "Stolen": 0}])
                    return RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )

                market_sell_mock.side_effect = fake_sell
                market_buy_mock.side_effect = fake_buy
                haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    post_sell_settle_s=2.5,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda s: sleep_calls.append(s),
                )

        self.assertEqual(sleep_calls.count(2.5), 2)

    def test_post_sell_settle_skipped_when_cargo_empty(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": _STATION_1}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_2}],
            [{"event": "Docked", "StationName": _STATION_2}],
            [],
            [{"event": "Undocked", "StationName": _STATION_2}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": _STATION_1}],
            [{"event": "Docked", "StationName": _STATION_1}],
        ])
        sleep_calls: list[float] = []

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            _write_market(
                journal_dir,
                _STATION_1,
                [
                    {"Category": "Metals", "Name": "aluminium", "Name_Localised": _CARGO_1, "DemandBracket": 1, "Stock": 1000},
                    {"Category": "Minerals", "Name": "bertrandite", "Name_Localised": _CARGO_2, "DemandBracket": 1, "Stock": 1000},
                ],
            )
            _write_cargo(journal_dir, [])
            with patch("edap.routines.haul_two_way.market_sell") as market_sell_mock, patch(
                "edap.routines.haul_two_way.market_buy"
            ) as market_buy_mock:
                market_sell_mock.side_effect = lambda controls, watcher, **kwargs: RoutineResult(
                    action="market_sell",
                    dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                )

                def fake_buy(controls, watcher, **kwargs):
                    _write_cargo(
                        journal_dir,
                        [{"Name": kwargs["target"].lower(), "Count": 64, "Stolen": 0}],
                    )
                    return RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )

                market_buy_mock.side_effect = fake_buy
                haul_loop_two_way(
                    controls,
                    watcher,
                    journal_dir=journal_dir,
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_1_system=_SYSTEM_1,
                    station_2=_STATION_2,
                    station_2_buying=_CARGO_2,
                    station_2_system=_SYSTEM_2,
                    iterations=1,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    boost_settle_s=0.0,
                    post_sell_settle_s=2.5,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    time_fn=_ticking_clock(),
                    sleeper=lambda s: sleep_calls.append(s),
                )

        # Station 1 sell was skipped (empty cargo), so only the station 2 sell triggers the settle.
        self.assertEqual(sleep_calls.count(2.5), 1)

    def test_rejects_duplicate_stations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "station_1 and station_2 must differ"):
                haul_loop_two_way(
                    FakeShipControls(),
                    FakeWatcher([]),
                    journal_dir=Path(tmp),
                    station_1=_STATION_1,
                    station_1_buying=_CARGO_1,
                    station_2=_STATION_1,
                    station_2_buying=_CARGO_2,
                )


if __name__ == "__main__":
    unittest.main()
