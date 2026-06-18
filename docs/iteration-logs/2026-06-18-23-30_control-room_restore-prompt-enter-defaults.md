# Iteration Log

- Area: `control-room`
- Title: `restore-prompt-enter-defaults`
- Started: `2026-06-18 23:30`

## Summary

- Restored prompt-default Enter handling for Control Room prompts by catching blank Enter at the key-event layer and routing it through backend prompt submission.
- Verified the fix for both embedded and connected active-operator flows by keeping blank `raw_input` valid over the session transport and covering both paths with focused tests.

## Changes

- Updated `ControlRoomApp.on_key()` to submit empty prompt input on `Enter` during destination/haul prompt flows instead of relying on widget-level submitted events.
- Kept `on_input_submitted()` prompt-aware so non-empty and already-submitted prompt values still route through the backend without normal command-mode stripping.
- Added protocol/UI regression coverage for blank Enter during destination prompts and server-side coverage for active-operator command submission handling.

## Follow-ups

- Live-test connected active-operator prompt flows against a running `serve` instance, especially multi-step haul prompts and other prompt-heavy commands.
