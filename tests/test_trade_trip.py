from __future__ import annotations

import unittest

from edap.eddn.routes import TimeModel
from edap.haul_history import RouteSummary, RunTotals
from edap.eddn.messages import journal_event_updates, station_type_from_game
from edap.recent_markets import MarketSnapshot
from edap.trade_trip import (
    PartialFacts,
    StationFacts,
    estimate_trip,
    gather_facts,
    measured_route,
    store_lookup,
)
from tests.test_eddn import memory_store
from tests.test_eddn_routes import galaxy, routes


def facts(station: str, system: str, coords=(0.0, 0.0, 0.0), dist_ls=500.0, station_type="Coriolis") -> StationFacts:
    return StationFacts(station, system, coords, "eddn", dist_ls, "eddn", station_type, "eddn")


def snapshot(market_id: int, station: str, system: str, station_type: str = "Coriolis") -> MarketSnapshot:
    return MarketSnapshot(market_id, station, system, station_type, "2026-11-10T10:00:00Z", ())


def totals(count: int, profit: int, duration_s: float) -> RunTotals:
    return RunTotals(count, 0, profit, profit, duration_s)


def route(station_1: str, system_1: str | None, station_2: str, system_2: str | None, *, count: int, profit: int,
          duration_s: float) -> RouteSummary:
    done = totals(count, profit, duration_s)
    return RouteSummary(station_1, system_1, station_2, system_2, done, totals(0, 0, 0.0), done)


class TripEstimateTests(unittest.TestCase):
    def test_best_deal_trip_time_matches_the_routes_page_for_the_same_stations(self) -> None:
        store = galaxy()
        self.addCleanup(store.close)
        [found] = routes(store)
        lookup = [("eddn", store_lookup(store._db))]

        x = gather_facts(1, "Galileo", "Sol", lookup)
        y = gather_facts(2, "Alpha Port", "Alpha", lookup)
        estimate = estimate_trip(x, y, laden_jump_range_ly=17.2, time_model=TimeModel())

        self.assertEqual((x.coords, x.dist_ls, x.station_type, x.coords_source), ((0.0, 0.0, 0.0), 500.0, "Ocellus", "eddn"))
        self.assertEqual((estimate.jumps, estimate.distance_ly, estimate.missing), (found.jumps, 10.0, ()))
        self.assertEqual(estimate.trip_s, round(found.trip_s))

    def test_jumps_follow_the_laden_range_and_surface_stations_add_landing_time(self) -> None:
        x = facts("Port", "Sol")
        y = facts("Dock", "Far", coords=(40.0, 0.0, 0.0))
        model = TimeModel()

        orbital = estimate_trip(x, y, laden_jump_range_ly=17.2, time_model=model)
        surface = estimate_trip(x, facts("Dock", "Far", coords=(40.0, 0.0, 0.0), station_type="CraterOutpost"),
                                laden_jump_range_ly=40.0, time_model=model)

        self.assertEqual(orbital.jumps, 3)
        self.assertEqual(surface.jumps, 1)
        self.assertEqual(surface.trip_s, round(2 * model.leg_s(1, 500.0, surface=False) + model.surface_extra_s))

    def test_missing_inputs_leave_the_time_unknown_and_name_what_is_missing(self) -> None:
        x = facts("Port", "Sol", coords=None)
        y = facts("Dock", "Far", dist_ls=None, station_type=None)

        estimate = estimate_trip(x, y, laden_jump_range_ly=17.2, time_model=TimeModel())

        self.assertIsNone(estimate.trip_s)
        self.assertIsNone(estimate.jumps)
        self.assertEqual(estimate.missing, ("Sol coordinates", "Dock distance from star", "Dock station type"))

    def test_two_stations_in_one_system_need_no_coordinates(self) -> None:
        estimate = estimate_trip(facts("Port", "Sol", coords=None), facts("Dock", "sol", coords=None),
                                 laden_jump_range_ly=17.2, time_model=TimeModel())

        self.assertEqual((estimate.jumps, estimate.distance_ly, estimate.missing), (0, 0.0, ()))
        self.assertIsNotNone(estimate.trip_s)


class FactSourceTests(unittest.TestCase):
    def test_each_input_comes_from_the_first_source_that_knows_it_and_later_sources_wait(self) -> None:
        calls: list[str] = []

        def source(name: str, partial: PartialFacts):
            def lookup(market_id: int, station: str, system: str) -> PartialFacts:
                calls.append(name)
                return partial
            return name, lookup

        sources = [
            source("eddn", PartialFacts(coords=(1.0, 2.0, 3.0), station_type="")),
            source("journal", PartialFacts(coords=(9.0, 9.0, 9.0), dist_ls=120.0, station_type="Orbis")),
            source("ardent", PartialFacts(dist_ls=999.0, station_type="Outpost")),
        ]

        found = gather_facts(7, "Port", "Sol", sources)

        self.assertEqual((found.coords, found.coords_source), ((1.0, 2.0, 3.0), "eddn"))
        self.assertEqual((found.dist_ls, found.dist_ls_source), (120.0, "journal"))
        self.assertEqual((found.station_type, found.station_type_source), ("Orbis", "journal"))
        self.assertEqual(calls, ["eddn", "journal"])

    def test_the_store_knows_docked_distance_jump_coordinates_and_the_market_type_from_our_journal(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        events = [
            {"event": "FSDJump", "timestamp": "2026-11-10T10:00:00Z", "StarSystem": "Sol", "SystemAddress": 10,
             "StarPos": [0, 0, 0]},
            {"event": "Docked", "timestamp": "2026-11-10T10:05:00Z", "MarketID": 1, "StationName": "Galileo",
             "StarSystem": "Sol", "SystemAddress": 10, "StationType": "Ocellus", "DistFromStarLS": 505.3,
             "LandingPads": {"Small": 4, "Medium": 6, "Large": 2}},
            {"event": "Location", "timestamp": "2026-11-10T11:00:00Z", "StarSystem": "Alpha", "SystemAddress": 20,
             "StarPos": [10.0, 0.0, 0.0], "Docked": False},
            {"event": "Music", "timestamp": "2026-11-10T11:01:00Z"},
        ]
        store.save([update for event in events for update in journal_event_updates(event)])
        # Market.json names the type of a station we never docked at, and a market in an unknown system.
        store.save([station_type_from_game(snapshot(2, "Alpha Port", "Alpha")),
                    station_type_from_game(snapshot(3, "Far Port", "Unvisited"))])

        lookup = store_lookup(store._db)
        self.assertEqual(lookup(1, "Galileo", "SOL"), PartialFacts((0.0, 0.0, 0.0), 505.3, "Ocellus"))
        self.assertEqual(store._db.execute("SELECT max_pad FROM station WHERE market_id = 1").fetchone(), ("L",))
        # Never docked at Alpha Port: coordinates from the jump, type from Market.json, no distance.
        self.assertEqual(lookup(2, "Alpha Port", "Alpha"), PartialFacts((10.0, 0.0, 0.0), None, "Coriolis"))
        self.assertEqual(lookup(3, "Far Port", "Unvisited"), PartialFacts())

    def test_a_docked_location_records_the_station_and_newest_wins(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        docked = {"event": "Location", "timestamp": "2026-11-10T12:00:00Z", "StarSystem": "Sol", "SystemAddress": 10,
                  "StarPos": [0, 0, 0], "Docked": True, "MarketID": 1, "StationName": "Galileo",
                  "StationType": "Ocellus", "DistFromStarLS": 505.3}
        store.save(journal_event_updates(docked))
        # An older Market.json type does not overwrite the newer docked row.
        store.save([station_type_from_game(MarketSnapshot(1, "Galileo", "Sol", "Coriolis", "2026-11-10T09:00:00Z", ()))])

        self.assertEqual(store_lookup(store._db)(1, "Galileo", "Sol"), PartialFacts((0.0, 0.0, 0.0), 505.3, "Ocellus"))
        self.assertEqual(journal_event_updates({"event": "Docked", "MarketID": 1}), [])

class MeasuredRouteTests(unittest.TestCase):
    def test_completed_runs_either_way_and_any_case_add_up_to_a_measured_rate(self) -> None:
        summaries = [
            route("Galileo", "Sol", "Alpha Port", "Alpha", count=2, profit=8_000_000, duration_s=2400.0),
            route("alpha port", None, "GALILEO", "sol", count=1, profit=4_000_000, duration_s=1200.0),
            route("Galileo", "Other Sol", "Alpha Port", "Alpha", count=5, profit=1, duration_s=1.0),
            route("Galileo", "Sol", "Elsewhere", "Alpha", count=5, profit=1, duration_s=1.0),
        ]

        measured = measured_route(summaries, snapshot(1, "Galileo", "Sol"), snapshot(2, "Alpha Port", "Alpha"))

        self.assertEqual((measured.runs, measured.profit, measured.duration_s), (3, 12_000_000, 3600.0))
        self.assertEqual(measured.profit_per_hour, 12_000_000)

    def test_no_completed_timed_runs_means_no_measurement(self) -> None:
        x, y = snapshot(1, "Galileo", "Sol"), snapshot(2, "Alpha Port", "Alpha")
        self.assertIsNone(measured_route([], x, y))
        self.assertIsNone(measured_route([route("Galileo", "Sol", "Alpha Port", "Alpha", count=1, profit=5,
                                                duration_s=0.0)], x, y))


if __name__ == "__main__":
    unittest.main()
