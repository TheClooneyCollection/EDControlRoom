# Iteration Log

- Area: `haul`
- Title: `route-and-pad-full-retry`
- Started: `2026-07-01 12:52`

## Summary

- Added non-fatal haul handling for galaxy-map route failures and a pad-full docking retry path for `DockingDenied` `NoSpace` style responses.

## Changes

- Two-way and multi-leg haul now retry galaxy-map destination setting twice, log/TTS an unconfirmed-route warning, skip automatic FSD engage on route failure, and continue waiting for pilot-driven journal progress.
- Docking now classifies pad-full denial reasons, holds throttle at zero, uses a separate slower pad-full retry budget, and announces the pad-full state once before retrying.
- Added regression coverage for route-unconfirmed continuation, confirmed-route fixtures, pad-full retry success, pad-full retry exhaustion, and the new default TTS phrase.

## Follow-ups

- Live-validate the actual Elite journal reason string for full pads under CrossOver and tune the default `30s x 20` pad-full retry window if it feels too slow or too persistent.
