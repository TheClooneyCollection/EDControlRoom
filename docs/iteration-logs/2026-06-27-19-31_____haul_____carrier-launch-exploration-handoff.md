# Iteration Log

- Area: `haul`
- Title: `carrier-launch-exploration-handoff`
- Started: `2026-06-27 19:31`

## Summary

- Added a carrier-specific undock handoff so haul/manual undock can treat `MusicTrack="Exploration"` as resumed manual launch control after `Undocked` from `Stronghold Carrier` or `Fleet Carrier`.

## Changes

- Added shared journal-event helpers for carrier detection and the `Exploration` manual-resume special case.
- Updated undock/haul clear-of-station handling to accept carrier `Exploration`, then continue into the normal mass-lock escape and hyperspace path.
- Updated ship-state and Control Room event reducers so carrier `Exploration` clears `in_undocking` to `in_space` instead of waiting indefinitely for `NoTrack`.
- Added routine, haul, state, and Control Room tests for the carrier `Exploration` path and widened the failure-message matcher for the new timeout wording.

## Follow-ups

- Live-validate both named `Stronghold Carrier` launches and real owner-named `Fleet Carrier` launches to confirm the carrier-name/type heuristics are sufficient in journal output.
