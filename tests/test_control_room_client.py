from __future__ import annotations

import unittest

from edap.control_room.client.connect import parse_observer_server_target


class ControlRoomClientTests(unittest.TestCase):
    def test_parse_target_defaults_to_http_and_default_port(self) -> None:
        target = parse_observer_server_target("192.168.1.44")

        self.assertEqual(target.host, "192.168.1.44")
        self.assertEqual(target.port, 8765)
        self.assertEqual(target.http_base_url, "http://192.168.1.44:8765")
        self.assertEqual(target.websocket_url, "ws://192.168.1.44:8765/session")

    def test_parse_target_keeps_explicit_https_port(self) -> None:
        target = parse_observer_server_target("https://bridge.local:9443")

        self.assertEqual(target.host, "bridge.local")
        self.assertEqual(target.port, 9443)
        self.assertEqual(target.http_base_url, "https://bridge.local:9443")
        self.assertEqual(target.websocket_url, "wss://bridge.local:9443/session")


if __name__ == "__main__":
    unittest.main()
