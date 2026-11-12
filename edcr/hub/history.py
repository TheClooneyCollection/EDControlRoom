"""Central haul history on the hub: every node's finished runs, tagged with the node they came from.

Peers send each finished run row up the link; the hub appends it to its own JSONL file (the
`haul_runs_file` format plus a `node` field: `{id, name}`), once per run key and node. The hub's
own runs stay in its `haul_runs_file` and join the view under the hub's node id, so that file
stays the one source of truth for the local node, as a peer's own file is for the peer.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Iterable

from edcr.haul_history import append_run, load_runs, run_key
from edcr.hub.peer import NodeHello

# Filter value meaning "every node" or "every ship".
ALL = "all"


def tag_node(row: dict[str, Any], node: NodeHello) -> dict[str, Any]:
    return {**row, "node": {"id": node.node_id, "name": node.name}}


def row_node_id(row: dict[str, Any]) -> str | None:
    node = row.get("node")
    node_id = node.get("id") if isinstance(node, dict) else None
    return node_id if isinstance(node_id, str) else None


def row_ship_id(row: dict[str, Any]) -> int | None:
    ship = row.get("ship")
    ship_id = ship.get("id") if isinstance(ship, dict) else None
    return ship_id if isinstance(ship_id, int) and not isinstance(ship_id, bool) else None


class HubRuns:
    """Peers' runs on the hub, append-only. Thread-safe: every peer session adds from its own thread."""

    def __init__(self, path: Path, keys: set[tuple[str, str, str, str | None]], log: Callable[[str], None]) -> None:
        self.path = path
        self._keys = keys
        self._log = log
        self._lock = threading.Lock()

    @classmethod
    def open(cls, path: Path, log: Callable[[str], None]) -> "HubRuns":
        rows, _ = load_runs(path)
        return cls(path, {run_key(row) for row in rows}, log)

    def add(self, node: NodeHello, row: object) -> bool:
        """Store one peer run; False when the hub already has it.

        Raises ValueError for a row that is not a finished run, OSError when the file write failed.
        """
        if not isinstance(row, dict):
            raise ValueError("Invalid run")
        tagged = tag_node(row, node)
        key = run_key(tagged)
        with self._lock:
            if key in self._keys:
                return False
            if not append_run(self.path, tagged, self._log):
                raise OSError(f"could not append to {self.path}")
            self._keys.add(key)
            return True

    def rows(self) -> tuple[list[dict[str, Any]], int]:
        return load_runs(self.path)


class CentralHistory:
    """What the hub's history views read: its own runs under its node id, then every peer's."""

    def __init__(self, *, local: NodeHello, local_file: Path, runs: HubRuns) -> None:
        self.local = local
        self.local_file = local_file
        self.runs = runs

    def rows(self) -> tuple[list[dict[str, Any]], int]:
        own, own_skipped = load_runs(self.local_file)
        peers, peer_skipped = self.runs.rows()
        # A peer row claiming the hub's id would be a copied node id; the hub's own file wins.
        peers = [row for row in peers if row_node_id(row) != self.local.node_id]
        return [tag_node(row, self.local) for row in own] + peers, own_skipped + peer_skipped


def parse_node_filter(value: str | None) -> str:
    text = (value or "").strip()
    return text or ALL


def parse_ship_filter(value: str | None) -> int | None:
    """None for every ship; raises ValueError for anything but `all` or a ship id."""
    text = (value or "").strip().lower()
    if text in ("", ALL):
        return None
    return int(text)


def filter_runs(rows: Iterable[dict[str, Any]], *, node: str, ship: int | None) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if (node == ALL or row_node_id(row) == node) and (ship is None or row_ship_id(row) == ship)
    ]


def history_options(rows: Iterable[dict[str, Any]], local: NodeHello | None) -> dict[str, list[dict[str, Any]]]:
    """The nodes and ships seen in the history, for the page's filters; newest name wins."""
    nodes: dict[str, dict[str, Any]] = {}
    ships: dict[int, dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: str(item.get("ended_at"))):
        node_id = row_node_id(row)
        if node_id is not None:
            nodes[node_id] = {"id": node_id, "name": str(row["node"].get("name") or node_id),
                              "local": local is not None and node_id == local.node_id}
        ship_id = row_ship_id(row)
        if ship_id is not None:
            ship = row["ship"]
            ships[ship_id] = {"id": ship_id, "type": ship.get("type"), "name": ship.get("name")}
    if local is not None:
        nodes.setdefault(local.node_id, {"id": local.node_id, "name": local.name, "local": True})
    return {
        "nodes": sorted(nodes.values(), key=lambda node: (not node["local"], node["name"].casefold())),
        "ships": sorted(ships.values(), key=lambda ship: (str(ship["name"] or ship["type"] or "")).casefold()),
    }
