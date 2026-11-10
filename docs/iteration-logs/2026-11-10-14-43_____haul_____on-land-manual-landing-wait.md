# Iteration Log

- Area: `haul`
- Title: `on-land-manual-landing-wait`
- Started: `2026-11-10 14:43`

## Summary

- A haul to an `on land` station looked paused but could not be resumed: after the drop, `transit_to_station` returned the manual-landing result, the haul loop returned, and `clear_routine` stopped the session (run recorded `aborted` / `stats stopped` in transit, e.g. Chauhan Dock 2026-11-10 14:21). `resume` only works for the in-routine pause before a buy, so it reported no active haul.

## Changes

- `transit_to_station` takes a required `wait_for_manual_landing`. Two-way and multi-leg haul pass `True`: after the drop near an on-land station they log and TTS `manual_landing` ("please land manually at {station_name}. We continue once docked."), wait for `Docked` within the dock timeout, open the refuel menu as usual and continue trading. `travel` and Spansh routes pass `False` and still end at the handoff.

## Follow-ups

- Live-validate at Chauhan Dock: the routine should continue straight into the station 1 buy after a manual landing.
