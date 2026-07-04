# Iteration Log

- Area: `web`
- Title: `fix-haul-web-system-summary`
- Started: `2026-07-04 16:55`

## Summary

- Fixed the `/haul` summary strip so Home system comes from the configured `control_room.home_system`, while Current system comes only from the live ship system instead of falling back to station or market names.

## Changes

- Added `home_system` to the Control Room hydrate read model and payload parsing, with local data sources exporting the configured home system.
- Updated `web/haul-v1.html` to render `summary-home` from `payload.home_system`, render `summary-current` from `ship.system`, and use neutral static placeholders before hydrate.
- Added regression coverage for hydrate payload home-system export and the static web page's distinct home/current system rendering.

## Follow-ups

- Live-check `/haul` during an active CrossOver session to confirm refresh/reconnect now shows the configured home and the same current system as the terminal status panel.
