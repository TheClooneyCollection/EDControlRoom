"""Cheapest-market HTTP flows, with in-memory peers and an injected Spansh transport."""
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

from edcr.eddn.messages import CommodityPrice, MarketSnapshot, StationInfo, SystemPosition
from edcr.eddn.store import EddnStore
from edcr.hub.protocol import HubUnreachable, REQUEST_CHEAPEST_MARKETS
from edcr.recent_markets import MarketSnapshot as RecentMarket, save_recent_markets
from edcr.ship_types import SHIP_PAD_SIZES, SHIP_TYPE_NAMES, ship_pad_size
from tests.shared_loop import TestClient
from tests.test_control_room_server import _base_data_read_model
from tests.test_hub import server, TOKEN


def unexpected_post(url, body, timeout):
    raise AssertionError('This flow must not contact Spansh')


class CheapestEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.db = Path(tmp.name) / 'market.sqlite'
        cls.now = time.time()
        store = EddnStore.open(cls.db)
        store.save([SystemPosition(1, 'Sol', 0, 0, 0, cls.now),
                    StationInfo(1, 1, 'Sol', 'Port', 'Coriolis', 50, 'L', cls.now),
                    MarketSnapshot(1, 'Sol', 'Port', False, cls.now,
                                   (CommodityPrice('tritium', 1000, 0, 1000, 0),), '')])
        store.close()

    def setUp(self):
        data = _base_data_read_model()
        self.data = replace(data, ship=replace(data.ship, system='Sol', ship_type='python', cargo_capacity=128))
        self.defaults = patch('edcr.control_room.server.app.load_haul_search_config', return_value={'min_landing_pad': 'large'})
        self.defaults.start()
        self.addCleanup(self.defaults.stop)

    def app(self, **kwargs):
        return server(data_provider=lambda: self.data, market_database_file=self.db,
                      spansh_post=kwargs.pop('spansh_post', unexpected_post), **kwargs)

    def get(self, app, **params):
        with TestClient(app) as client:
            return client.get('/api/cheapest-markets', params={'access_token': TOKEN, 'commodity': 'tritium', **params})

    def test_ship_defaults_and_explicit_filters(self):
        app = self.app()
        result = self.get(app, spansh='0').json()
        self.assertEqual((result['query']['reference_system'], result['query']['pad'], result['query']['min_supply']),
                         ('Sol', 'M', 128))
        self.assertEqual(result['offers'][0]['source'], 'hub')
        self.assertEqual(result['spansh'], {'asked': False, 'count': None, 'error': ''})
        override = self.get(app, spansh='0', system='', radius_ly='', pad='S', min_supply='2000').json()
        self.assertEqual(override['offers'], [])
        self.assertEqual(override['hidden']['supply'], 1)
        self.assertIsNone(override['query']['radius_ly'])

    def test_unknown_ship_uses_configured_pad(self):
        self.data = replace(self.data, ship=replace(self.data.ship, ship_type='new_ship'))
        self.assertEqual(self.get(self.app(), spansh='0').json()['query']['pad'], 'L')

    def test_spansh_merges_and_receives_display_name(self):
        sent = []
        def post(url, body, timeout):
            sent.append(body)
            return {'count': 2, 'results': [{'market_id': 2, 'system_name': 'Sol', 'name': 'Cheap Port',
                'type': 'Coriolis Starport', 'has_large_pad': True, 'distance': 0,
                'market_updated_at': datetime.fromtimestamp(self.now, timezone.utc).isoformat(),
                'market': [{'commodity': 'Tritium', 'buy_price': 900, 'supply': 1000}]}, None]}
        result = self.get(self.app(spansh_post=post)).json()
        self.assertEqual([o['source'] for o in result['offers']], ['spansh', 'hub'])
        self.assertEqual(result['spansh']['count'], 2)
        self.assertEqual(result['spansh']['error'], '1 Spansh rows skipped')
        self.assertEqual(result['total'], 2)
        self.assertEqual(sent[0]['filters']['market'][0]['name'], 'Tritium')

    def test_spansh_failure_keeps_hub_rows(self):
        def offline(url, body, timeout):
            raise OSError('Spansh offline')
        response = self.get(self.app(spansh_post=offline))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['spansh']['error'], 'Spansh offline')
        self.assertEqual(len(response.json()['offers']), 1)

    def test_auth_bad_filters_unknown_system_and_missing_store(self):
        app = self.app()
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/cheapest-markets').status_code, 401)
        self.assertEqual(self.get(app, min_supply='bad').status_code, 400)
        response = self.get(app, spansh='0', system='Unknown')
        self.assertEqual((response.status_code, response.json()['detail']), (404, 'Unknown system'))
        self.assertEqual(self.get(server(spansh_post=unexpected_post), spansh='0').status_code, 404)
        self.assertEqual(app.state.link_handlers[REQUEST_CHEAPEST_MARKETS]([]).status, 400)

    def test_unknown_system_with_spansh_keeps_hub_rows_without_distance(self):
        result = self.get(self.app(spansh_post=lambda *args: {'count': 0, 'results': []}), system='Unknown').json()
        self.assertIsNone(result['offers'][0]['distance_ly'])
        self.assertEqual(result['spansh']['error'], '')

    def test_peer_forwards_resolved_defaults_and_search_timeout_to_hub(self):
        hub = self.app(spansh_post=lambda *args: {'count': 0, 'results': []})
        sent = []
        def request(kind, body, *, timeout_s):
            sent.append((kind, body, timeout_s))
            return hub.state.link_handlers[kind](body)
        link = SimpleNamespace(hello=None, request=request, hub_label='Home hub', search_timeout_s=20, request_timeout_s=5)
        peer = self.app(peer_link=link)
        result = self.get(peer, radius_ly='').json()
        self.assertEqual(result['query']['pad'], 'M')
        self.assertEqual(result['spansh']['error'], '')
        self.assertEqual(sent[0][0], REQUEST_CHEAPEST_MARKETS)
        self.assertEqual(sent[0][1]['min_supply'], '128')
        self.assertEqual(sent[0][1]['radius_ly'], '')
        self.assertEqual(sent[0][2], 20)
        def disconnected(*args, **kwargs):
            raise HubUnreachable('offline')
        link.request = disconnected
        self.assertEqual(self.get(peer).status_code, 502)

    def test_hub_viewed_node_defaults_and_unavailable_state(self):
        nodes = [{'node_id': 'remote', 'name': 'Remote ship', 'connected': True,
                  'state': {'current_system': 'Sol', 'ship': {'type': 'cutter', 'cargo_capacity': 720}}}]
        registry = SimpleNamespace(local=SimpleNamespace(node_id='local'), nodes=lambda: nodes)
        app = self.app(hub_side=SimpleNamespace(registry=registry, relay=None))
        result = self.get(app, node='remote', spansh='0').json()
        self.assertEqual((result['query']['pad'], result['query']['min_supply']), ('L', 720))
        nodes[0]['state'] = {}
        self.assertEqual(self.get(app, node='remote', spansh='0').status_code, 409)
        nodes[0]['connected'] = False
        self.assertEqual(self.get(app, node='remote', spansh='0').status_code, 502)
        self.assertEqual(self.get(app, node='missing', spansh='0').status_code, 502)

    def test_recent_market_display_name_is_sent_to_spansh(self):
        with TemporaryDirectory() as directory:
            recent = Path(directory) / 'recent.json'
            save_recent_markets(recent, (RecentMarket(1, 'Port', 'Sol', 'Coriolis', '',
                ({'Name': '$hydrogenfuel_name;', 'Name_Localised': 'Hydrogen Fuel'},), ''),))
            sent = []
            def post(url, body, timeout):
                sent.append(body)
                return {'count': 0, 'results': []}
            reply = self.app(spansh_post=post, recent_markets_file=recent).state.link_handlers[
                REQUEST_CHEAPEST_MARKETS]({'commodity': 'hydrogenfuel', 'system': 'Sol'})
            self.assertEqual(reply.body['name'], 'Hydrogen Fuel')
            self.assertEqual(sent[0]['filters']['market'][0]['name'], 'Hydrogen Fuel')

    def test_ship_pad_table_covers_known_journal_types(self):
        self.assertEqual(set(SHIP_PAD_SIZES), set(SHIP_TYPE_NAMES))
        for ship, pad in [('Adder', 'S'), ('python', 'M'), (' cutter ', 'L'), ('unknown', '')]:
            self.assertEqual(ship_pad_size(ship), pad)
