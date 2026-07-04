# Iteration Log

- Area: `control-room`
- Title: `dest-fibonacci-settle-retry`
- Started: `2026-07-04 22:02`

## Summary

- Added a narrow retry path for `dest` when route verification finds no destination in `NavRoute.json`.

## Changes

- `set_gal_map_destination()` now accepts optional retry map-settle values and reruns the full galaxy-map flow only when verification fails with an unset route destination.
- Control Room `dest` dispatch now starts with the configured settle and then retries with Fibonacci-style longer settles, giving the normal `2.0s` default the sequence `2, 3, 5, 8`.
- Added regressions for unset-route retry, wrong-destination no-retry behavior, and Control Room retry-settle wiring.

## Follow-ups

- Live-check `dest <system>` under CrossOver when the first route plot leaves `NavRoute.json` empty to confirm the 3/5/8 second retries are enough before adding operator configuration.
