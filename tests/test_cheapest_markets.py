"""Commodity buying flows through the hub store and merged public payload."""
from dataclasses import replace
from pathlib import Path
import tempfile
import time
import unittest

from edcr.cheapest_markets import (
    CheapestQuery, CheapestResult, MarketOffer, UnknownSystemError,
    cheapest_payload, merge_offers, parse_cheapest_query, query_hub_store,
)
from edcr.eddn.messages import CommodityPrice, MarketSnapshot, StationInfo, SystemPosition
from edcr.eddn.store import EddnStore

NOW = 1_800_000_000.0
QUERY = CheapestQuery('tritium', 'Sol', 100.0, 100, 'L', 168.0, False, True, 50)
OFFER = MarketOffer('hub', 1, 'Sol', 'Port', 'Coriolis', False, 'L', 50.0, 0.0,
                    1000, 500, NOW, False)


class QueryParsingTests(unittest.TestCase):
    def parse(self, **params):
        return parse_cheapest_query(params, current_system='Sol', cargo_capacity=720, ship_pad='L')

    def test_ship_defaults_and_commodity_normalisation(self):
        self.assertEqual(self.parse(commodity=' $Tritium_Name; '), replace(QUERY, min_supply=720))

    def test_operator_can_override_every_filter(self):
        self.assertEqual(self.parse(commodity='gold', system=' Achenar ', radius_ly='15.5',
                                    min_supply='20', pad='m', max_age_hours='2.5', carriers='1', spansh='0'),
                         CheapestQuery('gold', 'Achenar', 15.5, 20, 'M', 2.5, True, False, 50))

    def test_clear_radius_or_system_for_global_search(self):
        self.assertIsNone(self.parse(commodity='gold', radius_ly='').radius_ly)
        self.assertEqual(self.parse(commodity='gold', system='').reference_system, '')
        self.assertIsNone(self.parse(commodity='gold', system='').radius_ly)

    def test_invalid_filters_raise_readable_validation_errors(self):
        for key, values in {
            'commodity': ['', '   '], 'pad': ['', 'XL'], 'min_supply': ['-1', '1.2', 'nan'],
            'radius_ly': ['-1', 'nan', 'inf', 'no'],
            'max_age_hours': ['-1', 'nan', '-inf', 'no', ''],
            'carriers': ['yes', '2'], 'spansh': ['false', ''],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, key):
                    self.parse(**dict({'commodity': 'tritium'}, **{key: value}))

    def test_zero_filters_are_valid_and_limit_is_fixed(self):
        query = self.parse(commodity='gold', radius_ly='0', min_supply='0', max_age_hours='0', limit='10000')
        self.assertEqual((query.radius_ly, query.min_supply, query.max_age_hours, query.limit), (0, 0, 0, 50))


class HubStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.temp.name) / 'markets.sqlite'
        store = EddnStore.open(cls.db)
        store.save([SystemPosition(1, 'Sol', 0, 0, 0, NOW),
                    SystemPosition(2, 'Near', 3, 4, 0, NOW),
                    SystemPosition(3, 'Far', 101, 0, 0, NOW)])
        # Every multi-failure row should contribute only to its first reason.
        fixtures = [
            (1, 'Sol', 1, False, 'L', 100, NOW, 1000),
            (2, 'Far', 3, True, 'S', 1, NOW - 700000, 20),
            (3, 'Far', 3, False, 'M', 1, NOW - 700000, 1000),
            (4, 'Far', 3, False, 'L', 1, NOW - 700000, 1000),
            (5, 'Far', 3, False, 'L', 100, NOW - 700000, 1000),
            (6, 'Far', 3, False, 'L', 100, NOW, 1000),
            (7, 'Near', 2, False, '', 100, NOW, 900),
            (8, 'Sol', 1, False, 'L', 0, NOW, 1),
            (9, 'Unmapped', 9, False, 'L', 100, NOW, 1000),
            (10, 'Near', 2, True, 'L', 100, NOW, 99),
            (11, 'Near', 2, True, 'L', 100, NOW, 100),
            (12, 'Near', 2, False, 'L', 100, NOW - 168 * 3600, 1000),
        ]
        for mid, system, address, carrier, pad, supply, updated, price in fixtures:
            store.save([
                StationInfo(mid, address, system, f'Port {mid}', 'FleetCarrier' if carrier else 'Coriolis',
                            50.0, pad, NOW),
                MarketSnapshot(mid, system, f'Port {mid}', carrier, updated,
                               (CommodityPrice('tritium', price, 0, supply, 0),), ''),
            ])
        # A market without station facts is still useful; coordinates come from its latest market system.
        store.save([MarketSnapshot(13, 'Sol', 'Unknown pad', False, NOW,
                                   (CommodityPrice('tritium', 1100, 0, 100, 0),), '')])
        store.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_ship_search_counts_first_failure_and_keeps_unknown_pads(self):
        offers, hidden = query_hub_store(self.db, QUERY, now=NOW)
        self.assertEqual([o.market_id for o in offers], [7, 1, 12, 13])
        self.assertEqual(hidden, {'carrier': 3, 'pad': 1, 'supply': 1, 'age': 1, 'radius': 2})
        self.assertEqual(offers[0].distance_ly, 5.0)
        self.assertEqual(offers[0].max_pad, '')
        self.assertEqual((offers[-1].station_type, offers[-1].dist_ls), ('', None))

    def test_carrier_toggle_exposes_suspect_prices_strictly_below_threshold(self):
        offers, hidden = query_hub_store(self.db, replace(QUERY, include_carriers=True), now=NOW)
        self.assertEqual([(o.market_id, o.suspect_price) for o in offers[:2]], [(10, True), (11, False)])
        self.assertEqual(hidden['carrier'], 0)
        self.assertEqual(hidden['pad'], 2)

    def test_unknown_reference_errors_without_spansh_and_keeps_rows_with_it(self):
        query = replace(QUERY, reference_system='Missing')
        with self.assertRaisesRegex(UnknownSystemError, 'Unknown system: Missing'):
            query_hub_store(self.db, replace(query, use_spansh=False), now=NOW)
        offers, hidden = query_hub_store(self.db, query, now=NOW)
        self.assertEqual(len(offers), 6)
        self.assertTrue(all(o.distance_ly is None for o in offers))
        self.assertEqual(hidden['radius'], 0)

    def test_no_reference_means_no_distance_and_no_radius(self):
        offers, hidden = query_hub_store(self.db, replace(QUERY, reference_system=''), now=NOW)
        self.assertEqual(len(offers), 6)
        self.assertTrue(all(o.distance_ly is None for o in offers))
        self.assertEqual(hidden['radius'], 0)

    def test_global_radius_keeps_distance_and_unknown_locations(self):
        offers, hidden = query_hub_store(self.db, replace(QUERY, radius_ly=None), now=NOW)
        self.assertEqual(len(offers), 6)
        self.assertEqual(hidden['radius'], 0)
        self.assertEqual(next(o for o in offers if o.market_id == 6).distance_ly, 101)

    def test_radius_and_age_boundaries_are_inclusive_case_insensitive_reference(self):
        offers, _ = query_hub_store(self.db, replace(QUERY, reference_system='sOL', radius_ly=5), now=NOW)
        self.assertIn(12, [o.market_id for o in offers])

    def test_commodity_without_sellers_is_empty(self):
        offers, hidden = query_hub_store(self.db, replace(QUERY, commodity='gold'), now=NOW)
        self.assertEqual(offers, [])
        self.assertEqual(sum(hidden.values()), 0)

    def test_hub_does_not_limit_before_merge(self):
        offers, _ = query_hub_store(self.db, replace(QUERY, limit=1), now=NOW)
        self.assertEqual(len(offers), 4)


class MergeAndPayloadTests(unittest.TestCase):
    def test_newer_spansh_wins_with_hub_medium_pad_and_ties_keep_hub(self):
        hub = replace(OFFER, max_pad='M')
        for delta in [-1, 0, 1]:
            with self.subTest(delta=delta):
                remote = replace(OFFER, source='spansh', max_pad='', updated_at=NOW + delta)
                offers = merge_offers([hub], [remote], QUERY)
                self.assertEqual(offers[0].source, 'spansh' if delta > 0 else 'hub')
                self.assertEqual(offers[0].max_pad, 'M')
        self.assertEqual(hub.max_pad, 'M')

    def test_sort_by_price_distance_then_limit_and_unknown_distance_last(self):
        offers = [replace(OFFER, market_id=1, distance_ly=None),
                  replace(OFFER, market_id=2, distance_ly=50),
                  replace(OFFER, market_id=3, distance_ly=0),
                  replace(OFFER, market_id=4, buy_price=999, distance_ly=100)]
        self.assertEqual([o.market_id for o in merge_offers(offers, [], replace(QUERY, limit=3))], [4, 3, 2])

    def test_carrier_flag_uses_merged_station_median_before_limit(self):
        rows = [OFFER, replace(OFFER, market_id=2, buy_price=3000),
                replace(OFFER, market_id=3, buy_price=199, is_carrier=True, source='spansh'),
                replace(OFFER, market_id=4, buy_price=200, is_carrier=True)]
        offers = merge_offers(rows[:2], rows[2:], replace(QUERY, limit=2))
        self.assertEqual([o.suspect_price for o in offers], [True, False])

    def test_prior_hub_suspect_flag_survives_filtered_station_baseline(self):
        carrier = replace(OFFER, is_carrier=True, suspect_price=True)
        self.assertTrue(merge_offers([carrier], [], QUERY)[0].suspect_price)
        self.assertFalse(merge_offers([], [replace(carrier, suspect_price=False)], QUERY)[0].suspect_price)

    def test_payload_retains_hub_results_and_spansh_failure(self):
        now = time.time()
        offer = replace(OFFER, updated_at=now - 60)
        hidden = {'carrier': 12, 'pad': 0, 'supply': 0, 'age': 0, 'radius': 0}
        payload = cheapest_payload(CheapestResult([offer], hidden, None, 'Timed out'), QUERY, 'Tritium')
        self.assertEqual(payload['commodity'], 'tritium')
        self.assertEqual(payload['name'], 'Tritium')
        self.assertEqual(payload['query']['reference_system'], 'Sol')
        self.assertEqual(payload['spansh'], {'asked': True, 'count': None, 'error': 'Timed out'})
        self.assertEqual(payload['hidden'], hidden)
        self.assertAlmostEqual(payload['offers'][0]['age_s'], 60, delta=1)
        self.assertEqual(payload['offers'][0]['source'], 'hub')

    def test_empty_payload_spansh_count_and_future_age(self):
        result = CheapestResult([], {}, 123, '')
        self.assertEqual(cheapest_payload(result, QUERY, 'Tritium')['spansh']['count'], 123)
        result = CheapestResult([replace(OFFER, updated_at=time.time() + 60)], {}, None, '')
        payload = cheapest_payload(result, replace(QUERY, use_spansh=False), 'Tritium')
        self.assertFalse(payload['spansh']['asked'])
        self.assertEqual(payload['offers'][0]['age_s'], 0)
