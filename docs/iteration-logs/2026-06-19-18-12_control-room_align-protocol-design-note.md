# Iteration Log

- Area: `control-room`
- Title: `align-protocol-design-note`
- Started: `2026-06-19 18:12`

## Summary

- Realigned the main Control Room protocol design note with the current shipped remote architecture so the written contract no longer describes superseded message families and payloads.

## Changes

- Replaced the stale draft vocabulary in `docs/design/0002-control-room-client-server-protocol.md` with the actual current command, event, and response message set used by `serve` and `connect`.
- Updated the example envelope plus payload sections to describe `command.submit_input`, replay commands, active-operator claiming, and `command.cancel_active_routine` instead of the pre-remote routine/filter draft.
- Expanded the capabilities section to match the current runtime metadata fields that the HTTP discovery surface returns.

## Follow-ups

- Keep the protocol design note and the checked-in schema moving together whenever the remote surface changes, so future web-client work is not forced to guess which document is authoritative.
