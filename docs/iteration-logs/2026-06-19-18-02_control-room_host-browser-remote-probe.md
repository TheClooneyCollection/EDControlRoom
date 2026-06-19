# Iteration Log

- Area: `control-room`
- Title: `host-browser-remote-probe`
- Started: `2026-06-19 18:02`

## Summary

- Hosted the browser probe from the observer server itself and taught it to send real operator commands, which makes the future web-client path exercise the actual runtime surface instead of only reading discovery metadata.

## Changes

- Added `GET /browser-probe` on the observer server so a browser can load the probe from the same origin as the remote session surface.
- Extended the browser probe to claim operator, submit command input, request snapshots, and cancel active routines while still showing snapshot and activity state.
- Added server coverage for the hosted HTML endpoint and updated the remote operator docs/status handoff to point at the served probe as the default browser validation path.

## Follow-ups

- If a real web client is built next, reuse the hosted probe flow first and only replace its UI shell; do not regress the same-origin browser validation path unless there is a deliberate reason to decouple it.
