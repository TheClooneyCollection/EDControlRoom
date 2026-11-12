from __future__ import annotations

import unittest

from edcr.ardent import ArdentError, ArdentLookup
from edcr.eddn.messages import StationInfo, SystemPosition
from edcr.trade_trip import PartialFacts, store_lookup
from tests.test_eddn import memory_store

BASE = "https://ardent.test/v2"


def station_row(market_id: int, name: str, *, station_type: str = "Ocellus", dist: float = 5.67, pad: int = 3) -> dict:
    return {
        "marketId": market_id, "stationName": name, "stationType": station_type, "distanceToArrival": dist,
        "maxLandingPadSize": pad, "systemAddress": 5368172137344, "systemName": "Chelgit",
        "systemX": 6.21875, "systemY": -33.5, "systemZ": 56.21875, "updatedAt": "2026-10-25T19:18:53.681Z",
    }


class FakeArdent:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, float]] = []

    def __call__(self, url: str, timeout_s: float) -> object:
        self.requests.append((url, timeout_s))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


class ArdentLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = 1000.0
        self.saved: list[object] = []
        self.logs: list[str] = []

    def lookup(self, fetch: FakeArdent) -> ArdentLookup:
        return ArdentLookup(fetch, now=lambda: self.clock, save=self.saved.extend, log=self.logs.append,
                            base_url=BASE, timeout_s=2.5, retry_after_s=600.0)

    def test_one_stations_request_fills_the_station_and_is_cached_and_saved(self) -> None:
        fetch = FakeArdent({f"{BASE}/system/name/Chelgit/stations": [
            station_row(3225948672, "Humboldt Hub"), station_row(42, "Allard's Mineralogical",
                                                                 station_type="OnFootSettlement", pad=1),
            {"stationName": "No market id"},
        ]})
        lookup = self.lookup(fetch)

        first = lookup(3225948672, "Humboldt Hub", "Chelgit")
        by_name = lookup(0, "allard's mineralogical", "chelgit")

        self.assertEqual(first, PartialFacts((6.21875, -33.5, 56.21875), 5.67, "Ocellus"))
        self.assertEqual(by_name.station_type, "OnFootSettlement")
        self.assertEqual(fetch.requests, [(f"{BASE}/system/name/Chelgit/stations", 2.5)])
        position, hub, settlement = self.saved
        self.assertIsInstance(position, SystemPosition)
        self.assertEqual((hub.market_id, hub.max_pad, hub.system_address), (3225948672, "L", 5368172137344))
        self.assertEqual(settlement.max_pad, "S")

    def test_a_system_without_stations_gets_coordinates_from_the_system_endpoint(self) -> None:
        url = f"{BASE}/system/name/LHS%20493"
        fetch = FakeArdent({f"{url}/stations": [], url: {
            "systemAddress": 7, "systemName": "LHS 493", "systemX": 1.0, "systemY": 2.0, "systemZ": 3.0,
            "updatedAt": "2023-04-28T09:19:59.000Z"}})

        facts = self.lookup(fetch)(9, "Somewhere", "LHS 493")

        self.assertEqual(facts, PartialFacts(coords=(1.0, 2.0, 3.0)))
        self.assertEqual([request for request, _ in fetch.requests], [f"{url}/stations", url])

    def test_a_failed_lookup_knows_nothing_and_waits_before_asking_again(self) -> None:
        url = f"{BASE}/system/name/Chelgit/stations"
        fetch = FakeArdent({url: ArdentError("timed out")})
        lookup = self.lookup(fetch)

        self.assertEqual(lookup(1, "Humboldt Hub", "Chelgit"), PartialFacts())
        self.assertEqual(lookup(1, "Humboldt Hub", "Chelgit"), PartialFacts())
        self.clock += 601.0
        fetch.responses[url] = [station_row(1, "Humboldt Hub")]
        recovered = lookup(1, "Humboldt Hub", "Chelgit")

        self.assertEqual(len(fetch.requests), 2)
        self.assertEqual(recovered.dist_ls, 5.67)
        self.assertEqual(self.logs, ["Ardent lookup for Chelgit failed: timed out"])

    def test_an_unexpected_error_or_body_is_a_failed_lookup(self) -> None:
        fetch = FakeArdent({f"{BASE}/system/name/A/stations": ValueError("bad json"),
                            f"{BASE}/system/name/B/stations": {"detail": "oops"}})
        lookup = self.lookup(fetch)

        self.assertEqual(lookup(1, "x", "A"), PartialFacts())
        self.assertEqual(lookup(1, "x", "B"), PartialFacts())
        self.assertEqual(len(self.logs), 2)
        self.assertEqual(self.saved, [])

    def test_saved_rows_land_in_the_eddn_store_for_routes_and_best_deal(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        store.save([
            SystemPosition(address=7, name="Chelgit", x=6.0, y=-33.5, z=56.0, timestamp=1.0),
            StationInfo(market_id=11, system_address=7, system_name="Chelgit", name="Humboldt Hub",
                        type="Ocellus", dist_ls=5.7, max_pad="L", timestamp=1.0),
        ])

        self.assertEqual(store_lookup(store._db)(11, "Humboldt Hub", "Chelgit"),
                         PartialFacts((6.0, -33.5, 56.0), 5.7, "Ocellus"))


if __name__ == "__main__":
    unittest.main()
