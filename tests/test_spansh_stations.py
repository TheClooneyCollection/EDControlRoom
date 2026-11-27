"""Spansh requests and market offers through a fake JSON transport."""

from dataclasses import replace
import unittest

from edcr.cheapest_markets import CheapestQuery
from edcr.spansh_stations import SEARCH_URL, search_cheapest, spansh_search_body

NOW = 1795773600.0
QUERY = CheapestQuery("tritium", "Adach", 100.0, 720, "L", 168.0, False, True, 50)


def station(**changes):
    return {
        "market_id": 123, "name": "Rippert Legacy", "type": "Coriolis Starport",
        "system_name": "Adach", "distance": 12.5, "distance_to_arrival": 80.5,
        "has_large_pad": True, "market_updated_at": "2026-11-27 10:00:00+00",
        "market": [{"commodity": "Gold", "buy_price": 5, "supply": 10},
                   {"commodity": "Tritium", "buy_price": 44862, "supply": 1000}],
        **changes,
    }


class SpanshStationsTests(unittest.TestCase):
    def test_search_sends_price_sorted_filters_and_returns_total_and_offer(self):
        requests = []

        def post(url, body, timeout):
            requests.append((url, body, timeout))
            return {"results": [station()], "count": 3366}

        offers, count = search_cheapest(QUERY, "Tritium", post, now=NOW)
        self.assertEqual(count, 3366)
        offer, = offers
        self.assertEqual((offer.source, offer.market_id, offer.system_name, offer.station_name),
                         ("spansh", 123, "Adach", "Rippert Legacy"))
        self.assertEqual((offer.buy_price, offer.supply, offer.updated_at), (44862, 1000, NOW))
        self.assertEqual((offer.distance_ly, offer.dist_ls, offer.max_pad), (12.5, 80.5, "L"))
        self.assertFalse(offer.is_carrier)
        self.assertFalse(offer.suspect_price)
        url, body, timeout = requests[0]
        self.assertEqual((url, timeout), (SEARCH_URL, 10))
        # Literal request shape confirmed against the live API with size=5.
        self.assertEqual(body, {
            "filters": {
                "market": [{"name": "Tritium", "supply": {"comparison": ">=", "value": 720}}],
                "distance": {"min": 0, "max": 100.0},
                "has_large_pad": {"value": True},
                "type": {"value": ["Asteroid base", "Coriolis Starport", "Ocellus Starport",
                                   "Orbis Starport", "Outpost", "Planetary Outpost",
                                   "Planetary Port", "Settlement", "Mega ship"]},
                "market_updated_at": {"comparison": "<=>", "value": [
                    "2026-11-20T10:00:00+00:00", "2026-11-27T10:00:00+00:00"]},
            },
            "sort": [{"market_buy_price": [{"name": "Tritium", "direction": "asc"}]}],
            "size": 50, "page": 0, "reference_system": "Adach",
        })
        self.assertEqual(body["size"], 50)
        self.assertEqual(body["reference_system"], "Adach")
        self.assertEqual(body["sort"], [{"market_buy_price": [{"name": "Tritium", "direction": "asc"}]}])
        self.assertEqual(body["filters"]["distance"], {"min": 0, "max": 100})
        self.assertEqual(body["filters"]["has_large_pad"], {"value": True})
        self.assertEqual(body["filters"]["market"][0]["supply"], {"comparison": ">=", "value": 720})
        types = body["filters"]["type"]["value"]
        self.assertIn("Outpost", types)
        self.assertFalse(any("Carrier" in value for value in types))
        self.assertEqual(body["filters"]["market_updated_at"], {
            "comparison": "<=>", "value": ["2026-11-20T10:00:00+00:00", "2026-11-27T10:00:00+00:00"],
        })

    def test_galaxy_search_does_not_invent_distances_or_medium_pads(self):
        query = replace(QUERY, reference_system="", pad="M", include_carriers=True)
        body = spansh_search_body(query, "Tritium")
        for key in ("has_large_pad", "type", "distance"):
            self.assertNotIn(key, body["filters"])
        self.assertNotIn("reference_system", body)
        offers, _ = search_cheapest(query, "Tritium", lambda *_: {
            "results": [station(type="Fleet Carrier", has_large_pad=False,
                                distance_to_arrival=None, distance=None,
                                market_updated_at="2026-11-27T10:00:00Z")], "count": 1,
        }, now=NOW)
        offer, = offers
        self.assertTrue(offer.is_carrier)
        self.assertFalse(offer.suspect_price)
        self.assertEqual(offer.max_pad, "")
        self.assertIsNone(offer.distance_ly)
        self.assertIsNone(offer.dist_ls)

    def test_cleared_radius_keeps_reference_for_distance_column(self):
        body = spansh_search_body(replace(QUERY, radius_ly=None, pad="S", limit=5), "Gold")
        self.assertEqual(body["reference_system"], "Adach")
        self.assertEqual(body["size"], 5)
        self.assertEqual(body["filters"]["market"][0]["name"], "Gold")
        self.assertNotIn("distance", body["filters"])
        self.assertNotIn("has_large_pad", body["filters"])

    def test_empty_search_is_successful(self):
        self.assertEqual(search_cheapest(QUERY, "Tritium", lambda *_: {
            "results": [], "count": 0,
        }, now=NOW), ([], 0))

    def test_network_error_reaches_caller(self):
        def offline(*_):
            raise TimeoutError("Spansh timed out")
        with self.assertRaisesRegex(TimeoutError, "timed out"):
            search_cheapest(QUERY, "Tritium", offline, now=NOW)

    def test_unexpected_response_is_not_reported_as_empty_success(self):
        for response in (None, [], {}, {"error": "Unknown system"},
                         {"results": {}, "count": 0}, {"results": [], "count": "0"},
                         {"results": [], "count": True}, {"results": [], "count": -1},
                         {"results": [station()], "count": 0}):
            with self.subTest(response=response), self.assertRaisesRegex(ValueError, "Spansh"):
                search_cheapest(QUERY, "Tritium", lambda *_: response, now=NOW)

    def test_malformed_station_or_commodity_is_a_clear_error(self):
        for row in (None, station(market=None), station(market=[None]), station(market=[]),
                    station(market=[station()["market"][1]] * 2),
                    station(market=[{"commodity": "Tritium", "buy_price": "1", "supply": 1}]),
                    station(market_id=1.5), station(name=None), station(type=None),
                    station(has_large_pad="yes"), station(distance=float("nan")),
                    station(distance_to_arrival=-1), station(market_updated_at=None),
                    station(market_updated_at="invalid")):
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "Spansh response"):
                search_cheapest(QUERY, "Tritium", lambda *_: {
                    "results": [row], "count": 1,
                }, now=NOW)

    def test_timestamp_without_offset_is_utc(self):
        offers, _ = search_cheapest(QUERY, "Tritium", lambda *_: {
            "results": [station(market_updated_at="2026-11-27 10:00:00")], "count": 1,
        }, now=NOW)
        self.assertEqual(offers[0].updated_at, NOW)
