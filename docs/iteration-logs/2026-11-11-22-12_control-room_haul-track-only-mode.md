# Iteration Log

- Area: `control-room`
- Title: `haul-track-only-mode`
- Started: `2026-11-11 22:12`

## Summary

- Two-way haul gets a **Track only** mode for commanders who fly and trade by hand and only want the stats. Web: a Track only button next to Start route sends `command.dispatch_haul_loop` with `params.mode = "track"`, so the hub relays it to a peer unchanged. Command bar: `haul track` on the selected route.
- `routines_haul.dispatch_haul_loop` validates the stations as before, then `track_haul` starts `HaulStats(tracking=True)` instead of a routine (refused with `_refuse_busy` while one runs). `start_haul_stats` now takes a required `tracking`.
- No routine sets the phase while tracking, so `haul_tracking._track_phase` infers it from the journal: MarketBuy buy, Undocked undock, StartJump depart, FSDJump / SupercruiseExit / Docked transit, MarketSell sell. Buy and undock point at the other station; dock and sell at this one. It runs before the run row is updated so the row's `phase` matches.
- Run rows carry `"mode": "tracked"` or `"assisted"` in the one history file; no filter yet. `stop` (and the Stop stats button) ends tracking through `_stop_haul_stats` instead of refusing an active haul. The routine panel shows "Tracking" and the stage steps.

## Follow-ups

- Tracking is not persisted: a Control Room restart ends it.
- No automatic detection of a hand-flown loop; the user asked for the manual button first.
- Not yet tried live or in a browser.
