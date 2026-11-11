"""Finding the hub on the LAN: the hub advertises `_edcr._tcp.local` over mDNS, a peer without
`[hub] url` browses for it.

The peer remembers the hub it first linked to (`KnownHub`, saved next to the config) and from then
on dials only that hub, so a stray advertiser on the LAN cannot quietly take over. Browsing and
advertising are plain functions (`zeroconf_browse`, `dnssd_browse`, `zeroconf_advertise`), so tests use
fakes. On macOS the peer browses with the system `dns-sd` tool: mDNSResponder already owns the mDNS port
and answers it, while Python's own multicast socket may receive nothing without Local Network permission.
"""
from __future__ import annotations

import json
import os
import re
import select
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from edap.hub.protocol import LinkConnection

SERVICE_TYPE = "_edcr._tcp.local."
# The remembered hub lives next to the config, beside the node id; delete it to pick another hub.
KNOWN_HUB_FILE_NAME = ".control_room_known_hub.json"
# How long one browse listens for hubs before the peer picks one.
BROWSE_S = 3.0


@dataclass(frozen=True)
class HubAdvert:
    """One hub found on the LAN, from its mDNS record."""

    hub_id: str
    name: str
    version: str
    address: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{self.address}:{self.port}"


class NoHubFound(OSError):
    """Browsing found no hub this peer may link to; the link redials later."""


def advert_properties(*, hub_id: str, name: str, version: str) -> dict[str, str]:
    """The TXT record a hub advertises."""
    return {"role": "hub", "id": hub_id, "name": name, "version": version}


def advert_from_record(properties: dict[str, str], address: str, port: int) -> HubAdvert | None:
    """A hub from one resolved mDNS record; None for anything that is not an EDCR hub."""
    if properties.get("role") != "hub" or not properties.get("id") or not address or not port:
        return None
    return HubAdvert(hub_id=properties["id"], name=properties.get("name") or properties["id"],
                     version=properties.get("version", ""), address=address, port=port)


class KnownHub:
    """The hub this peer linked to first: its id, name and last address, kept in a small JSON file."""

    def __init__(self, path: Path, log: Callable[[str], None]) -> None:
        self.path = path
        self._log = log
        self._lock = threading.Lock()
        self._hub = self._read()

    def _read(self) -> dict[str, str] | None:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            # Never fall back to "any hub": a broken file keeps the peer away until the user fixes it.
            self._log(f"WARNING: remembered hub file {self.path} is unreadable ({exc}); "
                      "delete it to link to the hub found on the LAN")
            return {"hub_id": "", "name": "unreadable file", "url": ""}
        if not isinstance(value, dict) or not isinstance(value.get("hub_id"), str):
            self._log(f"WARNING: remembered hub file {self.path} is not a hub record; delete it to pick a hub again")
            return {"hub_id": "", "name": "unreadable file", "url": ""}
        return {key: str(value.get(key) or "") for key in ("hub_id", "name", "url")}

    def _save(self, hub: dict[str, str]) -> None:
        self._hub = hub
        try:
            self.path.write_text(json.dumps(hub, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            self._log(f"Warning: could not save the remembered hub to {self.path}: {exc}")

    def current(self) -> dict[str, str] | None:
        with self._lock:
            return dict(self._hub) if self._hub is not None else None

    def accept(self, hub_id: str, name: str, url: str) -> str:
        """Check the hub that welcomed this peer: "" to keep the link, else why it is refused.
        The first hub is remembered; a later one with another id is refused until the file is deleted."""
        with self._lock:
            if self._hub is None:
                self._save({"hub_id": hub_id, "name": name, "url": url})
                self._log(f"Hub {name} ({url}, id {hub_id}) is now this peer's hub; remembered in {self.path}")
                return ""
            if self._hub["hub_id"] == hub_id:
                # The same hub, maybe at a new address: the id decides, the address is only a hint.
                if (self._hub["name"], self._hub["url"]) != (name, url):
                    self._save({"hub_id": hub_id, "name": name, "url": url})
                return ""
            return (f"hub {name} (id {hub_id}) is not the remembered hub {self._hub['name']} "
                    f"(id {self._hub['hub_id'] or '?'}); delete {self.path} to switch")


class DiscoveredHub:
    """The link's `connect` for a peer without `[hub] url`: browse, pick the remembered hub (or the
    only one on a first run) and dial it. `url` is the hub last dialled, for status and logs."""

    def __init__(
        self,
        *,
        browse: Callable[[], list[HubAdvert]],
        known: KnownHub,
        dial: Callable[[str], LinkConnection],
        log: Callable[[str], None],
    ) -> None:
        self._browse = browse
        self._known = known
        self._dial = dial
        self._log = log
        self.url = ""
        # Strangers already warned about, so a redial loop does not repeat the warning.
        self._warned: set[str] = set()

    def pick(self, found: list[HubAdvert]) -> HubAdvert:
        known = self._known.current()
        if known is not None:
            ours = [hub for hub in found if hub.hub_id == known["hub_id"]]
            for hub in found:
                if hub.hub_id != known["hub_id"] and hub.hub_id not in self._warned:
                    self._warned.add(hub.hub_id)
                    self._log(f"WARNING: another hub {hub.name} ({hub.url}, id {hub.hub_id}) is on the LAN; "
                              f"ignoring it, this peer's hub is {known['name']} (id {known['hub_id'] or '?'}). "
                              f"Delete {self._known.path} to switch.")
            if not ours:
                raise NoHubFound(f"remembered hub {known['name']} not found on the LAN")
            return ours[0]
        if not found:
            raise NoHubFound("no hub found on the LAN")
        if len({hub.hub_id for hub in found}) > 1:
            names = ", ".join(f"{hub.name} ({hub.url})" for hub in found)
            raise NoHubFound(f"several hubs on the LAN ({names}); set `[hub] url` to pick one")
        return found[0]

    def __call__(self) -> LinkConnection:
        hub = self.pick(self._browse())
        self.url = hub.url
        return self._dial(hub.url)


def zeroconf_browse(seconds: float) -> Callable[[], list[HubAdvert]]:
    """Browse `_edcr._tcp.local` for `seconds` and resolve every hub found."""

    def browse() -> list[HubAdvert]:
        from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf

        names: list[str] = []

        class Listener(ServiceListener):
            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                names.append(name)

            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

        zc = Zeroconf(ip_version=IPVersion.V4Only)
        try:
            browser = ServiceBrowser(zc, SERVICE_TYPE, Listener())
            threading.Event().wait(seconds)
            browser.cancel()
            found: list[HubAdvert] = []
            for name in dict.fromkeys(names):
                info = zc.get_service_info(SERVICE_TYPE, name, timeout=int(seconds * 1000))
                if info is None or info.port is None:
                    continue
                properties = {
                    key.decode("utf-8", "replace"): (value or b"").decode("utf-8", "replace")
                    for key, value in info.properties.items()
                }
                addresses = info.parsed_addresses(IPVersion.V4Only)
                advert = advert_from_record(properties, addresses[0] if addresses else "", info.port)
                if advert is not None:
                    found.append(advert)
            return found
        finally:
            zc.close()

    return browse


# `dns-sd -B` rows: timestamp, Add/Rmv, flags, interface, domain, service type, then the instance name.
_BROWSE_ROW = re.compile(r"^\S+\s+(Add|Rmv)\s+\d+\s+\d+\s+\S+\s+_edcr\._tcp\.\s+(.+)$")
# `dns-sd -L`: "<full name> can be reached at <host>:<port> (interface N)", the TXT record on the next line.
_LOOKUP_ROW = re.compile(r" can be reached at (\S+):(\d+) \(interface \d+\)")
# `dns-sd -G v4` rows: timestamp, Add/Rmv, flags, interface, hostname, address, TTL.
_ADDRESS_ROW = re.compile(r"^\S+\s+Add\s+\S+\s+\d+\s+\S+\s+(\d+\.\d+\.\d+\.\d+)\s+\d+")


def _txt_entries(line: str) -> dict[str, str]:
    """The TXT record as `dns-sd -L` prints it: entries split by spaces, with a space or backslash
    inside an entry escaped by a backslash and other control bytes written as \\xHH."""
    raw: list[bytearray] = [bytearray()]
    text = line.strip().encode("utf-8")
    index = 0
    while index < len(text):
        byte = text[index]
        if byte == ord("\\") and text[index + 1:index + 2] == b"x" and re.fullmatch(
                rb"[0-9A-Fa-f]{2}", text[index + 2:index + 4]):
            raw[-1].append(int(text[index + 2:index + 4], 16))
            index += 4
            continue
        if byte == ord("\\") and index + 1 < len(text):
            raw[-1].append(text[index + 1])
            index += 2
            continue
        if byte == ord(" "):
            raw.append(bytearray())
        else:
            raw[-1].append(byte)
        index += 1
    entries: dict[str, str] = {}
    for entry in raw:
        key, _, value = entry.decode("utf-8", "replace").partition("=")
        if key:
            entries.setdefault(key, value)
    return entries


def _lookup_record(output: str) -> tuple[str, int, dict[str, str]] | None:
    """Host, port and TXT entries from `dns-sd -L` output, or None before it has answered."""
    lines = output.splitlines()
    for index, line in enumerate(lines[:-1]):
        match = _LOOKUP_ROW.search(line)
        if match:
            return match.group(1), int(match.group(2)), _txt_entries(lines[index + 1])
    return None


def _lan_address(output: str) -> str:
    """The host's address from `dns-sd -G v4` output: a LAN one over loopback, which a hub on this very
    Mac also reports and no other machine could use. "" before it has answered."""
    addresses = [match.group(1) for match in map(_ADDRESS_ROW.match, output.splitlines()) if match]
    lan = [address for address in addresses if not address.startswith("127.")]
    return (lan or addresses or [""])[0]


def dnssd_browse(
    seconds: float, run: Callable[[list[str], float, Callable[[str], bool]], str],
) -> Callable[[], list[HubAdvert]]:
    """Browse `_edcr._tcp.local` with macOS `dns-sd`: list instances for `seconds`, then look up each one
    and resolve its host. `run(args, seconds, done)` runs dns-sd (which never exits by itself) until
    `done(output)` or the deadline and returns what it printed."""

    def browse() -> list[HubAdvert]:
        instances: dict[str, None] = {}
        for match in map(_BROWSE_ROW.match, run(["dns-sd", "-B", "_edcr._tcp", "local"], seconds,
                                                 lambda output: False).splitlines()):
            if match and match.group(1) == "Add":
                instances[match.group(2)] = None
            elif match:
                instances.pop(match.group(2), None)
        found: list[HubAdvert] = []
        for instance in instances:
            record = _lookup_record(run(["dns-sd", "-L", instance, "_edcr._tcp", "local"], seconds,
                                        lambda output: _lookup_record(output) is not None))
            if record is None:
                continue
            host, port, properties = record
            address = _lan_address(run(["dns-sd", "-G", "v4", host], seconds,
                                       lambda output: bool(_lan_address(output))))
            advert = advert_from_record(properties, address, port)
            if advert is not None:
                found.append(advert)
        return found

    return browse


def run_until(args: list[str], seconds: float, done: Callable[[str], bool]) -> str:
    """Run a command that does not exit by itself (`dns-sd`), collect its output until `done(output)`
    or `seconds` pass, then stop it. A missing command returns "", as if nothing was found."""
    try:
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return ""
    chunks: list[bytes] = []
    deadline = time.monotonic() + seconds
    try:
        assert process.stdout is not None
        while (remaining := deadline - time.monotonic()) > 0:
            ready, _, _ = select.select([process.stdout], [], [], remaining)
            if not ready:
                break
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            chunks.append(chunk)
            if done(b"".join(chunks).decode("utf-8", "replace")):
                break
    finally:
        process.kill()
        process.wait()
        if process.stdout is not None:
            process.stdout.close()
    return b"".join(chunks).decode("utf-8", "replace")


def lan_browse(platform: str, seconds: float) -> Callable[[], list[HubAdvert]]:
    """The peer's browser: `dns-sd` on macOS (see the module note), zeroconf elsewhere."""
    if platform == "darwin":
        return dnssd_browse(seconds, run_until)
    return zeroconf_browse(seconds)


def zeroconf_advertise(*, address: str, port: int, properties: dict[str, str]) -> Callable[[], None]:
    """Advertise this hub on the interface that owns `address`; returns the function that stops it."""
    from zeroconf import IPVersion, ServiceInfo, Zeroconf

    name = properties.get("name") or socket.gethostname()
    # mDNS instance names cannot hold dots; the hub name is only a label here, the TXT id decides.
    label = name.replace(".", "-")[:60]
    info = ServiceInfo(
        SERVICE_TYPE,
        f"{label}.{SERVICE_TYPE}",
        addresses=[socket.inet_aton(address)],
        port=port,
        properties=properties,
        server=f"{socket.gethostname().split('.')[0]}.local.",
    )
    zc = Zeroconf(interfaces=[address], ip_version=IPVersion.V4Only)
    zc.register_service(info, allow_name_change=True)

    def stop() -> None:
        zc.unregister_service(info)
        zc.close()

    return stop


def advertise_address(host: str, detect_lan_host: Callable[[], str]) -> str:
    """The address the hub advertises: the bind host, or the detected LAN address when it binds every
    interface. "" (no advert) for loopback, where no peer on another machine could reach it."""
    if host in {"0.0.0.0", ""}:
        try:
            return detect_lan_host()
        except RuntimeError:
            return ""
    if host.startswith("127.") or host == "localhost":
        return ""
    return host

