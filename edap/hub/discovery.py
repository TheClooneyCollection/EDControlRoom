"""Finding the hub on the LAN: the hub advertises `_edcr._tcp.local` over mDNS, a peer without
`[hub] url` browses for it.

The peer remembers the hub it first linked to (`KnownHub`, saved next to the config) and from then
on dials only that hub, so a stray advertiser on the LAN cannot quietly take over. Browsing and
advertising are plain functions (`zeroconf_browse`, `zeroconf_advertise`), so tests use fakes.
"""
from __future__ import annotations

import json
import socket
import threading
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

