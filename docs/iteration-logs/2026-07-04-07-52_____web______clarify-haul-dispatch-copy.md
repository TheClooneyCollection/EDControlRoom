# Iteration Log

- Area: `web`
- Title: `clarify-haul-dispatch-copy`
- Started: `2026-07-04 07:52`

## Summary

- Corrected the static Haul prototype copy so it does not describe the existing structured haul dispatch command as future backend work.

## Changes

- Updated `web/haul-v1.html` to label `command.dispatch_haul_loop` as an existing backend command.
- Left `command.search_haul_routes` framed as future work because the server-side structured search command is not implemented yet.

## Follow-ups

- Wire the existing `command.dispatch_haul_loop` path before adding new backend action surface for haul search.
