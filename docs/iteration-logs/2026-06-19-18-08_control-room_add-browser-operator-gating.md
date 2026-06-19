# Iteration Log

- Area: `control-room`
- Title: `add-browser-operator-gating`
- Started: `2026-06-19 18:08`

## Summary

- Added active-operator gating to the hosted browser probe so the future web-client path respects the same observer-versus-operator boundary as the Textual remote client.

## Changes

- Disabled mutating browser-probe controls while the current session is only an observer and surfaced an explicit operator hint in the UI.
- Blocked outbound mutating protocol commands client-side unless the latest snapshot says the browser session is the active operator, while still allowing snapshot requests and operator claims.
- Updated endpoint coverage plus the remote operator docs/status handoff to reflect that browser validation now exercises active-operator gating too.

## Follow-ups

- If a dedicated web client is built, keep the client-side operator gating as a UX safeguard even though the server remains authoritative for permission checks.
