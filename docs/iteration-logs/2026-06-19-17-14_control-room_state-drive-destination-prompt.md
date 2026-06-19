# Iteration Log

- Area: `control-room`
- Title: `state-drive-destination-prompt`
- Started: `2026-06-19 17:14`

## Summary

- Moved destination-prompt submission off the backend’s inline field-mutation path and into explicit `PromptState` helpers, which gives the remote architecture a cleaner prompt-state seam ahead of the larger haul wizard migration.

## Changes

- Added `begin_destination_prompt`, `resolve_destination_prompt_submission`, and `clear_destination_prompt` helpers in `edap/control_room/prompts.py` that operate directly on `PromptState`.
- Updated `start_dest_prompt` and prompt cancellation to reuse those state helpers, so destination-prompt state reset/dispatch logic is no longer open-coded in multiple places.
- Changed `LocalControlRoomBackend.submit_input()` to resolve destination-prompt submissions through the new prompt-state helper and dispatch the resulting `DestinationPromptDispatch` instead of editing destination prompt fields inline.
- Added direct prompt-state tests for successful and invalid destination-prompt submission paths.
- Verified with `uv run python3 -m unittest discover -s tests` (`481 tests in 0.211s`).

## Follow-ups

- Move the multi-step haul prompt onto the same explicit prompt-state transition model so remote prompt orchestration no longer depends on headless-app-local branching for wizard progression.
- Decide whether replay navigation should get explicit server-native commands or remain a widget-mirrored client concern after the haul prompt work lands.
