# Iteration Log

- Area: `travel`
- Title: `fsd-charge-confirm-supercruise-fallback`
- Started: `2026-11-10 20:59`

## Summary

- Leaving Chauhan Dock, `HyperSuperCombination` does nothing when the station obscures the jump target (it only shows "Destination Target Obscured"; verified it never falls back to supercruise), yet TTS already said "Ready to jump". The auto engage now confirms the FSD is charging before saying that, and falls back to supercruise when it is not.

## Changes

- `engage_fsd_and_confirm_charging` in `edap/routines/transit.py`: say `fsd_engage_trying`, press `HyperSuperCombination`, poll Status.json `FsdCharging` (or `FsdJump`) for `FSD_CHARGE_CONFIRM_TIMEOUT_S = 4.0`. Charging: say `station_cleared`. Not charging from normal space (depart / undock paths): say `supercruise_fallback` and press `Supercruise`. Not charging from supercruise (`travel` supercruise start): say `fsd_jump_blocked` only, since `Supercruise` would drop the ship out. Unreadable Status.json: progress warning, no further TTS.
- Status.json is polled instead of waiting for the `StartJump` journal event so the wait does not consume journal events that the later arrival wait needs.
- New `AnnouncementId`s and `defaults/tts.toml` phrases: `fsd_engage_trying`, `supercruise_fallback`, `fsd_jump_blocked`. The `station_cleared` wording is unchanged.
- Follow-up wording: the blocked lines say "Frame shift drive failed to engage", and the normal-space fallback adds `supercruise_countdown` ("Engaging supercruise in 3, 2, 1.") and waits `SUPERCRUISE_FALLBACK_COUNTDOWN_S = 8.0` before pressing `Supercruise`, since queued TTS gives no completion signal.
- Tests: `tests/test_fsd_engage.py`; the hardpoint transit test now sets `FsdCharging` on the jump press.

## Follow-ups

- Live-validate at Chauhan Dock: the 4s window, that `FsdCharging` shows up promptly under CrossOver, and the target swap after the supercruise fallback.
