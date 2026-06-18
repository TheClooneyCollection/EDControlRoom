# Iteration Log

- Area: `control-room`
- Title: `session-command-transport`
- Started: `2026-06-18 20:15`

## Summary

- Added bidirectional WebSocket session command handling, with `command.request_snapshot` round-tripping successfully and operator-only commands now getting explicit correlated protocol errors for observer sessions.

## Changes

- Extended the server session loop to receive client envelopes as well as push broker events, and added protocol handling for `command.request_snapshot`, unsupported message errors, and observer rejection for `command.submit_input`.
- Added outbound command queuing and response handling to `RemoteObserverBackend`, so the remote client can issue protocol commands and surface `response.error` or `response.success` messages locally.
- Added focused tests for correlated snapshot responses, observer command rejection, and remote backend command queue behavior, then re-ran compile checks and the full unittest suite.

## Follow-ups

- The next slice is active-operator promotion plus actual command execution on the server host; the transport and error semantics are now in place for that change.
