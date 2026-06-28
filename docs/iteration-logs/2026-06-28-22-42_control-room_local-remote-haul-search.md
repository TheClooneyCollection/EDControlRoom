# Iteration Log

- Area: `control-room`
- Title: `local-remote-haul-search`
- Started: `2026-06-28 22:42`

## Summary

- Moved `control_room connect` haul search execution and route-picker/results state off the remote server and onto the local observer client, while keeping selected-route and `dest` submission pointed at the remote host.

## Changes

- Added a structured `command.load_trade_route` remote message plus server/backend handling so a locally selected Inara route can prefill the remote haul prompt without relying on server-side `haul route <index>` state.
- Overrode observer-mode haul search dispatch to run local Inara searches, retain local picker state across remote snapshot refreshes, ignore remote trade-route snapshot hydration, and continue sending destination shortcuts to the remote session.
- Extended protocol, schema, and client/server tests for local observer searches, remote route submission, and the new message type, then re-ran the full unittest suite successfully.

## Follow-ups

- Live-check `control_room connect` during a real operator session to confirm local Inara latency, picker ergonomics, and remote haul-prefill timing all feel correct end to end.
