from __future__ import annotations

import unittest

from edap.routing.route_cache import RouteCache, RouteRequestKey
from edap.routing.types import Route, RouteWaypoint, SpanshMetadata


def _route(source: str = "A", destination: str = "B") -> Route:
    waypoint = RouteWaypoint(
        system=source,
        star_class=None,
        neutron_boost=False,
        x=0.0, y=0.0, z=0.0,
        ly_from_prev=0.0,
        jumps_from_prev=0,
    )
    return Route(
        waypoints=(waypoint,),
        total_ly=0.0,
        total_jumps=0,
        neutron_count=0,
        source="spansh",
        source_system=source,
        destination_system=destination,
        metadata=SpanshMetadata(efficiency=60, supercharge_multiplier=4, galaxy_map_visits=0),
    )


def _key(**overrides: object) -> RouteRequestKey:
    defaults = dict(
        source_system="A",
        destination_system="B",
        range_ly=60.0,
        efficiency=60,
        supercharge_multiplier=4,
    )
    defaults.update(overrides)
    return RouteRequestKey(**defaults)  # type: ignore[arg-type]


class RouteCacheTests(unittest.TestCase):
    def test_put_and_get_roundtrip(self) -> None:
        cache = RouteCache()
        route = _route()
        route_id = cache.put(route, request_key=_key())
        self.assertIs(cache.get(route_id), route)

    def test_id_stable_for_same_key(self) -> None:
        cache = RouteCache()
        route_id_1 = cache.put(_route(), request_key=_key())
        route_id_2 = cache.put(_route(), request_key=_key())
        self.assertEqual(route_id_1, route_id_2)
        self.assertEqual(len(cache), 1)

    def test_different_key_produces_different_id(self) -> None:
        cache = RouteCache()
        id_a = cache.put(_route(), request_key=_key(range_ly=60.0))
        id_b = cache.put(_route(), request_key=_key(range_ly=65.0))
        self.assertNotEqual(id_a, id_b)
        self.assertEqual(len(cache), 2)

    def test_get_unknown_returns_none(self) -> None:
        self.assertIsNone(RouteCache().get("nope"))

    def test_lru_eviction(self) -> None:
        cache = RouteCache(max_entries=2)
        id_a = cache.put(_route("A"), request_key=_key(source_system="A"))
        id_b = cache.put(_route("B"), request_key=_key(source_system="B"))
        cache.get(id_a)  # touch A so B is oldest
        id_c = cache.put(_route("C"), request_key=_key(source_system="C"))
        self.assertIsNone(cache.get(id_b))
        self.assertIsNotNone(cache.get(id_a))
        self.assertIsNotNone(cache.get(id_c))

    def test_put_existing_id_moves_to_end_and_updates(self) -> None:
        cache = RouteCache(max_entries=2)
        cache.put(_route("A"), request_key=_key(source_system="A"))
        id_b = cache.put(_route("B"), request_key=_key(source_system="B"))
        updated = _route("B", destination="B2")
        cache.put(updated, request_key=_key(source_system="B"))
        cache.put(_route("C"), request_key=_key(source_system="C"))
        self.assertIs(cache.get(id_b), updated)

    def test_max_entries_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            RouteCache(max_entries=0)


if __name__ == "__main__":
    unittest.main()
