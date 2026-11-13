from __future__ import annotations

import unittest
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated; install `httpx2` instead\.",
)

from edcr.control_room.models import ShipState
from edcr.control_room.server.app import build_observer_server_app
from edcr.control_room.server.auth import SharedAccessTokenAuth
from edcr.control_room.server.broker import InMemoryObserverSessionBroker
from edcr.eddn.listener import apply_payload
from edcr.eddn.messages import CarrierSighting
from edcr.eddn.route_query import parse_route_query, run_route_query
from edcr.eddn.routes import RouteFilters, TimeModel, find_routes, load_route_markets
from edcr.eddn.store import EddnStore
from edcr.trip_time_fit import TripTimeModels
from tests.shared_loop import TestClient
from tests.test_eddn import commodity_envelope, docked_envelope, frame, memory_store, signal_envelope

NOW = 1_794_319_200.0  # 2026-11-10T14:00:00Z, the fixture timestamp


def price(name: str, *, buy: int = 0, sell: int = 0, stock: int = 0, demand: int = 0) -> dict[str, object]:
    return {"name": name, "buyPrice": buy, "sellPrice": sell, "stock": stock, "demand": demand}


def add_station(
    store: EddnStore, market_id: int, station: str, system: str, x: float, station_type: str,
    pads: dict[str, int], commodities: list[dict[str, object]], dist_ls: float = 500.0, access: str = "",
) -> None:
    apply_payload(store, frame(docked_envelope(
        MarketID=market_id, StationName=station, StationType=station_type, StarSystem=system,
        SystemAddress=1000 + int(x), StarPos=[x, 0.0, 0.0], DistFromStarLS=dist_ls, LandingPads=pads,
    )))
    envelope = commodity_envelope(market_id=market_id, station=station, commodities=commodities)
    envelope["message"]["systemName"] = system  # type: ignore[index]
    if access:
        envelope["message"]["carrierDockingAccess"] = access  # type: ignore[index]
    apply_payload(store, frame(envelope))


LARGE = {"Small": 4, "Medium": 4, "Large": 2}


def galaxy() -> EddnStore:
    store = memory_store()
    add_station(store, 1, "Galileo", "Sol", 0.0, "Ocellus", LARGE,
                [price("gold", buy=9000, stock=5000), price("silver", sell=5200, demand=9000)])
    add_station(store, 2, "Alpha Port", "Alpha", 10.0, "Coriolis", LARGE,
                [price("gold", sell=12000, demand=8000), price("silver", buy=4000, stock=500)])
    add_station(store, 3, "Alpha Outpost", "Alpha", 10.0, "Outpost", {"Small": 2, "Medium": 1, "Large": 0},
                [price("gold", sell=20000, demand=8000)])
    add_station(store, 4, "K7Q-BQL", "Sol", 0.0, "FleetCarrier", LARGE, [price("gold", buy=100, stock=9000)])
    add_station(store, 5, "Far Hub", "Far", 100.0, "Orbis", LARGE, [price("gold", sell=50000, demand=8000)])
    store.commit()
    return store


def routes(store: EddnStore, **options: object):
    markets = load_route_markets(store._db, RouteFilters(), now=NOW)
    defaults: dict[str, object] = dict(capacity=1137, max_route_ly=68.8, laden_jump_range_ly=17.2, time_model=TimeModel())
    return find_routes(markets, **{**defaults, **options})


class EddnRouteFinderTests(unittest.TestCase):
    def test_round_trip_caps_hold_by_stock_and_skips_carriers_small_pads_and_far_stations(self) -> None:
        store = galaxy()
        self.addCleanup(store.close)
        [route] = routes(store)

        self.assertEqual((route.station_1.station, route.station_2.station, route.jumps), ("Galileo", "Alpha Port", 1))
        self.assertEqual((route.outbound.commodity, route.outbound.tons, route.outbound.profit), ("gold", 1137, 3_411_000))
        self.assertEqual((route.inbound.commodity, route.inbound.tons, route.inbound.profit), ("silver", 500, 600_000))
        self.assertEqual(route.profit_per_trip, 4_011_000)
        self.assertEqual(route.profit_per_hour, round(4_011_000 * 3600 / route.trip_s))

    def test_more_jumps_rank_by_profit_per_hour_and_near_view_needs_station_1_close(self) -> None:
        store = galaxy()
        self.addCleanup(store.close)
        ranked = routes(store, max_route_ly=200.0)

        self.assertEqual([(r.station_2.station, r.jumps) for r in ranked[:2]], [("Far Hub", 6), ("Alpha Port", 1)])
        self.assertGreater(ranked[0].trip_s, ranked[1].trip_s)
        near_far = routes(store, max_route_ly=200.0, origin=(100.0, 0.0, 0.0), origin_radius_ly=5.0)
        self.assertEqual([(r.station_1.station, r.station_2.station) for r in near_far], [("Galileo", "Far Hub")])

    def test_a_named_carrier_stays_out_by_its_station_type(self) -> None:
        store = galaxy()
        self.addCleanup(store.close)
        # Commodity messages carry no station type, and "VAON" is not a callsign.
        add_station(store, 6, "VAON", "Alpha", 10.0, "FleetCarrier", LARGE, [price("gold", sell=90000, demand=8000)])
        store.commit()

        self.assertNotIn("VAON", [route.station_2.station for route in routes(store)])

    def test_carriers_open_to_all_or_of_unknown_access_by_default(self) -> None:
        store = galaxy()
        self.addCleanup(store.close)
        for market_id, callsign, access in ((6, "AAA-111", "all"), (7, "BBB-222", "squadronfriends"), (8, "CCC-333", "")):
            add_station(store, market_id, callsign, "Alpha", 10.0, "FleetCarrier", LARGE,
                        [price("gold", sell=12000 + market_id, demand=8000)], access=access)
        apply_payload(store, frame(signal_envelope("GRAND ARTS THEATRE AAA-111")))
        store.commit()

        def carriers(**filters: object) -> dict[str, tuple[str, str]]:
            markets = load_route_markets(store._db, RouteFilters(include_carriers=True, **filters), now=NOW)
            return {m.station: (m.carrier_name, m.carrier_access) for m in markets if m.is_carrier}

        self.assertEqual(carriers(), {"K7Q-BQL": ("", ""), "AAA-111": ("GRAND ARTS THEATRE", "all"), "CCC-333": ("", "")})
        self.assertEqual(carriers(carriers_open_only=False)["BBB-222"], ("", "squadronfriends"))
        self.assertEqual([parse_route_query(params, search_defaults={}, current_system="Sol", cargo_capacity=1)
                          .filters.carriers_open_only for params in ({}, {"carrier_access": "all"}, {"carrier_access": "any"})],
                         [True, True, False])
        with self.assertRaisesRegex(ValueError, "carrier_access"):
            parse_route_query({"carrier_access": "friends"}, search_defaults={}, current_system="Sol", cargo_capacity=1)

    def test_carriers_seen_elsewhere_or_missing_from_our_journal_batch_are_gone(self) -> None:
        store = galaxy()
        self.addCleanup(store.close)
        for market_id, callsign in ((6, "AAA-111"), (7, "BBB-222"), (8, "CCC-333")):
            add_station(store, market_id, callsign, "Alpha", 10.0, "FleetCarrier", LARGE,
                        [price("gold", sell=12000 + market_id, demand=8000)])
        alpha = 1010
        store.save([
            # Our journal listed Alpha's carriers after their markets were read: CCC-333 was not there.
            CarrierSighting(callsign="AAA-111", system_address=alpha, timestamp=NOW + 1800, complete=True),
            CarrierSighting(callsign="BBB-222", system_address=alpha, timestamp=NOW + 1800, complete=True),
            # An EDDN upload saw K7Q-BQL, read in Sol, in Alpha later.
            CarrierSighting(callsign="K7Q-BQL", system_address=alpha, timestamp=NOW + 600, complete=False),
        ])

        def carriers() -> set[str]:
            markets = load_route_markets(store._db, RouteFilters(include_carriers=True), now=NOW)
            return {m.station for m in markets if m.is_carrier}

        self.assertEqual(carriers(), {"AAA-111", "BBB-222"})
        # A newer market for CCC-333 in Alpha brings it back; a later batch with only AAA-111 hides the others.
        newer = commodity_envelope(market_id=8, station="CCC-333", timestamp="2026-11-10T15:00:00Z",
                                   commodities=[price("gold", sell=12008, demand=8000)])
        newer["message"]["systemName"] = "Alpha"  # type: ignore[index]
        apply_payload(store, frame(newer))
        self.assertEqual(carriers(), {"AAA-111", "BBB-222", "CCC-333"})
        store.save([CarrierSighting(callsign="AAA-111", system_address=alpha, timestamp=NOW + 7200, complete=True)])
        self.assertEqual(carriers(), {"AAA-111"})

    def test_surface_stations_need_opting_in_and_add_landing_time(self) -> None:
        store = galaxy()
        self.addCleanup(store.close)
        add_station(store, 6, "Crater Dock", "Alpha", 10.0, "CraterOutpost", LARGE,
                    [price("gold", sell=12000, demand=8000), price("silver", buy=4000, stock=500)])
        store.commit()
        self.assertNotIn("Crater Dock", [route.station_2.station for route in routes(store)])

        markets = load_route_markets(store._db, RouteFilters(include_surface=True), now=NOW)
        found = find_routes(markets, capacity=1137, max_route_ly=68.8, laden_jump_range_ly=17.2, time_model=TimeModel())
        trips = {route.station_2.station: route.trip_s for route in found}
        self.assertEqual(trips["Crater Dock"] - trips["Alpha Port"], TimeModel().surface_extra_s)

    def test_a_listed_sell_price_counts_whatever_the_demand(self) -> None:
        store = galaxy()
        self.addCleanup(store.close)
        # A producer still buys its own export: EDDN shows demand 1 (Sitterly Enterprise beryllium).
        add_station(store, 6, "Producer", "Alpha", 10.0, "Orbis", LARGE, [price("gold", sell=30000, demand=1)])
        store.commit()

        [best, *_] = routes(store)

        self.assertEqual((best.station_2.station, best.outbound.commodity, best.outbound.tons), ("Producer", "gold", 1137))

    def test_query_defaults_come_from_haul_search_and_ship(self) -> None:
        query = parse_route_query(
            {"jumps": "2"},
            search_defaults={"max_route_distance_ly": "17.2", "min_supply": "5000", "min_demand": "5000", "max_station_distance_ls": "any",
                             "min_landing_pad": "large", "use_surface_stations": "no"},
            current_system="Sol",
            cargo_capacity=1137,
        )

        self.assertEqual((query.view, query.system, query.max_route_ly, query.capacity), ("near", "Sol", 34.4, 1137))
        self.assertEqual((query.filters.min_supply, query.filters.min_pad, query.filters.max_station_distance_ls),
                         (5000, "L", None))
        with self.assertRaisesRegex(ValueError, "view"):
            parse_route_query({"view": "x"}, search_defaults={}, current_system="", cargo_capacity=0)

    def test_unticked_filters_send_any_to_turn_off_the_haul_search_value(self) -> None:
        saved = {"min_supply": "5000", "max_station_distance_ls": "1000", "max_price_age_hours": "8"}
        ticked = parse_route_query({}, search_defaults=saved, current_system="Sol", cargo_capacity=1).filters
        unticked = parse_route_query({"min_supply": "any", "max_station_distance_ls": "any", "max_age_hours": "any"},
                                     search_defaults=saved, current_system="Sol", cargo_capacity=1).filters
        self.assertEqual((ticked.min_supply, ticked.max_station_distance_ls, ticked.max_age_s), (5000, 1000, 8 * 3600))
        self.assertEqual((unticked.min_supply, unticked.max_station_distance_ls), (0, None))
        self.assertGreater(unticked.max_age_s, 365 * 86400)

    def test_surface_stations_follow_the_page_then_the_haul_search_choice(self) -> None:
        def include_surface(params: dict[str, str], saved: str) -> bool:
            query = parse_route_query(params, search_defaults={"use_surface_stations": saved}, current_system="Sol", cargo_capacity=1)
            return query.filters.include_surface

        self.assertEqual([include_surface({}, saved) for saved in ("yes_with_odyssey", "yes_exclude_odyssey", "no", "")],
                         [True, True, False, False])
        self.assertEqual([include_surface({"surface": page}, "yes_with_odyssey") for page in ("no", "0")], [False, False])
        self.assertEqual([include_surface({"surface": page}, "no") for page in ("yes", "1")], [True, True])


class EddnRoutesApiTests(unittest.TestCase):
    def test_api_runs_near_search_from_the_database_file(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "eddn.sqlite3"
            store = EddnStore.open(path)
            source = galaxy()
            self.addCleanup(source.close)
            source._db.backup(store._db)
            store.close()

            payload = run_route_query(
                path,
                parse_route_query({}, search_defaults={}, current_system="Sol", cargo_capacity=1137),
                time_model=TimeModel(),
                display_names={"gold": "Gold"},
                now=NOW,
            )
            [route] = payload["routes"]
            self.assertEqual((route["outbound"]["name"], route["inbound"]["name"]), ("Gold", "silver"))
            self.assertEqual({key: route["station_1"][key] for key in ("is_carrier", "carrier_access", "carrier_name")},
                             {"is_carrier": False, "carrier_access": "", "carrier_name": ""})
            self.assertIsNone(route["trade_route"])
            named = run_route_query(path, parse_route_query({}, search_defaults={}, current_system="Sol", cargo_capacity=1137),
                                    time_model=TimeModel(), display_names={"gold": "Gold", "silver": "Silver"}, now=NOW)
            self.assertEqual(
                {key: named["routes"][0]["trade_route"][key] for key in
                 ("from_station", "to_station", "source_buy_commodity", "target_buy_commodity", "profit_per_trip")},
                {"from_station": "Galileo", "to_station": "Alpha Port", "source_buy_commodity": "Gold",
                 "target_buy_commodity": "Silver", "profit_per_trip": "4,011,000 Cr"},
            )
            self.assertFalse(named["routes"][0]["trade_route"]["to_manual_landing"])
            out, back = named["routes"][0]["outbound"], named["routes"][0]["inbound"]
            self.assertEqual(
                [named["routes"][0]["trade_route"][key] for key in
                 ("from_buy_price", "to_sell_price", "to_buy_price", "from_sell_price")],
                [f"{price:,} Cr" for price in (out["buy_price"], out["sell_price"], back["buy_price"], back["sell_price"])],
            )

            def global_view(system: str, time_model: TimeModel = TimeModel()) -> dict:
                return run_route_query(
                    path, parse_route_query({"view": "global"}, search_defaults={}, current_system=system,
                                            cargo_capacity=1137),
                    time_model=time_model, display_names={}, now=NOW,
                )

            from_alpha = global_view("alpha")
            self.assertEqual(from_alpha["distance_system"], "alpha")
            self.assertEqual(
                [(route["station_1"]["ly_from_system"], route["station_2"]["ly_from_system"])
                 for route in from_alpha["routes"]],
                [(10.0, 0.0)],
            )
            # An unknown current system still searches anywhere, just without distances.
            unknown_system = global_view("Nowhere")
            self.assertIsNone(unknown_system["distance_system"])
            self.assertIsNone(unknown_system["routes"][0]["station_1"]["ly_from_system"])

            app = build_observer_server_app(
                data_provider=lambda: type("Data", (), {"ship": ShipState(system="Nowhere", cargo_capacity=1137)})(),
                command_handler=None, broker=InMemoryObserverSessionBroker(),
                auth=SharedAccessTokenAuth("secret-token"), market_database_file=path,
                time_models=TripTimeModels(configured=TimeModel(docked_s=0.0), source="config", fit_days=14.0, fit_ship="current",
                                           connect=None, clock=lambda: NOW),
            )
            with patch("edcr.control_room.server.app.load_haul_search_config", return_value={}), TestClient(app) as client:
                self.assertEqual(client.get("/api/eddn-routes").status_code, 401)
                unknown = client.get("/api/eddn-routes?access_token=secret-token")
                self.assertEqual(unknown.status_code, 404)
                self.assertIn("Nowhere", unknown.json()["detail"])
                found = client.get("/api/eddn-routes?access_token=secret-token&view=global&max_age_hours=999999")
                self.assertEqual(found.json()["routes"][0]["station_2"]["station"], "Alpha Port")
                # The configured time model sets the trip time: no docked time is 180s shorter.
                configured = global_view("Nowhere", TimeModel(docked_s=0.0))["routes"][0]["trip_s"]
                self.assertEqual(found.json()["routes"][0]["trip_s"], configured)
                self.assertEqual(global_view("Nowhere")["routes"][0]["trip_s"] - configured, 180)
                self.assertEqual(found.json()["time_model"]["active"]["scope"], "config")
                self.assertEqual(client.get("/api/eddn-routes?access_token=secret-token&jumps=x").status_code, 400)


if __name__ == "__main__":
    unittest.main()
