# Iteration Log

- Area: `web`
- Title: `default-serve-token-and-web-prompt`
- Started: `2026-07-04 11:22`

## Summary

- Added an implicit `edcr` shared token for `control_room.py serve` when no `--token` is passed, kept explicit-token sessions from pre-filling that default in the web client, and replaced missing/rejected-token prompts with a styled in-page dialog.

## Changes

- Added a `DEFAULT_OBSERVER_ACCESS_TOKEN` constant for serve-mode CLI wiring while leaving `connect` token requirements unchanged.
- Passed a web-default token separately from the server auth token so `/haul` only receives `edcr` for implicit no-flag serve sessions.
- Updated Haul Web v1 to use URL token, cached localStorage token, then server-injected token, and to prompt the user when none is available.
- Replaced `window.prompt()` with a styled `<dialog>` token prompt with Connect/Cancel controls and Enter-to-submit behavior.
- Added rejected-token handling that clears a bad cached token, warns in the activity log, and reopens the token dialog when the websocket closes before `event.connection_ready`.
- Added CLI and server regression coverage for implicit serve tokens, explicit-token web behavior, and the in-page web token prompt/retry path.

## Follow-ups

- Live-check `/haul` from both `serve` and `serve --token ...` sessions to confirm the browser token prompt/default feels right.
