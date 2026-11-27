"""Service searches through HTTP and the peer link, without live network calls."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from edcr.eddn.messages import StationInfo, SystemPosition
from edcr.eddn.store import EddnStore
from edcr.hub.protocol import HubUnreachable, REQUEST_NEAREST_SERVICES
from edcr.spansh_stations import SYSTEM_SEARCH_URL
from tests.test_station_services import remote
from tests.shared_loop import TestClient
from tests.test_control_room_server import _base_data_read_model
from tests.test_hub import server, TOKEN


def unexpected_post(*args):
    raise AssertionError('This flow must not contact Spansh')


class ServicesEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.db = Path(tmp.name) / 'market.sqlite'
        store = EddnStore.open(cls.db)
        store.save([
            SystemPosition(1, 'Sol', 0, 0, 0, 100),
            StationInfo(1, 1, 'Sol', 'Port', 'Coriolis', 50, 'L', 100,
                        services=('carriermanagement', 'customservice')),
            StationInfo(2, 1, 'Sol', 'Small Port', 'Outpost', 20, 'S', 100,
                        services=('carriermanagement',)),
            StationInfo(3, 1, 'Sol', 'Other Port', 'Coriolis', 50, 'L', 100,
                        services=('shipyard',)),
            StationInfo(4, 2, 'Uncharted', 'Unranked Port', 'Coriolis', 50, 'L', 100,
                        services=('no-coordinates-service',)),
        ])
        store.close()

    def setUp(self):
        data = _base_data_read_model()
        self.data = replace(data, ship=replace(data.ship, system='Sol', ship_type='python'))
        defaults = patch('edcr.control_room.server.app.load_haul_search_config',
                         return_value={'min_landing_pad': 'large'})
        defaults.start()
        self.addCleanup(defaults.stop)

    def app(self, **kwargs):
        return server(data_provider=lambda: self.data, market_database_file=self.db,
                      spansh_post=kwargs.pop('spansh_post', unexpected_post), **kwargs)

    def get(self, app, **params):
        with TestClient(app) as client:
            return client.get('/api/nearest-services', params={
                'access_token': TOKEN, 'service': 'carriermanagement', **params})

    def answer(self, app, **params):
        return app.state.link_handlers[REQUEST_NEAREST_SERVICES]({
            'service': 'carriermanagement', 'system': 'Sol', 'spansh': '0', **params})

    def test_ship_defaults_coverage_and_explicit_filters(self):
        app = self.app()
        result = self.get(app, spansh='0').json()
        self.assertEqual((result['query']['reference_system'], result['query']['pad']), ('Sol', 'M'))
        self.assertEqual(result['query']['radius_ly'], 200)
        self.assertEqual(result['hub_known'], 4)
        self.assertEqual(result['hidden'], {'carrier': 0, 'pad': 1, 'radius': 0, 'no_coords': 0})
        self.assertEqual([row['station_name'] for row in result['stations']], ['Port'])
        self.assertGreaterEqual(result['stations'][0]['age_s'], 0)
        self.assertEqual(result['spansh'], {'asked': False, 'count': None, 'error': ''})
        result = self.get(app, spansh='0', radius_ly='', pad='S', carriers='1', limit='50').json()
        self.assertIsNone(result['query']['radius_ly'])
        self.assertTrue(result['query']['include_carriers'])
        self.assertEqual(len(result['stations']), 2)

    def test_station_without_coordinates_has_its_own_reason_even_without_radius(self):
        app = self.app()
        for radius in ('200', ''):
            result = self.answer(app, service='no-coordinates-service', radius_ly=radius).body
            self.assertEqual(result['stations'], [])
            self.assertEqual(result['hidden']['no_coords'], 1)
            self.assertEqual(result['hidden']['radius'], 0)
            self.assertEqual(result['total'], 0)

    def test_unknown_ship_uses_configured_pad(self):
        self.data = replace(self.data, ship=replace(self.data.ship, ship_type='unknown'))
        self.assertEqual(self.get(self.app(), spansh='0').json()['query']['pad'], 'L')

    def test_spansh_merges_newer_station_and_receives_service_label(self):
        sent = []
        def post(url, body, timeout):
            sent.append(body)
            return {'count': 1, 'results': [{
                'market_id': 1, 'system_name': 'Sol', 'name': 'Updated Port',
                'type': 'Coriolis Starport', 'distance': 0, 'large_pads': 1,
                'updated_at': '2026-11-27T00:00:00Z',
                'services': [{'name': 'Fleet Carrier Administration'}]}]}
        result = self.get(self.app(spansh_post=post)).json()
        self.assertEqual([row['station_name'] for row in result['stations']], ['Updated Port'])
        self.assertEqual(result['stations'][0]['source'], 'spansh')
        self.assertEqual(result['spansh'], {'asked': True, 'count': 1, 'error': ''})
        self.assertEqual(sent[0]['filters']['services'], [{'name': 'Fleet Carrier Administration'}])

    def test_spansh_failure_retains_hub_rows(self):
        def offline(*args):
            raise OSError('Spansh offline')
        result = self.get(self.app(spansh_post=offline)).json()
        self.assertEqual(result['spansh'], {'asked': True, 'count': None, 'error': 'Spansh offline'})
        self.assertEqual(result['stations'][0]['station_name'], 'Port')

    def test_unknown_service_searches_hub_and_explains_skipped_spansh(self):
        result = self.get(self.app(), service='customservice').json()
        self.assertFalse(result['spansh']['asked'])
        self.assertIn('customservice', result['spansh']['error'])
        self.assertEqual(result['stations'][0]['station_name'], 'Port')

    def test_auth_validation_unknown_system_and_missing_store(self):
        app = self.app()
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/nearest-services').status_code, 401)
        self.assertEqual(self.get(app, pad='bad').status_code, 400)
        self.assertEqual(self.get(app, service='').status_code, 400)
        reply = self.answer(app, system='Unknown')
        self.assertEqual((reply.status, reply.body['detail']), (404, 'Unknown system'))
        self.assertEqual(self.answer(server(spansh_post=unexpected_post)).status, 404)
        handler = app.state.link_handlers[REQUEST_NEAREST_SERVICES]
        self.assertEqual(handler([]).status, 400)
        self.assertEqual(handler({'service': 123}).status, 400)

    def test_unknown_origin_resolves_spansh_coordinates_and_applies_radius(self):
        def post(url, body, timeout):
            if url == SYSTEM_SEARCH_URL:
                return {'results': [{'name': 'Unknown', 'x': -3, 'y': 4, 'z': 0}]}
            return {'count': 0, 'results': []}
        app = self.app(spansh_post=post)
        result = self.answer(app, spansh='1', system='Unknown', radius_ly='5').body
        self.assertEqual(result['stations'][0]['distance_ly'], 5)
        result = self.answer(app, spansh='1', system='Unknown', radius_ly='4').body
        self.assertEqual(result['stations'], [])
        self.assertEqual(result['hidden']['radius'], 1)

    def test_missing_or_failed_coordinates_keep_spansh_results_and_count_unranked_hub(self):
        for missing in (True, False):
            def post(url, body, timeout):
                if url == SYSTEM_SEARCH_URL:
                    if missing:
                        return {'results': []}
                    raise OSError('Lookup offline')
                return {'count': 1, 'results': [remote(market_id=4)]}
            reply = self.answer(self.app(spansh_post=post), spansh='1', system='Unknown',
                                radius_ly='')
            self.assertEqual(reply.status, 200)
            self.assertEqual([row['market_id'] for row in reply.body['stations']], [4])
            self.assertEqual(reply.body['total'], 1)
            self.assertEqual(reply.body['hidden']['no_coords'], 1)
            self.assertEqual(reply.body['hidden']['radius'], 0)
            self.assertIn('coordinates' if missing else 'Lookup offline', reply.body['spansh']['error'])

    def test_returned_spansh_exclusions_combine_with_hub_counts_and_total_before_limit(self):
        rows = [remote(market_id=mid) for mid in range(10, 65)]
        rows += [remote(market_id=70, large_pads=0, medium_pads=0),
                 remote(market_id=71, type='Fleet Carrier'),
                 remote(market_id=72, distance=201)]
        result = self.answer(self.app(spansh_post=lambda *_: {'results': rows, 'count': len(rows)}),
                             spansh='1').body
        self.assertEqual(len(result['stations']), 50)
        self.assertEqual(result['total'], 56)
        self.assertEqual(result['hidden'], {'pad': 2, 'carrier': 1, 'radius': 1, 'no_coords': 0})

    def test_peer_forwards_resolved_defaults_with_search_timeout_and_reports_disconnect(self):
        hub = self.app()
        sent = []
        def request(kind, body, *, timeout_s):
            sent.append((kind, body, timeout_s))
            return hub.state.link_handlers[kind](body)
        link = SimpleNamespace(hello=None, request=request, hub_label='Home hub',
                               search_timeout_s=20, request_timeout_s=5)
        peer = self.app(peer_link=link)
        result = self.get(peer, spansh='0', radius_ly='').json()
        self.assertEqual(result['query']['pad'], 'M')
        self.assertEqual(sent[0][0], REQUEST_NEAREST_SERVICES)
        self.assertEqual(sent[0][1]['system'], 'Sol')
        self.assertNotIn('limit', sent[0][1])
        self.assertEqual(sent[0][1]['radius_ly'], '')
        self.assertEqual(sent[0][2], 20)
        def disconnected(*args, **kwargs):
            raise HubUnreachable('offline')
        link.request = disconnected
        self.assertEqual(self.get(peer).status_code, 502)

    def test_hub_answers_using_viewed_ship_and_checks_missing_node_state(self):
        nodes = [{'node_id': 'remote', 'name': 'Remote ship', 'connected': True,
                  'state': {'current_system': 'Sol', 'ship': {'type': 'cutter'}}}]
        registry = SimpleNamespace(local=SimpleNamespace(node_id='local'), nodes=lambda: nodes)
        app = self.app(hub_side=SimpleNamespace(registry=registry, relay=None))
        result = self.get(app, node='remote', spansh='0').json()
        self.assertEqual((result['query']['pad'], result['query']['reference_system']), ('L', 'Sol'))
        del nodes[0]['state']['current_system']
        self.assertEqual(self.get(app, node='remote', spansh='0').status_code, 409)
        self.assertEqual(self.get(app, node='remote', system='Sol', spansh='0').status_code, 200)
        nodes[0]['state'] = {}
        self.assertEqual(self.get(app, node='remote', spansh='0').status_code, 409)
        nodes[0]['connected'] = False
        self.assertEqual(self.get(app, node='remote', spansh='0').status_code, 502)
        self.assertEqual(self.get(app, node='missing', spansh='0').status_code, 502)

    def test_page_and_script_are_served(self):
        with TestClient(self.app()) as client:
            page = client.get('/services')
            self.assertEqual(page.status_code, 200)
            self.assertIn('services.js', page.text)
            script = client.get('/assets/services.js')
            self.assertEqual(script.status_code, 200)
            self.assertIn('text/javascript', script.headers['content-type'])
