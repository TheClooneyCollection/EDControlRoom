# Iteration Log

- Area: `control-room`
- Title: `push-snapshots-after-remote-input`
- Started: `2026-06-18 23:36`

## Summary

- Fixed a remote-only sync bug where the server accepted operator input but did not immediately push a fresh snapshot afterward, leaving connected clients with stale state for prompt and market transitions.

## Changes

- Updated `HeadlessControlRoomHost.handle_remote_input()` to publish a fresh snapshot through the configured protocol sink after backend input handling completes.
- Added server coverage that verifies remote input now produces a new published snapshot reflecting the updated host state.

## Follow-ups

- Live-test `dest`, `haul`, and other prompt-heavy commands over `connect` against a running `serve` instance now that post-input snapshot pushes are explicit.
