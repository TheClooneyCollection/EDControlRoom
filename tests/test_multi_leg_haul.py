from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edcr.actions import ActionDispatchResult
from edcr.config import default_haul_routine_defaults
from edcr.multi_leg_haul import (
    EXTERNAL_SCHEMA,
    CargoTransfer,
    MultiLegHaulDefinition,
    RouteEndpoint,
    RouteLeg,
    build_route_stops,
    multi_leg_haul_definition_from_data,
    multi_leg_haul_definition_to_external_json,
)
from edcr.routines import RoutineResult
from edcr.routines.callbacks import noop_announce, noop_progress
from edcr.routines.haul_support import (
    HaulMarketSettings,
    HaulRuntime,
    HaulTravelSettings,
    build_haul_runtime,
    build_haul_timing,
)
from edcr.routines.haul_multi_leg import (
    Phase,
    _wait_for_arrival_or_approach_event,
    multi_leg_haul as _multi_leg_haul,
)
from edcr.tts import AnnouncementId
from tests.fakes import FakeShipControls, FakeWatcher


_DEFAULTS = default_haul_routine_defaults()


def _write_navroute(journal_dir: Path, destination: str) -> None:
    (journal_dir / "NavRoute.json").write_text(
        f'{{"Route":[{{"StarSystem":"{destination}"}}]}}\n',
        encoding="utf-8",
    )


def multi_leg_haul(*args, **kwargs):
    controls, watcher = args
    definition = kwargs.pop("definition")
    journal_dir = kwargs.pop("journal_dir")
    if not (journal_dir / "Status.json").exists():
        (journal_dir / "Status.json").write_text('{"Flags": 0}', encoding="utf-8")
    runtime = build_haul_runtime(
        controls=controls,
        watcher=watcher,
        journal_dir=journal_dir,
        market_path=journal_dir / "Market.json",
        timing=build_haul_timing(
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
            nav_delay_s=kwargs.pop("market_nav_delay_s", 0.0),
            buy_top_up_max_attempts=kwargs.pop("buy_top_up_max_attempts", _DEFAULTS.market_buy_top_up_max_attempts),
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
    stop_requested_fn = kwargs.pop("stop_requested_fn", None)
    if kwargs:
        raise AssertionError(f"Unhandled multi-leg haul test kwargs: {sorted(kwargs)}")
    return _multi_leg_haul(runtime, definition=definition, stop_requested_fn=stop_requested_fn)


def _ticking_clock(step: float = 0.01):
    t = [0.0]

    def fn() -> float:
        value = t[0]
        t[0] += step
        return value

    return fn


def _definition() -> MultiLegHaulDefinition:
    return MultiLegHaulDefinition(
        route_name="Pawelczyk Dock -> Pawelczyk Dock (2 legs)",
        source_provider="spansh",
        source_job="job-123",
        source_url="fixture",
        source_parameters={"max_cargo": "460"},
        legs=(
            RouteLeg(
                index=1,
                source=RouteEndpoint(system="HIP 58412", station="Pawelczyk Dock"),
                destination=RouteEndpoint(system="HIP 68076", station="Bolivar Horizons"),
                cargo=(CargoTransfer(commodity="Water Purifiers", amount=460, buy_price=403, sell_price=2086),),
                jump_distance_ly=39.06,
                total_profit=774180,
                cumulative_profit=774180,
            ),
            RouteLeg(
                index=2,
                source=RouteEndpoint(system="HIP 68076", station="Bolivar Horizons"),
                destination=RouteEndpoint(system="HIP 58412", station="Pawelczyk Dock"),
                cargo=(CargoTransfer(commodity="Aluminium", amount=460, buy_price=2674, sell_price=20320),),
                jump_distance_ly=30.06,
                total_profit=8117160,
                cumulative_profit=8891340,
            ),
        ),
    )


class MultiLegHaulDefinitionTests(unittest.TestCase):
    def test_spansh_payload_normalizes_to_external_schema(self) -> None:
        payload = {
            "job": "job-123",
            "parameters": {"max_cargo": "460"},
            "result": [
                {
                    "commodities": [
                        {
                            "amount": 460,
                            "destination_commodity": {"sell_price": 2086},
                            "name": "Water Purifiers",
                            "profit": 1683,
                            "source_commodity": {"buy_price": 403},
                            "total_profit": 774180,
                        }
                    ],
                    "cumulative_profit": 774180,
                    "destination": {"station": "Bolivar Horizons", "system": "HIP 68076"},
                    "distance": 39.0604999487974,
                    "source": {"station": "Pawelczyk Dock", "system": "HIP 58412"},
                    "total_profit": 774180,
                }
            ],
            "state": "completed",
            "status": "ok",
        }

        definition = multi_leg_haul_definition_from_data(payload, source_label="fixture")
        external = multi_leg_haul_definition_to_external_json(definition)

        self.assertEqual(external["schema"], EXTERNAL_SCHEMA)
        self.assertEqual(external["route_name"], "Pawelczyk Dock -> Bolivar Horizons (1 legs)")
        self.assertEqual(external["legs"][0]["cargo"][0]["commodity"], "Water Purifiers")
        self.assertEqual(external["legs"][0]["cargo"][0]["amount"], 460)

    def test_external_round_trip_preserves_leg_data(self) -> None:
        definition = _definition()
        payload = multi_leg_haul_definition_to_external_json(definition)

        loaded = multi_leg_haul_definition_from_data(payload, source_label="fixture")
        stops = build_route_stops(loaded)

        self.assertEqual(loaded.route_name, definition.route_name)
        self.assertEqual(len(loaded.legs), 2)
        self.assertEqual(stops[1].inbound[0].commodity, "Water Purifiers")
        self.assertEqual(stops[1].outbound[0].commodity, "Aluminium")

    def test_external_round_trip_preserves_manual_landing_endpoints(self) -> None:
        definition = MultiLegHaulDefinition(
            route_name="Surface run",
            legs=(
                RouteLeg(
                    index=1,
                    source=RouteEndpoint(system="Sol", station="Galileo", manual_landing=False),
                    destination=RouteEndpoint(system="Achenar", station="Mahatma Settlement", manual_landing=True),
                    cargo=(CargoTransfer(commodity="Tea", amount=10),),
                ),
            ),
        )

        payload = multi_leg_haul_definition_to_external_json(definition)
        loaded = multi_leg_haul_definition_from_data(payload, source_label="fixture")
        # Routes exported before the rename name the flag `on_land`.
        legacy = json.loads(json.dumps(payload).replace('"manual_landing"', '"on_land"'))

        self.assertTrue(loaded.legs[0].destination.manual_landing)
        self.assertTrue(multi_leg_haul_definition_from_data(legacy, source_label="fixture").legs[0].destination.manual_landing)


class MultiLegHaulRoutineTests(unittest.TestCase):
    def test_numeric_buy_tops_up_only_the_remainder_with_configured_retry_limit(self) -> None:
        for counts, expected_amounts, warning, limit in (
            ([460], [460], False, 3),
            ([400, 60], [460, 60], False, 3),
            ([400, 30, 10, 5], [460, 60, 30, 20], True, 3),
            ([400], [460], True, 0),
            ([400, 30], [460, 60], True, 1),
            ([None], [460], False, 3),
            ([400, "error"], [460, 60], False, 3),
        ):
            with self.subTest(counts=counts), tempfile.TemporaryDirectory() as tmp:
                amounts = []
                progress = []
                announcements = []
                pending = iter(counts)
                ok = RoutineResult(action="test", dispatch=ActionDispatchResult(action="test", status="ok"))

                def buy(controls, watcher, *, target, amount, **kwargs):
                    if target == "Water Purifiers":
                        amounts.append(int(amount))
                        count = next(pending)
                    else:
                        count = int(amount)
                    return RoutineResult(
                        action="MarketBuy", dispatch=ActionDispatchResult(action="MarketBuy", status="error" if count == "error" else "ok"),
                        trigger_event={"Count": count}, details={"expected_count": int(amount)},
                    )

                with (
                    patch("edcr.routines.haul_multi_leg.market_buy", buy),
                    patch("edcr.routines.haul_multi_leg._read_cargo_json", lambda _: []),
                    patch("edcr.routines.haul_multi_leg.transit_to_station", return_value=ok),
                    patch("edcr.routines.haul_multi_leg.undock_and_route_to_system", return_value=ok),
                ):
                    result = multi_leg_haul(
                        FakeShipControls(), FakeWatcher([]), definition=_definition(), journal_dir=Path(tmp),
                        announce_fn=lambda message_id, **values: announcements.append((message_id, values)), progress_fn=progress.append, buy_top_up_max_attempts=limit,
                    )
                self.assertEqual(result.dispatch.status, "error" if "error" in counts else "ok")
                self.assertEqual(amounts, expected_amounts)
                self.assertEqual(any("Warning:" in line for line in progress), warning)


                self.assertEqual([item for item in announcements if item[0] == AnnouncementId.HAUL_BUY_STILL_SHORT],
                                 [(AnnouncementId.HAUL_BUY_STILL_SHORT, {"station_name": "Pawelczyk Dock"})] if warning else [])

    def test_numeric_top_up_skips_when_balance_cannot_buy_one_unit(self) -> None:
        for status_text, expected_amounts in (('{"Balance": 9}', [460]), ('{', [460, 60]), ('{}', [460, 60])):
            with self.subTest(status=status_text), tempfile.TemporaryDirectory() as tmp:
                journal_dir = Path(tmp)
                (journal_dir / "Market.json").write_text('{"Items": [{"Name": "Water Purifiers", "BuyPrice": 10}]}', encoding="utf-8")
                amounts = []
                progress = []
                announcements = []
                ok = RoutineResult(action="test", dispatch=ActionDispatchResult(action="test", status="ok"))

                def buy(controls, watcher, *, target, amount, **kwargs):
                    (journal_dir / "Status.json").write_text(status_text, encoding="utf-8")
                    if target == "Water Purifiers":
                        amounts.append(int(amount))
                        count = 400 if len(amounts) == 1 else int(amount)
                    else:
                        count = int(amount)
                    return RoutineResult(action="MarketBuy", dispatch=ActionDispatchResult(action="MarketBuy", status="ok"),
                                         trigger_event={"Count": count}, details={"expected_count": int(amount)})

                with (
                    patch("edcr.routines.haul_multi_leg.market_buy", buy),
                    patch("edcr.routines.haul_multi_leg._read_cargo_json", lambda _: []),
                    patch("edcr.routines.haul_multi_leg.transit_to_station", return_value=ok),
                    patch("edcr.routines.haul_multi_leg.undock_and_route_to_system", return_value=ok),
                ):
                    result = multi_leg_haul(FakeShipControls(), FakeWatcher([]), definition=_definition(),
                                           journal_dir=journal_dir, announce_fn=lambda message_id, **values: announcements.append((message_id, values)), progress_fn=progress.append)
                self.assertEqual(result.dispatch.status, "ok")
                self.assertEqual(amounts, expected_amounts)
                self.assertEqual(any("cannot afford top-up" in line for line in progress), len(expected_amounts) == 1)

                self.assertEqual([item for item in announcements if item[0] == AnnouncementId.HAUL_TOP_UP_UNAFFORDABLE],
                                 [(AnnouncementId.HAUL_TOP_UP_UNAFFORDABLE, {"commodity_name": "Water Purifiers", "station_name": "Pawelczyk Dock"})] if len(expected_amounts) == 1 else [])

    def test_transit_announces_next_station_before_opening_nav_panel(self) -> None:
        controls = FakeShipControls()
        sleep_calls: list[float] = []
        announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": "HIP 68076"}],
            [{"event": "SupercruiseExit", "BodyType": "Station"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": "Bolivar Horizons"}],
            [{"event": "Docked", "StationName": "Bolivar Horizons"}],
        ])
        definition = _definition()

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"FSDJump","StarSystem":"HIP 68076"}\n',
                encoding="utf-8",
            )
            (journal_dir / "Market.json").write_text(
                '{"StationName":"Pawelczyk Dock","StarSystem":"HIP 58412","Items":[]}\n',
                encoding="utf-8",
            )
            (journal_dir / "Cargo.json").write_text(
                '{"Inventory":[{"Name":"water purifiers","Name_Localised":"Water Purifiers","Count":460,"Stolen":0}]}\n',
                encoding="utf-8",
            )
            with patch("edcr.routines.haul_multi_leg.market_sell") as market_sell_mock:
                market_sell_mock.return_value = RoutineResult(
                    action="market_sell",
                    dispatch=ActionDispatchResult(action="market_sell", status="error", reason="stop after transit"),
                )
                result = multi_leg_haul(
                    controls,
                    watcher,
                    definition=definition,
                    journal_dir=journal_dir,
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
        self.assertEqual([call["action"] for call in controls.calls].count("FocusLeftPanel"), 2)
        self.assertIn(3.0, sleep_calls)
        self.assertIn(
            (AnnouncementId.ARRIVAL_NEXT_STATION, {"station_name": "Bolivar Horizons"}),
            announcements,
        )

    def test_transit_aborts_docking_after_interdiction_drop(self) -> None:
        controls = FakeShipControls()
        messages: list[str] = []
        announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": "HIP 68076"}],
            [
                {
                    "event": "Interdicted",
                    "Submitted": True,
                    "Interdictor": "Jeremy Linter",
                    "IsPlayer": False,
                },
                {"event": "SupercruiseExit", "BodyType": "Planet", "StarSystem": "HIP 68076"},
            ],
        ])
        definition = _definition()

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"FSDJump","StarSystem":"HIP 68076"}\n',
                encoding="utf-8",
            )
            (journal_dir / "Market.json").write_text(
                '{"StationName":"Pawelczyk Dock","StarSystem":"HIP 58412","Items":[]}\n',
                encoding="utf-8",
            )
            (journal_dir / "Cargo.json").write_text(
                '{"Inventory":[{"Name":"water purifiers","Name_Localised":"Water Purifiers","Count":460,"Stolen":0}]}\n',
                encoding="utf-8",
            )
            result = multi_leg_haul(
                controls,
                watcher,
                definition=definition,
                journal_dir=journal_dir,
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
        self.assertTrue(any("Interdiction detected during multi-leg haul transit" in message for message in messages))
        self.assertIn((AnnouncementId.HAUL_ABORTED, {}), announcements)

    def test_departure_warns_and_continues_when_galaxy_map_route_is_unconfirmed(self) -> None:
        controls = FakeShipControls()
        sleep_calls: list[float] = []
        messages: list[str] = []
        announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": "Pawelczyk Dock"}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "FSDJump", "StarSystem": "HIP 68076"}],
        ])
        definition = _definition()

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Market.json").write_text(
                '{"StationName":"Pawelczyk Dock","StarSystem":"HIP 58412","Items":[]}\n',
                encoding="utf-8",
            )
            (journal_dir / "Cargo.json").write_text(
                '{"Inventory":[{"Name":"water purifiers","Name_Localised":"Water Purifiers","Count":460,"Stolen":0}]}\n',
                encoding="utf-8",
            )
            route_failure = RoutineResult(
                action="GalaxyMapOpen",
                dispatch=ActionDispatchResult(
                    action="GalaxyMapOpen",
                    status="error",
                    reason="route mismatch: expected 'HIP 68076', got 'HIP 58412'",
                ),
            )
            with (
                patch("edcr.routines.transit.set_gal_map_destination", side_effect=[route_failure, route_failure]) as route_mock,
                patch("edcr.routines.transit.dock") as dock_mock,
            ):
                dock_mock.return_value = RoutineResult(
                    action="dock",
                    dispatch=ActionDispatchResult(action="dock", status="error", reason="stop after manual jump"),
                )
                result = multi_leg_haul(
                    controls,
                    watcher,
                    definition=definition,
                    journal_dir=journal_dir,
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
                    progress_fn=messages.append,
                    announce_fn=lambda message_id, **values: announcements.append((message_id, values)),
                )

        self.assertEqual(result.dispatch.reason, "stop after manual jump")
        self.assertEqual(route_mock.call_count, 2)
        dock_mock.assert_called_once()
        self.assertTrue(any("route to HIP 68076 is unconfirmed" in message for message in messages))
        self.assertTrue(any("Skipping automatic FSD engage" in message for message in messages))
        self.assertIn((AnnouncementId.ROUTE_UNCONFIRMED, {"system_name": "HIP 68076"}), announcements)
        self.assertNotIn("HyperSuperCombination", [call["action"] for call in controls.calls])

    def test_arrival_wait_ignores_intermediate_jump_systems(self) -> None:
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": "HIP 58412"}],
            [{"event": "FSDJump", "StarSystem": "HIP 68076"}],
        ])

        arrival_observed, pending_events = _wait_for_arrival_or_approach_event(
            watcher,
            destination_system="HIP 68076",
            deadline=1.0,
            time_fn=_ticking_clock(),
        )

        self.assertTrue(arrival_observed)
        self.assertEqual(pending_events, [])

    def test_haul_keeps_waiting_at_manual_landing_station_instead_of_stopping(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [{"event": "FSDJump", "StarSystem": "HIP 68076"}],
            [{"event": "SupercruiseExit", "BodyType": "Planet", "StarSystem": "HIP 68076"}],
        ])
        definition = MultiLegHaulDefinition(
            route_name="Surface run",
            legs=(
                RouteLeg(
                    index=1,
                    source=RouteEndpoint(system="HIP 58412", station="Pawelczyk Dock"),
                    destination=RouteEndpoint(system="HIP 68076", station="Mahatma Settlement", manual_landing=True),
                    cargo=(CargoTransfer(commodity="Water Purifiers", amount=460),),
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"FSDJump","StarSystem":"HIP 68076"}\n',
                encoding="utf-8",
            )
            (journal_dir / "Market.json").write_text(
                '{"StationName":"Pawelczyk Dock","StarSystem":"HIP 58412","Items":[]}\n',
                encoding="utf-8",
            )
            (journal_dir / "Cargo.json").write_text(
                '{"Inventory":[{"Name":"water purifiers","Name_Localised":"Water Purifiers","Count":460,"Stolen":0}]}\n',
                encoding="utf-8",
            )
            with patch("edcr.routines.transit.dock") as dock_mock:
                result = multi_leg_haul(
                    controls,
                    watcher,
                    definition=definition,
                    journal_dir=journal_dir,
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

        self.assertEqual(result.action, "Docked")
        self.assertEqual(result.dispatch.reason, "docked event was not observed before timeout")
        dock_mock.assert_not_called()

    def test_route_can_resume_midway_from_destination_station(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([
            [],
            [{"event": "Undocked", "StationName": "Bolivar Horizons"}],
            [{"event": "Music", "MusicTrack": "NoTrack"}],
            [{"event": "SupercruiseExit", "BodyType": "Station", "StarSystem": "HIP 58412"}],
            [],
            [{"event": "DockingGranted", "LandingPad": 1, "StationName": "Pawelczyk Dock"}],
            [{"event": "Docked", "StationName": "Pawelczyk Dock"}],
        ])
        definition = _definition()
        market_calls: list[tuple[str, str, str]] = []

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"Docked","StationName":"Bolivar Horizons","StarSystem":"HIP 68076"}\n',
                encoding="utf-8",
            )
            (journal_dir / "Market.json").write_text(
                '{"StationName":"Bolivar Horizons","StarSystem":"HIP 68076","Items":[]}\n',
                encoding="utf-8",
            )
            (journal_dir / "Cargo.json").write_text(
                '{"Inventory":[{"Name":"water purifiers","Name_Localised":"Water Purifiers","Count":460,"Stolen":0}]}\n',
                encoding="utf-8",
            )
            _write_navroute(journal_dir, "HIP 58412")
            with patch("edcr.routines.haul_multi_leg.market_sell") as market_sell_mock, patch(
                "edcr.routines.haul_multi_leg.market_buy"
            ) as market_buy_mock:
                def fake_sell(controls, watcher, **kwargs):
                    market_calls.append(("sell", kwargs["target"], kwargs["amount"]))
                    target = kwargs["target"]
                    if target == "Water Purifiers":
                        (journal_dir / "Cargo.json").write_text('{"Inventory":[]}\n', encoding="utf-8")
                    elif target == "Aluminium":
                        (journal_dir / "Cargo.json").write_text('{"Inventory":[]}\n', encoding="utf-8")
                    return RoutineResult(
                        action="market_sell",
                        dispatch=ActionDispatchResult(action="market_sell", status="ok"),
                    )

                def fake_buy(controls, watcher, **kwargs):
                    market_calls.append(("buy", kwargs["target"], kwargs["amount"]))
                    if kwargs["target"] == "Aluminium":
                        (journal_dir / "Cargo.json").write_text(
                            '{"Inventory":[{"Name":"aluminium","Name_Localised":"Aluminium","Count":460,"Stolen":0}]}\n',
                            encoding="utf-8",
                        )
                    return RoutineResult(
                        action="market_buy",
                        dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                    )

                market_sell_mock.side_effect = fake_sell
                market_buy_mock.side_effect = fake_buy
                result = multi_leg_haul(
                    controls,
                    watcher,
                    definition=definition,
                    journal_dir=journal_dir,
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
                ("sell", "Water Purifiers", "460"),
                ("buy", "Aluminium", "460"),
                ("sell", "Aluminium", "460"),
            ],
        )
        self.assertIn("HyperSuperCombination", [call["action"] for call in controls.calls])

    def test_stop_requested_halts_before_departure(self) -> None:
        controls = FakeShipControls()
        watcher = FakeWatcher([])
        definition = _definition()

        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"Docked","StationName":"Pawelczyk Dock","StarSystem":"HIP 58412"}\n',
                encoding="utf-8",
            )
            (journal_dir / "Market.json").write_text(
                '{"StationName":"Pawelczyk Dock","StarSystem":"HIP 58412","Items":[]}\n',
                encoding="utf-8",
            )
            (journal_dir / "Cargo.json").write_text(
                '{"Inventory":[]}\n',
                encoding="utf-8",
            )
            with patch("edcr.routines.haul_multi_leg.market_buy") as market_buy_mock:
                market_buy_mock.return_value = RoutineResult(
                    action="market_buy",
                    dispatch=ActionDispatchResult(action="market_buy", status="ok"),
                )
                result = multi_leg_haul(
                    controls,
                    watcher,
                    definition=definition,
                    journal_dir=journal_dir,
                    step_delay_s=0.0,
                    settle_s=0.0,
                    dock_timeout_s=30.0,
                    request_timeout_s=10.0,
                    undock_timeout_s=10.0,
                    trade_timeout_s=10.0,
                    stop_requested_fn=lambda: True,
                    time_fn=_ticking_clock(),
                    sleeper=lambda _: None,
                )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual([call["action"] for call in controls.calls], [])


if __name__ == "__main__":
    unittest.main()
