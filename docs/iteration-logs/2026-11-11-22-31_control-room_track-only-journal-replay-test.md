# Iteration Log

- Area: `control-room`
- Title: `track-only-journal-replay-test`
- Started: `2026-11-11 22:31`

## Summary

- Replayed a real assisted haul journal (three loops on one same-system route) through Track only. Profit, cargo and run times matched the assisted history; where a routine restart split one assisted run into two aborted rows, Track only counted it as one completed run with the same total.
- New regression fixture `tests/fixtures/journal/two_way_haul_hand_flown.jsonl`: 42 events cut from that journal, only Docked, Undocked, MarketBuy, MarketSell, StartJump, SupercruiseEntry and SupercruiseExit with an allowlist of game-data fields (no commander, chat or ship identity), dates moved to 2026-01-01. `test_haul_track_replays_a_real_hand_flown_journal` checks the phase timeline, the stats and the three tracked run rows.
- Fix found by the fixture: `ship.station` clears only on SupercruiseExit or a Music NoTrack while undocking, so a StartJump right after Undocked could still see the station just left and point the phase at the wrong station. `_track_phase` now reads the station only on station events (buy, sell, undock, dock) and keeps the target station in flight.
