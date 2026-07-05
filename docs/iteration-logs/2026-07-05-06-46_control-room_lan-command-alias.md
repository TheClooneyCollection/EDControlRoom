# Iteration Log

- Area: `control-room`
- Title: `lan-command-alias`
- Started: `2026-07-05 06:46`

## Summary

- Added `control_room.py lan` as a shorter alias for `control_room.py serve --lan`.

## Changes

- Routed `lan` through the existing observer-server startup path with LAN host detection, default token behavior, and the same `--host` conflict guard as `serve --lan`.
- Added CLI regression coverage for the alias and updated operator docs/status handoff references.

## Follow-ups

- None.
