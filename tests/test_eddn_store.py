"""Services have their own freshness clock across live updates and snapshots."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from edcr.ardent import ArdentLookup
from edcr.eddn.messages import StationInfo, StationTypeSeen, parse_eddn_message
from edcr.eddn.store import EddnStore
from tests.test_eddn import docked_envelope


class StationServicesStoreTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.store = EddnStore(self.db)
        self.addCleanup(self.store.close)
        self.station = StationInfo(1, 7, 'Sol', 'Port', 'Ocellus', 50, 'L', 100, ('dock', 'shipyard'))

    def services(self, market_id=1):
        return self.db.execute('SELECT service FROM station_service WHERE market_id=? ORDER BY service',
                               (market_id,)).fetchall()

    def test_listener_open_upgrades_v1_without_a_manual_migration(self):
        self.db.executescript('DROP TABLE station_service; DROP TABLE station_services_seen;')
        EddnStore(self.db)
        self.assertEqual(self.db.execute('PRAGMA user_version').fetchone(), (1,))
        for event in ('Docked', 'Location'):
            self.store.save(parse_eddn_message(docked_envelope(event=event, Docked=True, MarketID=1,
                                                              StationServices=['techBroker', 'Dock', 'dock'])))
            self.assertEqual(self.services(), [('dock',), ('techbroker',)])

    def test_newest_services_replace_the_whole_list_and_empty_clears_it(self):
        self.store.apply(self.station)
        self.assertFalse(self.store.apply(replace(self.station, timestamp=99, services=('outfitting',))))
        self.assertEqual(self.services(), [('dock',), ('shipyard',)])
        self.assertTrue(self.store.apply(replace(self.station, timestamp=101, services=('Dock', 'dock'))))
        self.assertEqual(self.services(), [('dock',)])
        self.store.apply(replace(self.station, timestamp=101, services=()))
        self.assertEqual(self.services(), [])
        self.assertEqual(self.db.execute('SELECT updated_at FROM station_services_seen').fetchone(), (101,))

    def test_ardent_and_station_type_updates_preserve_services_and_their_clock(self):
        self.store.apply(self.station)
        rows = [{'marketId': 1, 'systemAddress': 7, 'systemName': 'Sol', 'stationName': 'Port',
                 'stationType': 'Coriolis', 'updatedAt': '2026-11-27T00:00:00Z'}]
        lookup = ArdentLookup(lambda url, timeout: rows, now=lambda: 0, save=self.store.save,
                              log=lambda message: None)
        self.assertEqual(lookup(1, 'Port', 'Sol').station_type, 'Coriolis')
        self.assertEqual(self.services(), [('dock',), ('shipyard',)])
        self.assertTrue(self.store.apply(replace(self.station, timestamp=101, services=('outfitting',))))
        self.assertEqual(self.services(), [('outfitting',)])
        self.assertEqual(self.db.execute('SELECT type FROM station').fetchone(), ('Coriolis',))
        self.store.apply(StationTypeSeen(1, 'Sol', 'Port', 'Outpost', 2_000_000_000))
        self.assertEqual(self.services(), [('outfitting',)])
        self.assertEqual(self.db.execute('SELECT updated_at FROM station_services_seen').fetchone(), (101,))

    def test_missing_list_and_market_pruning_leave_services_intact(self):
        self.store.apply(self.station)
        self.store.apply(replace(self.station, timestamp=101, services=None))
        self.store.prune(older_than=200)
        self.assertEqual(self.services(), [('dock',), ('shipyard',)])
        self.assertEqual(self.db.execute('SELECT updated_at FROM station_services_seen').fetchone(), (100,))

    def test_v1_snapshot_without_service_tables_still_imports(self):
        self.store.apply(self.station)
        with TemporaryDirectory() as directory, closing(sqlite3.connect(':memory:')) as source:
            snapshot = EddnStore(source)
            snapshot.save([replace(self.station, timestamp=200, type='Coriolis', services=None)])
            source.executescript('DROP TABLE station_service; DROP TABLE station_services_seen;')
            path = Path(directory) / 'old.sqlite3'
            path.write_bytes(source.serialize())
            result = self.store.import_database(path, min_updated_at=0)
        self.assertEqual((result.stations, result.services), (1, 0))
        self.assertEqual(self.services(), [('dock',), ('shipyard',)])

    def test_snapshot_merges_only_newer_service_lists_including_empty_and_new_stations(self):
        self.store.save([replace(self.station, market_id=mid) for mid in range(1, 5)])
        # Station metadata is newer than service data; it must not block services import.
        self.store.apply(replace(self.station, timestamp=300, services=None))
        with TemporaryDirectory() as directory, closing(sqlite3.connect(':memory:')) as source:
            snapshot = EddnStore(source)
            snapshot.save([replace(self.station, timestamp=101, services=('repair',)),
                           replace(self.station, market_id=2, timestamp=99, services=('repair',)),
                           replace(self.station, market_id=3, timestamp=100, services=('repair',)),
                           replace(self.station, market_id=4, timestamp=101, services=()),
                           replace(self.station, market_id=5, timestamp=50, services=('refuel',))])
            path = Path(directory) / 'new.sqlite3'
            path.write_bytes(source.serialize())
            result = self.store.import_database(path, min_updated_at=1000)
            self.assertEqual(result.services, 3)
            self.assertEqual(self.store.import_database(path, min_updated_at=1000).services, 0)
        self.assertEqual(self.services(), [('repair',)])
        self.assertEqual(self.services(2), [('dock',), ('shipyard',)])
        self.assertEqual(self.services(3), [('dock',), ('shipyard',)])
        self.assertEqual(self.services(4), [])
        self.assertEqual(self.services(5), [('refuel',)])
        self.assertEqual(self.db.execute('SELECT updated_at FROM station WHERE market_id=1').fetchone(), (300,))

    def test_broken_services_snapshot_rolls_back_other_imported_facts(self):
        self.store.apply(self.station)
        with TemporaryDirectory() as directory, closing(sqlite3.connect(':memory:')) as source:
            snapshot = EddnStore(source)
            snapshot.save([replace(self.station, timestamp=200, type='Coriolis')])
            source.execute('DROP TABLE station_service')
            source.commit()
            path = Path(directory) / 'broken.sqlite3'
            path.write_bytes(source.serialize())
            with self.assertRaises(sqlite3.OperationalError):
                self.store.import_database(path, min_updated_at=0)
            self.assertEqual(self.db.execute('SELECT type FROM station').fetchone(), ('Ocellus',))
            self.assertEqual(self.services(), [('dock',), ('shipyard',)])
