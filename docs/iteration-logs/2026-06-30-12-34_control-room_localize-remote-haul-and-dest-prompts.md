# Iteration Log

- Area: `control-room`
- Title: `localize-remote-haul-and-dest-prompts`
- Started: `2026-06-30 12:34`

## Summary

- Rebased remote operator mode on the existing local `ControlRoomApp` prompt flows for `haul`, `haul route`, `haul search`, `dest`, and `home`, so `connect` now resolves those interactions locally and sends only finalized routine payloads to the headless server.

## Changes

- Added structured remote routine commands for finalized destination and haul launches, wired the remote backend to emit them, and taught the headless observer server to execute them without opening server-owned prompt sessions.
- Changed `ObserverControlRoomApp` to intercept prompt-owning commands locally, preserve local prompt state across snapshot refreshes, and load trade-route picker selections into the same local haul prompt used by embedded mode.
- Updated the checked-in control-room message schema plus client/server/protocol tests to cover the new dispatch commands and the new local-prompt remote behavior.

## Follow-ups

- Move replay browser ownership out of the server next so replay filtering, selection, and edit/execute entrypoints reuse the same fully local behavior in `connect`.
