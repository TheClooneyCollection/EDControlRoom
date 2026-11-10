# Iteration Log

- Area: `haul`
- Title: `manual-landing-rename`
- Started: `2026-11-10 16:11`

## Summary

- The per-station haul `on_land` flag is renamed `manual_landing`. It only means "hand off after `SupercruiseExit` because the ship cannot glide close to the pad"; planetary ports dock automatically with it off (Chauhan Dock, `BodyType: "Planet"`, docked ~60s after the drop). "Surface" stays the name for station-on-a-planet concepts (Inara `pi4`, EDDN `is_surface`, `TimeModel.surface_extra_s`).

## Changes

- Renamed fields, params, TOML keys, JSON keys, web ids and labels (`from_manual_landing`, `station_N_manual_landing`, `nav-manual-landing`, "Manual landing (can't glide to the pad)").
- Old names still load: `manual_landing_from_payload` in `edap/inara/trade_routes.py` covers saved state, pasted routes and server commands; `haul_config.py`, `multi_leg_haul.py`, `routines_haul.py`, the travel handler and `haul-ui.js` fall back to `on_land` / `<side>_on_land`. Tests cover each path.
- `/routes` Copy no longer sets the flag from `is_surface`; it always emits `false`.
- User docs, status and the 15:41 log follow-up reworded to the glide meaning.

## Follow-ups

- `detect_transit_resume_state` (`edap/routines/transit.py`) returns `NONE` for a `SupercruiseExit` with `BodyType` other than `Station` when the flag is off, so resuming right after a drop at a planetary port (before `DockingRequested`) does not pick up `POST_DROP_NEAR_STATION`. Kept on purpose: the user wants resume to pick it up only once docking starts.
