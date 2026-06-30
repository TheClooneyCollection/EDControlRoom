# Iteration Log

- Area: `control-room`
- Title: `preserve-observer-search-prefill`
- Started: `2026-06-30 17:26`

## Summary

- Investigated the `control_room connect` regression where `haul search <system>` can open the observer-local prompt with the correct placeholder but an empty command bar instead of the prefilled serialized Inara params; the attempted fix passed harness coverage but did not resolve the live bug.

## Changes

- Narrowed observer prompt-state capture so a brand-new local prompt keeps the generated prefill text unless the client is already editing that same prompt instance.
- Kept the earlier live-edit sync for ongoing observer prompt edits, so connect-mode caret and text preservation still work after the initial prompt opens.
- Delayed command-bar clearing for observer-local prompt-opening commands like `haul search` so the prompt helper can populate the field before any blank-state cleanup runs.
- Added regression coverage for the new-prompt blank-widget case alongside the existing observer prompt-edit preservation tests, but the live `connect` flow still reproduces the empty-prefill issue and needs deeper event-order debugging.

## Follow-ups

- Reproduce the live `connect`-mode empty-prefill path with targeted debug logging around `Input.Submitted`, `Input.Changed`, and observer prompt-state capture so the actual Textual event ordering is visible.
