# Iteration Log

- Area: `control-room`
- Title: `add-browser-remote-reconnect`
- Started: `2026-06-19 18:06`

## Summary

- Brought the hosted browser probe up to the same reconnect/state-healing baseline as the Textual remote client so transient disconnects do not leave the future web-client path in a stale one-shot state.

## Changes

- Added automatic browser-probe reconnect with exponential backoff, reconnect status messaging, and a fresh snapshot request on reconnect.
- Improved the browser probe’s replay rendering and message stream so announcements, replay choices, and reconnect behavior are easier to inspect during remote validation.
- Updated endpoint coverage plus the remote operator docs/status handoff so the browser path is explicitly documented as covering reconnect recovery too.

## Follow-ups

- If a dedicated web client is built, preserve the reconnect-and-refresh semantics as a baseline requirement rather than treating them as probe-only behavior.
