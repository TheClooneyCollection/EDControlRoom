from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from edcr.eddn.routes import TimeModel
from edcr.journal_store import JournalLine, JournalStore
from edcr.trip_time_fit import TripTimeModels, connect_read_only, fit_legs, read_legs, Leg, Stop

DAY = 86400.0
NOW = datetime(2026, 11, 13, 12, tzinfo=timezone.utc).timestamp()
# The pilot's real times, which the configured defaults do not match.
TRUE = TimeModel(docked_s=120.0, travel_base_s=100.0, first_jump_s=200.0, per_extra_jump_s=80.0,
                 supercruise_coeff=10.0, surface_extra_s=50.0)


class Journal:
    """One node's journal, one event per line, with a running clock; `save` writes it into the store."""

    def __init__(self, store: JournalStore, node: str, start: float) -> None:
        self.store, self.node, self.at, self.line = store, node, start, 0
        self.lines: list[JournalLine] = []

    def save(self) -> None:
        self.store.add(self.node, "Journal.2026-11-01T000000.01.log", self.lines)
        self.lines = []

    def event(self, name: str, after_s: float = 0.0, **fields) -> None:
        self.at += after_s
        self.line += 1
        stamp = datetime.fromtimestamp(self.at, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        text = json.dumps({"timestamp": stamp, "event": name, **fields})
        self.lines.append(JournalLine(self.line, text))

    def leg(self, model: TimeModel, jumps: int, dist_ls: float, *, surface: bool = False, extra: str = "") -> None:
        """Undock, fly `jumps` jumps and dock, taking as long as `model` says."""
        self.event("Undocked", model.docked_s)
        for _ in range(jumps):
            self.event("FSDJump", 1)
        if extra:
            self.event(extra, 1)
        self.event("SupercruiseExit", 1)
        flight = model.leg_s(jumps, dist_ls, surface=surface) - model.docked_s
        self.event("Docked", flight - jumps - 1 - bool(extra), DistFromStarLS=dist_ls,
                   StationType="CraterOutpost" if surface else "Coriolis")

    def haul(self, model: TimeModel, legs: int) -> None:
        for i in range(legs):
            self.leg(model, i % 3, (27.0, 125.0, 343.0, 1000.0)[i % 4], surface=i % 2 == 0)


class TripTimeFitTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "journal.sqlite3"
        self.store = JournalStore.open(self.path)
        self.addCleanup(self.store.close)

    def models(self, source: str, clock) -> TripTimeModels:
        return TripTimeModels(configured=TimeModel(), source=source, fit_days=14.0,
                              connect=connect_read_only(self.path), clock=clock)

    def test_fits_each_ship_from_its_own_legs_and_falls_back_to_pooled_then_configured(self) -> None:
        mac = Journal(self.store, "mac", NOW - 20 * DAY)
        mac.event("Loadout", ShipID=7, Ship="panthermkii")
        # Older than the window: not fitted, but the ship flown at its start still counts.
        mac.haul(TimeModel(), 5)
        mac.at = NOW - 3 * DAY
        mac.haul(TRUE, 36)
        # Not plain flights: interdicted, too long, and after a relog.
        mac.leg(TRUE, 1, 100.0, extra="Interdicted")
        mac.leg(TimeModel(travel_base_s=2000.0), 1, 100.0)
        mac.event("Undocked", 30)
        mac.event("LoadGame", 60, ShipID=7)
        mac.event("Docked", 60, DistFromStarLS=10.0, StationType="Coriolis")
        # A second node flies another ship, too little for its own fit.
        forge = Journal(self.store, "forge", NOW - 2 * DAY)
        forge.event("Loadout", ShipID=3, Ship="explorer_nx")
        forge.haul(TimeModel(), 4)
        mac.save()
        forge.save()

        clock = [NOW]
        models = self.models("fitted", lambda: clock[0])
        own = models.active(7)
        self.assertEqual((own.scope, own.ship_id, own.legs), ("ship", 7, 36))
        for name in ("travel_base_s", "first_jump_s", "per_extra_jump_s", "supercruise_coeff", "surface_extra_s"):
            self.assertAlmostEqual(getattr(own.model, name), getattr(TRUE, name), delta=1.0, msg=name)
        # 35 stops between the 36 legs, and the stops before the three dropped legs still count.
        self.assertEqual((own.model.docked_s, own.stops), (120.0, 38))
        self.assertEqual(own.model.unknown_dist_ls, TimeModel().unknown_dist_ls)

        pooled = models.active(3)
        self.assertEqual((pooled.scope, pooled.legs), ("pooled", 40))
        self.assertEqual(models.payload(3)["active"]["scope"], "pooled")
        self.assertEqual(models.active(None).scope, "pooled")
        # The configured set ignores the fit.
        self.assertEqual(self.models("config", lambda: NOW).active(7).model, TimeModel())

        # Cached for a minute: new legs show after that.
        forge.at = NOW
        forge.haul(TimeModel(), 1)
        forge.save()
        clock[0] = NOW + 30
        self.assertEqual(models.active(3).legs, 40)
        clock[0] = NOW + 61
        self.assertEqual(models.active(3).legs, 41)

        # Twenty days on, the window holds too few legs for any fit.
        late = self.models("fitted", lambda: NOW + 20 * DAY).active(7)
        self.assertEqual((late.scope, late.model), ("config", TimeModel()))

    def test_fields_without_enough_legs_keep_their_configured_value(self) -> None:
        # Only one-jump legs to orbital stations: the jump and the base cannot be told apart.
        legs = [Leg(1, TRUE.leg_s(1, ls, surface=False) - TRUE.docked_s, 1, ls, False)
                for ls in (27.0, 125.0, 343.0, 1000.0) * 10]
        # One stray leg, five minutes slow, is dropped before the second fit.
        legs.append(Leg(1, 900.0, 1, 125.0, False))
        model, fitted, support, kept = fit_legs(legs, [Stop(1, 100.0)] * 9, TimeModel())
        self.assertEqual(fitted, ("first_jump_s", "supercruise_coeff"))
        self.assertEqual((support["travel_base_s"], support["docked_s"], kept), (0, 9, 40))
        configured = TimeModel()
        for name in ("docked_s", "travel_base_s", "per_extra_jump_s", "surface_extra_s"):
            self.assertEqual(getattr(model, name), getattr(configured, name))
        # The base stays configured, so the first jump takes up the rest of the true base.
        self.assertAlmostEqual(model.first_jump_s, TRUE.first_jump_s + TRUE.travel_base_s - configured.travel_base_s,
                               delta=1.0)
        self.assertAlmostEqual(model.supercruise_coeff, TRUE.supercruise_coeff, delta=0.1)

    def test_reads_nothing_from_a_store_without_events(self) -> None:
        self.assertEqual(read_legs(self.store._db, 0.0), ([], []))
        missing = TripTimeModels(configured=TimeModel(), source="fitted", fit_days=14.0,
                                 connect=connect_read_only(self.path.with_name("none.sqlite3")), clock=lambda: NOW)
        self.assertEqual(missing.active(7).scope, "config")


if __name__ == "__main__":
    unittest.main()
