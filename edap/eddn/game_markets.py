"""Our own Market.json captures, written into the EDDN store by the same newest-wins rule as EDDN."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from edap.eddn.messages import market_snapshot_from_game
from edap.eddn.store import EddnStore
from edap.recent_markets import load_recent_markets


@dataclass(frozen=True)
class GameMarketImport:
    station: str
    system: str
    timestamp: str
    # False when the store already held newer data for the station.
    written: bool


def import_game_markets(store: EddnStore, recent_markets_file: Path) -> list[GameMarketImport]:
    """Write each captured market whose game timestamp is not older than the stored one.

    A newer snapshot replaces the station's whole price list, as an EDDN message does, so stale rows
    cannot ride along under a fresh timestamp.
    """
    results = []
    for game in load_recent_markets(recent_markets_file):
        snapshot = market_snapshot_from_game(game)
        if snapshot is not None:
            results.append(GameMarketImport(game.station, game.system, game.timestamp, store.apply(snapshot)))
    store.commit()
    return results


def import_summary(results: list[GameMarketImport]) -> str:
    written = [f"{result.station} ({result.timestamp})" for result in results if result.written]
    kept = len(results) - len(written)
    return f"our markets: {len(written)} written{': ' + ', '.join(written) if written else ''}; {kept} already newer in the DB"
