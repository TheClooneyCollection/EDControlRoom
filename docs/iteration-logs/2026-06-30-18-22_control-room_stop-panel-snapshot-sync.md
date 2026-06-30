# Iteration Log

- Area: `control-room`
- Title: `stop-panel-snapshot-sync`
- Started: `2026-06-30 18:22`

## Summary

- Stopped read-only panel refreshes from synchronizing snapshot state before rendering.

## Changes

- Removed `_sync_view_snapshot()` calls from status, haul, and market refresh methods now that those panels render from data-source-backed view models.

## Follow-ups

- Continue removing snapshot sync from interactive surfaces after they move behind view actions and data sources.
