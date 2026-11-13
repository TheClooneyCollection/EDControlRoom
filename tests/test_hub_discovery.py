from __future__ import annotations

import ipaddress
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from edcr.hub.discovery import (
    DiscoveredHub, HubAdvert, KnownHub, NoHubFound, advert_from_record, advert_properties, advertise_address,
    bind_hosts, dnssd_browse, lan_hosts,
)
from edcr.platform.lan import hostname_interfaces, ifconfig_interfaces, preferred_addresses
from edcr.hub.peer import PeerLink
from tests.test_hub import HUB_NODE, PEER_NODE, QuietRelay, rig

HOME = HubAdvert(hub_id=HUB_NODE.node_id, name="Home", version="1.0.0", addresses=("192.168.1.20",), port=8765)
STRANGER = HubAdvert(hub_id="stranger", name="Other", version="1.0.0", addresses=("192.168.1.30",), port=8765)
# A hub on Ethernet (default route) and Wi-Fi, two subnets.
TWO_NETWORKS = HubAdvert(hub_id=HUB_NODE.node_id, name="Home", version="1.0.0",
                         addresses=("192.168.2.8", "192.168.1.128"), port=8765)
WIFI_PEER = [ipaddress.IPv4Interface("127.0.0.1/8"), ipaddress.IPv4Interface("192.168.1.40/24")]


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.known_file = Path(tmp.name) / ".control_room_known_hub.json"
        self.logs: list[str] = []
        self.dialled: list[str] = []

    def found(self, *hubs: HubAdvert, local: list[ipaddress.IPv4Interface] = WIFI_PEER) -> DiscoveredHub:
        return DiscoveredHub(browse=lambda: list(hubs), known=KnownHub(self.known_file, self.logs.append),
                             dial=lambda url: self.dialled.append(url), local_interfaces=lambda: local,
                             log=self.logs.append)

    def remember(self, hub_id: str, name: str = "Home") -> None:
        self.known_file.write_text(json.dumps({"hub_id": hub_id, "name": name, "url": ""}), encoding="utf-8")

    def test_the_hub_record_carries_role_id_name_and_version_and_others_are_ignored(self) -> None:
        properties = advert_properties(hub_id="hub-node", name="Home", version="1.0.0")
        self.assertEqual(properties, {"role": "hub", "id": "hub-node", "name": "Home", "version": "1.0.0"})
        self.assertEqual(advert_from_record(properties, ["192.168.1.20"], 8765),
                         HubAdvert("hub-node", "Home", "1.0.0", ("192.168.1.20",), 8765))
        self.assertEqual(HOME.url, "http://192.168.1.20:8765")
        self.assertEqual(advert_from_record(properties, ["192.168.2.8", "", "192.168.1.128", "192.168.2.8"],
                                            8765).addresses, ("192.168.2.8", "192.168.1.128"))
        for record, addresses in (({**properties, "role": "peer"}, ["192.168.1.20"]),
                                  ({**properties, "id": ""}, ["192.168.1.20"]), (properties, []),
                                  (properties, [""])):
            self.assertIsNone(advert_from_record(record, addresses, 8765))

    def test_a_lan_bound_server_also_listens_on_loopback_unless_turned_off(self) -> None:
        self.assertEqual(bind_hosts(["192.168.1.42"], True), ["192.168.1.42", "127.0.0.1"])
        self.assertEqual(bind_hosts(["192.168.1.42"], False), ["192.168.1.42"])
        self.assertEqual(bind_hosts(["127.0.0.1"], True), ["127.0.0.1"])
        self.assertEqual(bind_hosts(["0.0.0.0"], True), ["0.0.0.0"])

    def test_a_lan_server_on_two_networks_listens_on_both_and_loopback(self) -> None:
        # The detected host stays first; the other interfaces follow once each.
        hosts = lan_hosts("192.168.2.8", ["192.168.2.8", "192.168.1.128"])
        self.assertEqual(hosts, ["192.168.2.8", "192.168.1.128"])
        self.assertEqual(bind_hosts(hosts, True), ["192.168.2.8", "192.168.1.128", "127.0.0.1"])
        # `lan_all_interfaces = false` passes no others.
        self.assertEqual(lan_hosts("192.168.2.8", []), ["192.168.2.8"])

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

    def test_a_peer_dials_a_hub_on_two_networks_on_its_own_subnet_first(self) -> None:
        hub = self.found(TWO_NETWORKS)
        hub()
        self.assertEqual((self.dialled, hub.url), (["http://192.168.1.128:8765"], "http://192.168.1.128:8765"))
        # On neither subnet (a routed or VPN peer): the record's order, the hub's default route first.
        self.dialled.clear()
        self.found(TWO_NETWORKS, local=[ipaddress.IPv4Interface("10.0.0.5/24")])()
        self.assertEqual(self.dialled, ["http://192.168.2.8:8765"])

    def test_an_unreachable_hub_address_falls_back_to_the_next_and_the_last_failure_is_raised(self) -> None:
        refused: set[str] = {"http://192.168.1.128:8765"}

        def dial(url: str) -> str:
            self.dialled.append(url)
            if url in refused:
                raise OSError("connection refused")
            return url

        hub = DiscoveredHub(browse=lambda: [TWO_NETWORKS], known=KnownHub(self.known_file, self.logs.append),
                            dial=dial, local_interfaces=lambda: WIFI_PEER, log=self.logs.append)
        self.assertEqual(hub(), "http://192.168.2.8:8765")
        self.assertEqual(self.dialled, ["http://192.168.1.128:8765", "http://192.168.2.8:8765"])
        self.assertEqual(hub.url, "http://192.168.2.8:8765")
        self.assertIn("not reachable at http://192.168.1.128:8765 (connection refused)", self.logs[0])
        refused.add("http://192.168.2.8:8765")
        with self.assertRaisesRegex(OSError, "connection refused"):
            hub()
        self.assertEqual(hub.url, "http://192.168.2.8:8765")

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
                                   local_interfaces=lambda: WIFI_PEER, log=self.logs.append)
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


# Recorded from macOS `dns-sd` against local adverts, with host names and addresses made generic.
DNSSD_BROWSE = """Browsing for _edcr._tcp.local
DATE: ---Wed 11 Nov 2026---
14:27:11.445  ...STARTING...
Timestamp     A/R    Flags  if Domain               Service Type         Instance Name
14:27:11.446  Add        3  14 local.               _edcr._tcp.          Gone Hub
14:27:11.446  Add        3   1 local.               _edcr._tcp.          Desk Hub
14:27:11.446  Add        3  14 local.               _edcr._tcp.          Desk Hub
14:27:11.446  Add        3  14 local.               _edcr._tcp.          Silent Hub
14:27:11.446  Add        2  14 local.               _edcr._tcp.          Not A Hub
14:27:12.101  Rmv        0  14 local.               _edcr._tcp.          Gone Hub
"""
DNSSD_LOOKUPS = {
    "Desk Hub": """Lookup Desk Hub._edcr._tcp.local
DATE: ---Wed 11 Nov 2026---
14:27:09.935  ...STARTING...
14:27:09.935  Desk\\032Hub._edcr._tcp.local. can be reached at hub-host.local.:8765 (interface 14) Flags: 1
 role=hub id=hub-node name=Café\\ Desk\\\\1 note=a=b\\x07 version=1.2.3
""",
    "Not A Hub": """Lookup Not A Hub._edcr._tcp.local
14:27:09.935  Not\\032A\\032Hub._edcr._tcp.local. can be reached at other-host.local.:9000 (interface 14)
 role=peer id=peer-node
""",
    "Silent Hub": """Lookup Silent Hub._edcr._tcp.local
DATE: ---Wed 11 Nov 2026---
14:27:09.935  ...STARTING...
""",
}
DNSSD_ADDRESSES = """DATE: ---Wed 11 Nov 2026---
14:26:36.947  ...STARTING...
Timestamp     A/R  Flags         IF  Hostname                               Address                                      TTL
14:26:36.947  Add  40000003       1  hub-host.local.                        127.0.0.1                                    4500
14:26:36.947  Add  40000002      14  hub-host.local.                        192.168.1.20                                 4500
"""


DNSSD_TWO_ADDRESSES = """DATE: ---Fri 13 Nov 2026---
14:26:36.947  ...STARTING...
Timestamp     A/R  Flags         IF  Hostname                               Address                                      TTL
14:26:36.947  Add  40000003      15  hub-host.local.                        192.168.2.8                                 120
14:26:36.947  Add  40000002      14  hub-host.local.                        192.168.1.128                                120
"""


class DnssdBrowseTests(unittest.TestCase):
    def test_a_mac_peer_finds_hubs_through_dns_sd_and_resolves_their_lan_address(self) -> None:
        runs: list[tuple[list[str], float, bool]] = []

        def run(args: list[str], seconds: float, done) -> str:
            output = {"-B": DNSSD_BROWSE, "-L": DNSSD_LOOKUPS.get(args[2], ""), "-G": DNSSD_ADDRESSES}[args[1]]
            runs.append((args, seconds, done(output)))
            return output

        found = dnssd_browse(3.0, run)()
        self.assertEqual(found, [HubAdvert("hub-node", "Café Desk\\1", "1.2.3", ("192.168.1.20",), 8765)])
        # The browse listens for its whole window; a lookup or address stops as soon as it has answered,
        # and one that never answers (Silent Hub) runs out its deadline and is skipped.
        self.assertEqual(runs, [
            (["dns-sd", "-B", "_edcr._tcp", "local"], 3.0, False),
            (["dns-sd", "-L", "Desk Hub", "_edcr._tcp", "local"], 3.0, True),
            (["dns-sd", "-G", "v4", "hub-host.local."], 3.0, True),
            (["dns-sd", "-L", "Silent Hub", "_edcr._tcp", "local"], 3.0, False),
            (["dns-sd", "-L", "Not A Hub", "_edcr._tcp", "local"], 3.0, True),
            (["dns-sd", "-G", "v4", "other-host.local."], 3.0, True),
        ])

    def test_a_hub_on_two_networks_resolves_to_both_addresses_once_dns_sd_has_sent_them_all(self) -> None:
        stops: list[bool] = []

        def run(args: list[str], seconds: float, done) -> str:
            output = {"-B": DNSSD_BROWSE, "-L": DNSSD_LOOKUPS.get(args[2], ""), "-G": DNSSD_TWO_ADDRESSES}[args[1]]
            if args[1] == "-G":
                # Not done after the first row: its flags say more rows are coming.
                partial = "\n".join(output.splitlines()[:4])
                stops.extend([done(partial), done(output)])
            return output

        [hub] = dnssd_browse(3.0, run)()
        self.assertEqual(hub.addresses, ("192.168.2.8", "192.168.1.128"))
        self.assertEqual(stops, [False, True, False, True])

    def test_no_dns_sd_output_finds_no_hub(self) -> None:
        self.assertEqual(dnssd_browse(3.0, lambda args, seconds, done: "")(), [])


# Recorded from macOS `ifconfig`, trimmed and with generic addresses; then Linux net-tools.
IFCONFIG_MAC = """lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
\tinet 127.0.0.1 netmask 0xff000000
\tinet6 ::1 prefixlen 128
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 192.168.1.128 netmask 0xffffff00 broadcast 192.168.1.255
utun4: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1280
\tinet 100.100.1.2 --> 100.100.1.2 netmask 0xffffffff
en11: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 192.168.2.8 netmask 0xffffff00 broadcast 192.168.2.255
"""
IFCONFIG_LINUX = """eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 10.0.0.12  netmask 255.255.0.0  broadcast 10.0.255.255
"""


class LocalInterfaceTests(unittest.TestCase):
    def test_ifconfig_lists_each_ipv4_address_with_its_subnet(self) -> None:
        self.assertEqual([str(interface) for interface in ifconfig_interfaces(IFCONFIG_MAC)],
                         ["127.0.0.1/8", "192.168.1.128/24", "100.100.1.2/32", "192.168.2.8/24"])
        self.assertEqual([str(interface) for interface in ifconfig_interfaces(IFCONFIG_LINUX)], ["10.0.0.12/16"])

    def test_windows_host_name_addresses_are_assumed_to_sit_on_a_slash_24(self) -> None:
        self.assertEqual([str(interface) for interface in hostname_interfaces(["192.168.1.40", "192.168.1.40", "x"])],
                         ["192.168.1.40/24"])

    def test_a_single_address_needs_no_interface_lookup_and_loopback_is_no_shared_subnet(self) -> None:
        def no_lookup() -> list[ipaddress.IPv4Interface]:
            raise AssertionError("looked up interfaces for one address")

        self.assertEqual(preferred_addresses(["192.168.1.20"], no_lookup), ["192.168.1.20"])
        self.assertEqual(preferred_addresses(["192.168.2.8", "127.0.0.1"],
                                             lambda: [ipaddress.IPv4Interface("127.0.0.1/8")]),
                         ["192.168.2.8", "127.0.0.1"])
