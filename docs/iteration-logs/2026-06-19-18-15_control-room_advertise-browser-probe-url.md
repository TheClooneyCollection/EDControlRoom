# Iteration Log

- Area: `control-room`
- Title: `advertise-browser-probe-url`
- Started: `2026-06-19 18:15`

## Summary

- Added first-class discovery for the hosted browser probe so future launchers and web shells can find the served browser client entrypoint from `/capabilities` instead of hardcoding it.

## Changes

- Added `browser_probe_url` to the observer server capabilities response alongside the existing `message_schema_url`.
- Updated the checked-in message schema, server tests, and schema regression coverage so the new discovery field is treated as part of the remote contract.
- Refreshed the protocol design note, remote operator runbook, and control-room status handoff to describe the new browser-probe discovery path.

## Follow-ups

- If a dedicated launcher or browser shell is introduced, prefer reading `browser_probe_url` from capabilities rather than constructing the path independently.
