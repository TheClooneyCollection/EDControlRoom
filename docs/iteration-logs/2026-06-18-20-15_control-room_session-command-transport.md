# Iteration Log

- Area: `control-room`
- Title: `session-command-transport`
- Started: `2026-06-18 20:15`

## Summary

- Added bidirectional WebSocket session command handling, wired active-operator submit callbacks into the headless host, and kept observer sessions on explicit correlated protocol errors for operator commands.

## Changes

- Extended the server session loop to receive client envelopes as well as push broker events, and added protocol handling for `command.request_snapshot`, unsupported message errors, and observer rejection for `command.submit_input`.
- Added outbound command queuing and response handling to `RemoteObserverBackend`, so the remote client can issue protocol commands and surface `response.error` or `response.success` messages locally.
- Added a minimal headless command-input stub plus server-side submit callback wiring so active-operator sessions can drive simple remote inputs through the existing command parser and prompt state.
- Added focused tests for correlated snapshot responses, observer command rejection, active-operator command acceptance, headless-host remote input, and remote backend command queue behavior, then re-ran compile checks and the full unittest suite.

## Follow-ups

- The next slice is active-operator promotion in the session broker plus broader remote command validation, especially routine-heavy commands that still depend on deeper worker/runtime seams in the headless host.
