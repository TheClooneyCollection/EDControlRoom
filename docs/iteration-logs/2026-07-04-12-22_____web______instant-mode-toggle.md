# Iteration Log

- Area: `web`
- Title: `instant-mode-toggle`
- Started: `2026-07-04 12:22`

## Summary

- Added a Haul Web instant-mode toggle that reflects hydrated routine state and sends explicit `instant on/off` commands.

## Changes

- Added an `Instant on/off` button to `/haul`, disabled unless the browser is the active operator.
- Wired the toggle to `routine.instant_mode` from hydrate and to `command.submit_input` with `skip_delay=true`.
- Added static web regression coverage for the instant-mode toggle payload.

## Follow-ups

- Live-check the `/haul` instant-mode toggle against a running server to confirm the hydrated state flips promptly after command execution.
