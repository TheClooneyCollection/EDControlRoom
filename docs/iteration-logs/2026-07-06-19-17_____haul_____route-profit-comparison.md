# Iteration Log

- Area: `haul`
- Title: `route-profit-comparison`
- Started: `2026-07-06 19:17`

## Summary

- Added selected-route per-trip profit tracking so completed two-way haul runs can be compared against the planned Inara route.

## Changes

- TUI route picker rows now include trip profit and the haul panel shows expected route trip profit plus last-run delta.
- Web `/haul` route results now show `Profit / trip` and include the selected route profit in `command.dispatch_haul_loop` params.
- Haul stats persist expected route profit and last-run delta through saved state and remote hydrate payloads.
- Completed clean haul runs log and TTS whether actual profit was more, less, or equal to the planned route.

## Follow-ups

- Live-validate that Inara trip-profit text from current route cards continues to parse cleanly during a full route-to-haul run.
