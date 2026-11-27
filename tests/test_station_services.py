"""Service searches through journal observations and an injected Spansh boundary."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from edcr.cheapest_markets import hub_system_coordinates
from edcr.eddn.messages import parse_eddn_message
from edcr.eddn.store import EddnStore
from edcr.spansh_stations import NON_CARRIER_TYPES, SEARCH_URL, search_service
from edcr.station_services import (
    PAGE_SERVICES, SERVICE_LABELS, ServiceQuery, ServiceStation, merge_stations,
    parse_service_query, query_hub_services, services_payload,
)
from tests.test_eddn import docked_envelope

NOW = 1795773600.0
QUERY = ServiceQuery('carriermanagement', 'Sol', 200.0, 'L', False, True, 50)
STATION = ServiceStation('hub', 1, 'Sol', 'Port', 'Coriolis', False, 'L', 50, 0, NOW)


def remote(**changes):
    return {
        'market_id': 1, 'name': 'Port', 'type': 'Coriolis Starport', 'system_name': 'Sol',
        'distance': 5, 'distance_to_arrival': 50, 'large_pads': 3, 'medium_pads': 2, 'small_pads': 1,
        'services': [{'name': 'Fleet Carrier Administration'}],
        'updated_at': '2026-11-27T10:00:00Z', **changes,
    }


class ParsingTests(unittest.TestCase):
    def parse(self, **params):
        return parse_service_query(params, current_system='Sol', ship_pad='L')

    def test_defaults_and_service_normalization(self):
        self.assertEqual(self.parse(service=' CarrierManagement '), QUERY)
        self.assertEqual(PAGE_SERVICES, tuple(SERVICE_LABELS))
        self.assertEqual(SERVICE_LABELS['carriervendor'], 'Fleet Carrier Vendor')

    def test_any_symbol_and_operator_overrides(self):
        self.assertEqual(self.parse(service='stationMenu', system=' Achenar ', radius_ly='',
                                    pad='m', carriers='1', spansh='0', limit='100'),
                         ServiceQuery('stationmenu', 'Achenar', None, 'M', True, False, 50))
        self.assertEqual(self.parse(service='dock', radius_ly='0').radius_ly, 0)

    def test_invalid_filters_are_visible(self):
        for key, values in {'service': ['', ' '], 'system': ['', ' '], 'pad': ['', 'XL'],
                            'radius_ly': ['nan', 'inf', '-1', 'no'],
                            'carriers': ['yes', ''], 'spansh': ['false', '2']}.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, key):
                    self.parse(**({'service': 'dock'} | {key: value}))


class HubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.temp.name) / 'services.sqlite'
        store = EddnStore.open(cls.db)
        fixtures = [
            (1, 0, 'L', 'Coriolis', 100, ['carriermanagement']),
            (2, 5, 'L', 'Coriolis', 20, ['carriermanagement']),
            (3, 5, 'M', 'Outpost', 10, ['carriermanagement']),
            (4, 300, 'L', 'Coriolis', 10, ['carriermanagement']),
            (5, 400, 'S', 'FleetCarrier', 10, ['carriermanagement']),
            (6, 5, '', 'Unknown', 30, ['carriermanagement']),
            (7, 0, 'L', 'Coriolis', 10, ['shipyard']),
            (8, 0, 'L', 'Coriolis', 10, []),
        ]
        for mid, distance, pad, kind, arrival, services in fixtures:
            store.save(parse_eddn_message(docked_envelope(
                event='Location' if mid % 2 else 'Docked', Docked=True,
                timestamp='2026-11-27T10:00:00Z', MarketID=mid, SystemAddress=mid,
                StarSystem='Sol' if mid == 1 else f'System {mid}', StarPos=[distance, 0, 0],
                StationName=f'Port {mid}', StationType=kind, DistFromStarLS=arrival,
                LandingPads={name: int(size == pad) for name, size in
                             [('Small', 'S'), ('Medium', 'M'), ('Large', 'L')]},
                StationServices=services,
            )))
        store.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def search(self, **changes):
        return query_hub_services(self.db, replace(QUERY, **changes),
                                  hub_system_coordinates(self.db, 'sOL'))

    def test_nearest_stations_count_each_exclusion_once_and_keep_unknown_pad(self):
        rows, hidden = self.search()
        self.assertEqual([row.market_id for row in rows], [1, 2, 6])
        self.assertEqual(hidden, {'carrier': 1, 'pad': 1, 'radius': 1})
        self.assertEqual((rows[0].services_at, rows[1].distance_ly, rows[-1].max_pad),
                         (NOW, 5, ''))

    def test_radius_is_inclusive_and_arrival_breaks_distance_ties(self):
        rows, hidden = self.search(radius_ly=5, pad='S')
        self.assertEqual([row.market_id for row in rows], [1, 3, 2, 6])
        self.assertEqual(hidden, {'carrier': 1, 'pad': 0, 'radius': 1})

    def test_global_search_and_carrier_toggle_and_no_early_limit(self):
        rows, hidden = self.search(radius_ly=None, pad='S', include_carriers=True, limit=1)
        self.assertEqual([row.market_id for row in rows], [1, 3, 2, 6, 4, 5])
        self.assertTrue(rows[-1].is_carrier)
        self.assertEqual(sum(hidden.values()), 0)

    def test_unobserved_service_is_empty(self):
        self.assertEqual(self.search(service='carriervendor'),
                         ([], {'carrier': 0, 'pad': 0, 'radius': 0}))


class MergePayloadTests(unittest.TestCase):
    def test_newest_wins_ties_prefer_hub_and_missing_pad_is_filled(self):
        for delta in (-1, 0, 1):
            row, = merge_stations([STATION], [replace(STATION, source='spansh',
                                  max_pad='', services_at=NOW + delta)], QUERY)
            self.assertEqual(row.source, 'spansh' if delta > 0 else 'hub')
            self.assertEqual(row.max_pad, 'L')
        row, = merge_stations([STATION], [replace(STATION, source='spansh',
                              max_pad='M', services_at=NOW + 1)], replace(QUERY, pad='M'))
        self.assertEqual(row.max_pad, 'M')

    def test_merge_filters_remote_rows_sorts_and_limits(self):
        rows = [replace(STATION, market_id=2, distance_ly=5, dist_ls=None),
                replace(STATION, market_id=3, distance_ly=5, dist_ls=10),
                replace(STATION, market_id=4, max_pad='S'),
                replace(STATION, market_id=5, is_carrier=True),
                replace(STATION, market_id=6, distance_ly=201)]
        self.assertEqual([row.market_id for row in merge_stations(
            [STATION], rows, replace(QUERY, limit=2))], [1, 3])

    def test_payload_keeps_hub_results_on_remote_failure_and_reports_coverage(self):
        payload = services_payload([STATION], QUERY, {'carrier': 2, 'pad': 3, 'radius': 4}, 123,
                                  spansh_asked=True, spansh_count=None,
                                  spansh_error='offline', now=NOW + 3600)
        self.assertEqual(payload['label'], 'Fleet Carrier Administration')
        self.assertEqual(payload['stations'][0]['age_s'], 3600)
        self.assertEqual(payload['hub_known'], 123)
        self.assertEqual(payload['query']['radius_ly'], 200)
        self.assertEqual(payload['hidden'], {'carrier': 2, 'pad': 3, 'radius': 4})
        self.assertEqual(payload['spansh'], {'asked': True, 'count': None, 'error': 'offline'})
        payload = services_payload([STATION], replace(QUERY, service='dock'), {}, 1,
                                  spansh_asked=False, spansh_count=None,
                                  spansh_error='No Spansh name for dock', now=NOW - 1)
        self.assertEqual(payload['label'], 'dock')
        self.assertEqual(payload['stations'][0]['age_s'], 0)
        self.assertFalse(payload['spansh']['asked'])


class SpanshTests(unittest.TestCase):
    def search(self, rows, **changes):
        return search_service(replace(QUERY, **changes), SERVICE_LABELS[QUERY.service],
                              lambda *_: {'results': rows, 'count': len(rows)}, (0, 0, 0))

    def test_request_shape_and_service_timestamp(self):
        requests = []
        def post(url, body, timeout):
            requests.append((url, body, timeout))
            return {'results': [remote()], 'count': 393}
        rows, count = search_service(QUERY, SERVICE_LABELS[QUERY.service], post, (0, 0, 0))
        self.assertEqual(count, 393)
        self.assertEqual(rows, [replace(STATION, source='spansh', station_type='Coriolis Starport',
                                        distance_ly=5)])
        self.assertEqual(requests, [(SEARCH_URL, {
            'filters': {'services': [{'name': 'Fleet Carrier Administration'}],
                        'distance': {'min': 0, 'max': 200},
                        'type': {'value': list(NON_CARRIER_TYPES)}, 'has_large_pad': {'value': True}},
            'sort': [{'distance': {'direction': 'asc'}}],
            'size': 50, 'page': 0, 'reference_system': 'Sol'}, 10)])

    def test_global_carrier_search_and_pad_counts(self):
        requests = []
        def post(url, body, timeout):
            requests.append(body)
            return {'results': [], 'count': 0}
        query = replace(QUERY, include_carriers=True, radius_ly=None, pad='M')
        self.assertEqual(search_service(query, 'Shipyard', post, (0, 0, 0)), ([], 0))
        self.assertEqual(requests[0]['filters'], {'services': [{'name': 'Shipyard'}]})
        for large, medium, small, expected in [(0, 2, 3, 'M'), (0, 0, 1, 'S'),
                                               (None, None, None, '')]:
            rows, _ = self.search([remote(type='Fleet Carrier', large_pads=large,
                                         medium_pads=medium, small_pads=small)], include_carriers=True)
            self.assertEqual(rows[0].max_pad, expected)
            self.assertTrue(rows[0].is_carrier)

    def test_malformed_responses_are_visible_instead_of_silent_omissions(self):
        responses = [None, {}, {'error': 'offline'}, {'results': {}, 'count': 0},
                     {'results': [], 'count': True}, {'results': [remote()], 'count': 0}]
        bad_rows = [None, remote(services=[]), remote(market_id=1.5), remote(name=None),
                    remote(distance=float('nan')), remote(distance_to_arrival=-1),
                    remote(large_pads='3'), remote(updated_at='bad')]
        responses.extend({'results': [row], 'count': 1} for row in bad_rows)
        for response in responses:
            with self.subTest(response=response), self.assertRaisesRegex(ValueError, 'Spansh'):
                search_service(QUERY, SERVICE_LABELS[QUERY.service], lambda *_: response, (0, 0, 0))

    def test_offline_error_reaches_caller_for_hub_fallback(self):
        def offline(*_):
            raise TimeoutError('offline')
        with self.assertRaisesRegex(TimeoutError, 'offline'):
            search_service(QUERY, SERVICE_LABELS[QUERY.service], offline, (0, 0, 0))
