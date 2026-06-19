# Iteration Log

- Area: `control-room`
- Title: `state-drive-haul-prompt-edges`
- Started: `2026-06-19 17:18`

## Summary

- Moved the haul wizard’s entry, confirmation, and reset edges onto explicit `PromptState` helpers so the remote architecture no longer depends on open-coded haul prompt field mutation for those transitions.

## Changes

- Added `begin_haul_prompt`, `resolve_haul_confirm_prompt`, `clear_haul_prompt`, and `clear_haul_confirm_prompt` helpers in [edap/control_room/prompts.py](/Users/nicholasclooney/Source/Projects/EDControlRoom/edap/control_room/prompts.py) that operate directly on `PromptState`.
- Updated haul prompt start and confirmation handling to reuse those helpers instead of open-coding prompt field mutation inside UI handlers.
- Updated prompt cancellation to reuse the new haul prompt reset helpers rather than manually clearing haul prompt fields inline.
- Added direct prompt-state tests for haul prompt start, haul confirmation resolution, and haul prompt reset behavior.
- Verified with `uv run python3 -m unittest discover -s tests` (`484 tests in 0.218s`).

## Follow-ups

- Move the remaining per-step haul wizard body onto explicit prompt-state transition helpers so remote prompt orchestration no longer depends on headless-app-local branching for each wizard step.
- Decide whether replay navigation should get explicit server-native commands or remain a widget-mirrored client concern after the haul wizard body is moved.
