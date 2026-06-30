# Iteration Log

- Area: `control-room`
- Title: `preserve-observer-prompt-caret`
- Started: `2026-06-30 17:14`

## Summary

- Fixed `control_room connect` prompt editing so periodic remote snapshot refreshes no longer shove the caret to the end of the command field while the operator is editing a local prompt or draft command.

## Changes

- Added observer-local caret tracking alongside the existing local draft-text preservation so the remote client can reapply the current input value without losing the operator's edit position.
- Synced the live observer prompt widget text back into retained local prompt state so snapshot rebuilds stop reviving stale prefill-era command text after mid-prompt edits.
- Split prompt-prefill signature handling so active prompt steps no longer treat operator text edits as a brand-new prefill event that should reset the caret to the end.
- Scoped the restore logic to observer mode only, leaving embedded/local Control Room input behavior unchanged after confirming the bug was not reproducible there.
- Tightened observer client regressions to assert mid-string caret preservation for both freeform command drafts and prompt-prefilled inputs across snapshot refreshes.

## Follow-ups

- Live-check one active `serve` plus `connect` session while a prompt is open to confirm the real Textual widget keeps caret position stable under the normal status refresh cadence.
