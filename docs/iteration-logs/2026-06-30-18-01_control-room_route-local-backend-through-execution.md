# Iteration Log

- Area: `control-room`
- Title: `route-local-backend-through-execution`
- Started: `2026-06-30 18:01`

## Summary

- Routed local backend command execution through the new composable execution dependency.

## Changes

- Updated `LocalControlRoomBackend` dispatch, destination, haul-loop, prompt, route-load, and interrupt paths to call `host.dependencies.execution`.
- Added a regression test proving backend dispatch uses the execution dependency surface.

## Follow-ups

- Continue reducing direct backend/facade coupling by moving app-facing command helpers to execution dependencies.
