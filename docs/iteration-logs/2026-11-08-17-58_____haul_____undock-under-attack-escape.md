# Iteration Log

- Area: `haul`
- Title: `undock-under-attack-escape`
- Started: `2026-11-08 17:58`

## Summary

- Steam Deck journal `Journal.2026-11-08T124339.01.log`: at Voltaire Terminal (A. Lavigny-Duval space) Power Security Force attacks on approach and launch. `Combat_Dogfight` music replaces the post-undock `NoTrack`, so the haul waited on a 600s timeout; at 15:04 the ship never left the no-fire zone and died at 15:08 after shields dropped.
- `ReceiveText` `$STATION_NoFireZone_exited;` fires on every launch, 20-45s after `NoTrack` on normal launches, and is the only clear cue under combat music.
- Normal auto-launch reaches `NoTrack` about 37s after `Undocked`, so boosting earlier risks the slot; the flee gate is 40s unless damage lands first.

## Changes

- No-fire-zone exit is a clear-of-station cue in the routine wait and both ship-state reducers.
- `_wait_for_clear_of_station` watches `UnderAttack` (Target `You`), `ShieldState` down and player `HullDamage`, calls a required `threat_fn` once (TTS `under_attack`), and returns `UnderAttack` on damage, on a clear cue while threatened, or 40s after `Undocked` (`undocked_at` now in the undock result details).
- Transit escape: mass-lock boost, hardpoint guard, `Supercruise` (new optional binding, Deck keymap `F8`; falls back to `HyperSuperCombination`), wait up to 45s for `SupercruiseEntry`/hyperspace `StartJump`, then TTS `supercruise_escape_align` and leave the jump to the pilot. Timeout aborts with `haul_aborted`. Standalone `undock` takes `announce_fn` and stops with an error for manual control.

## Follow-ups

- Live-validate the escape on Deck after rerunning `tools/deck_keymap.py --write` so `Supercruise` has a keyboard key.
- Attacks during approach/docking (seen 14:19 and 17:33) are not handled.
