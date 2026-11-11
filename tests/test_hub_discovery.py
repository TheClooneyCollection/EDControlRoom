from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from edap.hub.discovery import (
    DiscoveredHub, HubAdvert, KnownHub, NoHubFound, advert_from_record, advert_properties, advertise_address,
)
from edap.hub.peer import PeerLink
from tests.test_hub import HUB_NODE, PEER_NODE, QuietRelay, rig

HOME = HubAdvert(hub_id=HUB_NODE.node_id, name="Home", version="1.0.0", address="192.168.1.20", port=8765)
STRANGER = HubAdvert(hub_id="stranger", name="Other", version="1.0.0", address="192.168.1.30", port=8765)


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.known_file = Path(tmp.name) / ".control_room_known_hub.json"
        self.logs: list[str] = []
        self.dialled: list[str] = []

    def found(self, *hubs: HubAdvert) -> DiscoveredHub:
        return DiscoveredHub(browse=lambda: list(hubs), known=KnownHub(self.known_file, self.logs.append),
                             dial=lambda url: self.dialled.append(url), log=self.logs.append)

    def remember(self, hub_id: str, name: str = "Home") -> None:
        self.known_file.write_text(json.dumps({"hub_id": hub_id, "name": name, "url": ""}), encoding="utf-8")

    def test_the_hub_record_carries_role_id_name_and_version_and_others_are_ignored(self) -> None:
        properties = advert_properties(hub_id="hub-node", name="Home", version="1.0.0")
        self.assertEqual(properties, {"role": "hub", "id": "hub-node", "name": "Home", "version": "1.0.0"})
        self.assertEqual(advert_from_record(properties, "192.168.1.20", 8765),
                         HubAdvert("hub-node", "Home", "1.0.0", "192.168.1.20", 8765))
        self.assertEqual(HOME.url, "http://192.168.1.20:8765")
        for record, address in (({**properties, "role": "peer"}, "192.168.1.20"),
                                ({**properties, "id": ""}, "192.168.1.20"), (properties, "")):
            self.assertIsNone(advert_from_record(record, address, 8765))

    def test_the_hub_advertises_its_lan_bind_address_never_loopback(self) -> None:
        detect = lambda: "192.168.1.20"
        self.assertEqual(advertise_address("192.168.1.42", detect), "192.168.1.42")
        self.assertEqual(advertise_address("0.0.0.0", detect), "192.168.1.20")
        self.assertEqual(advertise_address("127.0.0.1", detect), "")

        def no_lan() -> str:
            raise RuntimeError("could not determine a LAN IPv4 address")

        self.assertEqual(advertise_address("0.0.0.0", no_lan), "")

    def test_a_new_peer_dials_the_only_hub_and_refuses_to_guess_between_two(self) -> None:
        hub = self.found(HOME)
        hub()
        self.assertEqual((self.dialled, hub.url), (["http://192.168.1.20:8765"], "http://192.168.1.20:8765"))
        for found, reason in (((), "no hub found"), ((HOME, STRANGER), "several hubs")):
            with self.subTest(reason=reason), self.assertRaisesRegex(NoHubFound, reason):
                self.found(*found)()

    def test_a_remembered_hub_is_the_only_one_dialled_and_a_stranger_is_warned_about_once(self) -> None:
        self.remember(HUB_NODE.node_id)
        hub = self.found(STRANGER, HOME)
        hub()
        hub()
        self.assertEqual(self.dialled, [HOME.url, HOME.url])
        [warning] = self.logs
        self.assertIn("WARNING: another hub Other", warning)
        self.assertIn(str(self.known_file), warning)
        with self.assertRaisesRegex(NoHubFound, "remembered hub Home not found"):
            self.found(STRANGER)()

    def test_the_first_welcome_is_remembered_and_another_hub_is_refused_until_the_file_is_deleted(self) -> None:
        known = KnownHub(self.known_file, self.logs.append)
        self.assertEqual(known.accept("hub-node", "Home", HOME.url), "")
        self.assertEqual(json.loads(self.known_file.read_text(encoding="utf-8")),
                         {"hub_id": "hub-node", "name": "Home", "url": HOME.url})
        # Kept across restarts; the same hub at a new address is still the same hub.
        known = KnownHub(self.known_file, self.logs.append)
        self.assertEqual(known.accept("hub-node", "Home", "http://192.168.1.21:8765"), "")
        self.assertEqual(known.current()["url"], "http://192.168.1.21:8765")
        refusal = known.accept("stranger", "Other", STRANGER.url)
        self.assertIn("not the remembered hub Home", refusal)
        self.assertIn(f"delete {self.known_file}", refusal)
        self.known_file.unlink()
        self.assertEqual(KnownHub(self.known_file, self.logs.append).accept("stranger", "Other", STRANGER.url), "")

    def test_an_unreadable_remembered_hub_file_refuses_every_hub(self) -> None:
        self.known_file.write_text("{not json", encoding="utf-8")
        known = KnownHub(self.known_file, self.logs.append)
        self.assertIn("unreadable", self.logs[0])
        self.assertIn("not the remembered hub", known.accept("hub-node", "Home", HOME.url))

    def test_a_discovered_peer_links_remembers_the_hub_and_drops_a_hub_lying_about_its_id(self) -> None:
        r = rig(self)
        known = KnownHub(self.known_file, self.logs.append)
        discovered = DiscoveredHub(browse=lambda: [HOME], known=known, dial=lambda url: r.connect(),
                                   log=self.logs.append)
        r.peer = PeerLink(hello=PEER_NODE, hub_url=lambda: discovered.url, outbox=r.outbox, relay=QuietRelay(),
                          connect=discovered, accept_hub=known.accept, now=r.clock, log=r.peer_logs.append,
                          heartbeat_s=30.0, request_timeout_s=10.0, search_timeout_s=180.0)
        self.assertTrue(r.peer.serve(discovered()))
        self.assertEqual(r.peer.status()["url"], HOME.url)
        self.assertEqual(known.current()["hub_id"], HUB_NODE.node_id)

        # A record claiming the remembered id, but the hub that answers is another one.
        self.remember("stranger", "Other")
        known = KnownHub(self.known_file, self.logs.append)
        r.peer = PeerLink(hello=PEER_NODE, hub_url=lambda: HOME.url, outbox=r.outbox, relay=QuietRelay(),
                          connect=r.connect, accept_hub=known.accept, now=r.clock, log=r.peer_logs.append,
                          heartbeat_s=30.0, request_timeout_s=10.0, search_timeout_s=180.0)
        self.assertFalse(r.peer.serve(r.connect()))
        self.assertIn("not the remembered hub Other", r.peer.status()["last_error"])
        self.assertIn("WARNING: not linking to 192.168.1.20:8765", "\n".join(r.peer_logs))


if __name__ == "__main__":
    unittest.main()
