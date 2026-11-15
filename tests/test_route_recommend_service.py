from dataclasses import replace
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from edcr.control_room.server.recommendations import recommendation_inputs, query_recommendations, estimate_selected_route
from edcr.eddn.routes import TimeModel
from edcr.eddn.store import EddnStoreCounts
from edcr.route_recommend import RouteRecommendSettings
from edcr.route_recommend_service import RecommendationLoop
from tests.test_eddn_routes import galaxy, NOW
from tests.test_route_recommend import recommendations, row


def inputs():
    return recommendation_inputs('local', SimpleNamespace(ship=SimpleNamespace(
        system='Sol', ship_id=7, cargo_capacity=100, laden_jump_range_ly=5)),
        selected_route=None, search_defaults={}, time_model=TimeModel(), connection='local')


class RecommendationServiceTests(unittest.TestCase):
    def test_changed_store_and_inputs_search_once_per_check_and_retry_failed_delivery(self):
        now, newest, nodes = [0], [100], [inputs()]
        searches, delivered, logs = [], [], []
        accept = [True]
        def query(node, clock):
            searches.append((node, clock))
            return recommendations([row()])
        def deliver(node, result):
            delivered.append(node)
            return accept[0]
        loop = RecommendationLoop(settings=RouteRecommendSettings(), time_fn=lambda: now[0],
            store_counts=lambda: EddnStoreCounts(0, 0, 0, 0, None, newest[0]), node_inputs=lambda: nodes,
            run_query=query, deliver=deliver, log=logs.append)
        loop.check()
        now[0] = 299
        newest[0] = 101
        loop.check()
        self.assertEqual(len(searches), 1)
        now[0] = 300
        loop.check()
        now[0] = 600
        loop.check()
        self.assertEqual(len(searches), 2)
        for field, value in [('capacity', 200), ('laden_jump_range_ly', 30), ('ship_id', 8),
                             ('current_system', 'Alpha'), ('selected_route', row()['trade_route'])]:
            nodes[0] = replace(nodes[0], **{field: value})
            now[0] += 300
            loop.check()
        self.assertEqual(len(searches), 7)
        accept[0] = False
        newest[0] += 1
        now[0] += 300
        loop.check()
        accept[0] = True
        now[0] += 300
        loop.check()
        self.assertEqual(len(searches), 9)
        self.assertEqual(logs, [])

    def test_selection_change_during_search_never_delivers_stale_gains(self):
        nodes, delivered = [inputs()], []
        def query(node, now):
            nodes[0] = replace(node, selected_route=row()['trade_route'])
            return recommendations([row()])
        loop = RecommendationLoop(settings=RouteRecommendSettings(), time_fn=lambda: 0,
            store_counts=lambda: EddnStoreCounts(0, 0, 0, 0, None, 1), node_inputs=lambda: nodes,
            run_query=query, deliver=lambda node, result: delivered.append(result), log=self.fail)
        loop.check()
        self.assertEqual(delivered, [])

    def test_actual_search_uses_ship_range_hold_model_and_global_cap(self):
        store = galaxy()
        self.addCleanup(store.close)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'markets.db'
            db = sqlite3.connect(path)
            store._db.backup(db)
            db.close()
            node = inputs()
            result = query_recommendations(node, settings=RouteRecommendSettings(max_route_ly=20),
                database_file=path, display_names={'gold': 'Gold', 'silver': 'Silver'}, now=NOW)
            self.assertEqual(len(result.routes), 1)
            route = result.routes[0]
            self.assertEqual(route['jumps'], 2)
            self.assertEqual(route['outbound']['tons'], 100)
            slower = query_recommendations(replace(node, time_model=TimeModel(docked_s=900)),
                settings=RouteRecommendSettings(max_route_ly=20), database_file=path,
                display_names={'gold': 'Gold', 'silver': 'Silver'}, now=NOW)
            self.assertLess(slower.routes[0]['profit_per_hour'], route['profit_per_hour'])
            baseline = estimate_selected_route(store._db, route['trade_route'], capacity=100,
                                              laden_range=5, time_model=node.time_model)
            self.assertAlmostEqual(baseline.cr_h, route['profit_per_hour'], delta=1000)
            missing = estimate_selected_route(store._db, {**route['trade_route'], 'source_buy_commodity': 'Missing'},
                                             capacity=100, laden_range=5, time_model=node.time_model)
            self.assertIsNone(missing.cr_h)
            self.assertIn('Missing buy/sell prices', missing.missing)
        self.assertIsNone(recommendation_inputs('x', SimpleNamespace(), selected_route=None,
            search_defaults={}, time_model=TimeModel(), connection='local'))
