# Iteration Log

- Area: `control-room`
- Title: `preserve-local-prompt-edits`
- Started: `2026-06-30 17:23`

## Summary

- Fixed embedded Control Room prompt editing so periodic local snapshot refreshes no longer overwrite in-progress `haul search` command-bar edits with the older prefilled parameter string.

## Changes

- Added local command-input change handling in `ControlRoomApp` so active prompt-prefill state tracks the live command-bar text instead of only the original prefill value.
- Added a regression proving a locally edited `search_edit` prompt survives `_apply_view_snapshot_state()` without losing the operator's edited search line or cursor position.
- Re-ran the embedded app test module plus the full repo suite after the shared input-path change.

## Follow-ups

- Live-check local `haul search` editing under the normal status-refresh cadence to confirm the real Textual widget no longer reverts edited parameters during long prompt sessions.
