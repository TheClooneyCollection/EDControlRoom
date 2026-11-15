from dataclasses import replace
import json
import unittest

from edcr.route_recommend import BaselineEstimate, RouteRecommendations, RouteRecommendSettings, recommend, route_key


def row(name="A", cr_h=100_000_000, *, known=True):
    trade = dict(from_station=name, from_system="Sol", to_station="B", to_system="Achenar",
                 source_buy_commodity="Gold", target_buy_commodity="Silver")
    return dict(station_1=dict(station=name, system="Sol"), station_2=dict(station="B", system="Achenar"),
                trade_route=trade if known else None, outbound={"name": "Gold"}, inbound={"name": "Silver"},
                profit_per_hour=cr_h, trip_s=600)


def unexpected_baseline(route):
    raise AssertionError("baseline estimator should not be needed")


def recommendations(rows, *, selected=None, estimate=unexpected_baseline, **settings):
    return recommend({"routes": rows}, selected_route=selected, estimate_baseline=estimate,
                     settings=replace(RouteRecommendSettings(), **settings), generated_at=123)


class RecommendationTests(unittest.TestCase):
    def test_both_thresholds_are_required_and_boundaries_qualify(self):
        for baseline, candidate, qualifies in ((100e6, 115e6, False), (200e6, 220e6, False),
                                                (100e6, 120e6, True), (200e6, 230e6, True)):
            with self.subTest(baseline=baseline, candidate=candidate):
                selected = row(cr_h=baseline)
                result = recommendations([selected, row("C", candidate)], selected=selected["trade_route"])
                self.assertEqual(len(result.routes), int(qualifies))
                self.assertEqual(result.below_threshold, int(not qualifies))
                self.assertEqual((result.baseline_cr_h, result.baseline_source), (baseline, "search"))

    def test_no_selection_lists_best_routes_up_to_cap(self):
        result = recommendations([row("C", 150e6), row(), row("D", 200e6)], list_cap=2)
        self.assertEqual([r["profit_per_hour"] for r in result.routes], [200e6, 150e6])
        self.assertEqual((result.below_threshold, result.baseline_cr_h, result.baseline_source), (0, None, "none"))

    def test_selected_pair_matches_ignoring_direction_case_and_whitespace(self):
        selected = dict(from_station=" b ", from_system="ACHENAR", to_station=" a ", to_system=" sol ")
        result = recommendations([row(), row("C", 130e6)], selected=selected)
        self.assertEqual(len(result.routes), 1)
        self.assertEqual(result.baseline_cr_h, 100e6)
        self.assertEqual(result.below_threshold, 0)

    def test_fallback_estimates_selected_route_when_pair_is_outside_search(self):
        selected = row()["trade_route"]
        estimates = {route_key(selected): BaselineEstimate(100e6, "store", ())}
        result = recommendations([row("C", 130e6)], selected=selected,
                                 estimate=lambda route: estimates[route_key(route)])
        self.assertEqual((result.baseline_cr_h, result.baseline_source), (100e6, "store"))
        self.assertEqual(len(result.routes), 1)

    def test_missing_baseline_keeps_top_routes_and_reason(self):
        result = recommendations([row("C", 1)], selected=row()["trade_route"],
                                 estimate=lambda route: BaselineEstimate(None, "unpriced", ("station distance",)))
        self.assertEqual(len(result.routes), 1)
        self.assertEqual(result.baseline_missing, ("station distance",))
        self.assertIsNone(result.baseline_cr_h)

    def test_counts_unknown_names_only_after_threshold_and_excludes_selected_pair(self):
        result = recommendations([row(known=False), row("C", 110e6, known=False),
                                  row("D", 130e6, known=False), row("E", 140e6)],
                                 selected=row()["trade_route"])
        self.assertEqual((result.below_threshold, result.name_unknown, len(result.routes)), (1, 1, 1))

    def test_payload_round_trip_preserves_rows_and_does_not_alias_search(self):
        original = row()
        result = recommendations([original])
        decoded = RouteRecommendations.from_payload(json.loads(json.dumps(result.to_payload())))
        self.assertEqual(decoded, result)
        self.assertEqual(decoded.searched_limit, 200)
        self.assertEqual(decoded.generated_at, 123)
        self.assertEqual(decoded.routes[0]["key"], route_key(original["trade_route"]))
        decoded.routes[0].pop("key")
        self.assertEqual(decoded.routes[0], original)
        decoded.routes[0]["outbound"]["name"] = "Changed"
        self.assertEqual(result.routes[0]["outbound"]["name"], "Gold")
        self.assertEqual(original["outbound"]["name"], "Gold")

    def test_key_is_stable_but_distinguishes_system_and_commodity(self):
        trade = row()["trade_route"]
        reversed_trade = dict(from_station=" b ", from_system="ACHENAR", to_station="a", to_system="sol",
                              source_buy_commodity="silver", target_buy_commodity="gold")
        self.assertEqual(route_key(trade), route_key(reversed_trade))
        for field in ("from_system", "to_system", "source_buy_commodity", "target_buy_commodity"):
            self.assertNotEqual(route_key(trade), route_key({**trade, field: "Other"}))

    def test_empty_search_has_zero_counts(self):
        result = recommendations([])
        self.assertEqual((result.routes, result.below_threshold, result.name_unknown), ([], 0, 0))
