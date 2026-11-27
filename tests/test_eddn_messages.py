"""Station services survive relay and local journal parsing."""
import unittest

from edcr.eddn.messages import StationInfo, journal_event_updates, parse_eddn_message
from tests.test_eddn import docked_envelope


class StationServicesMessageTests(unittest.TestCase):
    def test_docked_and_location_normalize_and_deduplicate_all_service_symbols(self):
        for event in ('Docked', 'Location'):
            with self.subTest(event=event):
                envelope = docked_envelope(event=event, Docked=True,
                                          StationServices=['Dock', 'techBroker', 'dock', 'carriervendor'])
                for updates in (parse_eddn_message(envelope), journal_event_updates(envelope['message'])):
                    station = next(update for update in updates if isinstance(update, StationInfo))
                    self.assertEqual(station.services, ('dock', 'techbroker', 'carriervendor'))

    def test_missing_or_invalid_list_is_unknown_but_empty_list_is_known(self):
        cases = [({}, None), ({'StationServices': []}, ()), ({'StationServices': None}, None),
                 ({'StationServices': 'dock'}, None), ({'StationServices': ['dock', 7]}, None)]
        for fields, expected in cases:
            with self.subTest(fields=fields):
                station = next(update for update in parse_eddn_message(docked_envelope(**fields))
                               if isinstance(update, StationInfo))
                self.assertEqual(station.services, expected)

    def test_undocked_location_does_not_publish_station_services(self):
        updates = parse_eddn_message(docked_envelope(event='Location', Docked=False, StationServices=['dock']))
        self.assertFalse(any(isinstance(update, StationInfo) for update in updates))
