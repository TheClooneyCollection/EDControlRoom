"""This machine's IPv4 interface addresses, for binding every LAN interface and for a peer picking the hub
address on its own subnet.

POSIX reads `ifconfig` (address and netmask). Windows has no stdlib call that lists netmasks, so it takes
every address the host name resolves to and assumes a /24, the common home LAN size.
"""
from __future__ import annotations

import ipaddress
import socket
import subprocess
from typing import Callable

WINDOWS_ASSUMED_PREFIX = 24


def ifconfig_interfaces(output: str) -> list[ipaddress.IPv4Interface]:
    """`inet` rows from `ifconfig` output: macOS writes the netmask in hex (`0xffffff00`), Linux dotted."""
    interfaces: list[ipaddress.IPv4Interface] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2 or parts[0] != "inet":
            continue
        address = parts[1].removeprefix("addr:")
        netmask = "32"
        for index, part in enumerate(parts[:-1]):
            if part == "netmask":
                netmask = parts[index + 1]
        if netmask.startswith("0x"):
            try:
                netmask = str(ipaddress.IPv4Address(int(netmask, 16)))
            except ValueError:
                netmask = "32"
        try:
            interfaces.append(ipaddress.IPv4Interface(f"{address}/{netmask}"))
        except ValueError:
            continue
    return interfaces


def hostname_interfaces(addresses: list[str]) -> list[ipaddress.IPv4Interface]:
    """Addresses the host name resolves to, each assumed to sit on a /24."""
    interfaces: list[ipaddress.IPv4Interface] = []
    for address in dict.fromkeys(addresses):
        try:
            interfaces.append(ipaddress.IPv4Interface(f"{address}/{WINDOWS_ASSUMED_PREFIX}"))
        except ValueError:
            continue
    return interfaces


def _run_ifconfig() -> str:
    try:
        return subprocess.check_output(["ifconfig"], text=True, stderr=subprocess.DEVNULL, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return ""


def _hostname_addresses() -> list[str]:
    try:
        return socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        return []


def local_ipv4_interfaces(platform: str) -> list[ipaddress.IPv4Interface]:
    """Every IPv4 interface address on this machine, loopback and VPNs included; callers filter."""
    if platform.startswith("win"):
        return hostname_interfaces(_hostname_addresses())
    return ifconfig_interfaces(_run_ifconfig())


def preferred_addresses(addresses: list[str],
                        local: Callable[[], list[ipaddress.IPv4Interface]]) -> list[str]:
    """`addresses` with the ones on a subnet this machine is on first, otherwise in their given order."""
    if len(addresses) < 2:
        return list(addresses)
    networks = [interface.network for interface in local() if not interface.ip.is_loopback]

    def on_our_subnet(address: str) -> bool:
        try:
            ip = ipaddress.IPv4Address(address)
        except ValueError:
            return False
        return any(ip in network for network in networks)

    return sorted(addresses, key=lambda address: not on_our_subnet(address))
