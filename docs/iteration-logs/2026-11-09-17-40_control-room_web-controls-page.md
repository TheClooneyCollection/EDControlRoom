# Iteration Log

- Area: `control-room`
- Title: `web-controls-page`
- Started: `2026-11-09 17:40`

## Summary

- The web UI had no way to fire single routines (dock, undock, escape and so on), and `/haul` is already full, so a separate `/controls` button board was added.

## Changes

- `web/controls.html` + `web/controls.js`: Flight (undock, dock, jump, escape, boost x3), Market (buy/sell with commodity and amount, sell all cargo), Routine (pause, resume, stop after run, stop now, instant toggle, reload config, reload keymap) and an activity feed. Idle-only buttons send through the normal launch delay; routine controls skip it.
- Follow-up from review: panel heads show `Idle` / `Busy: <routine>` (with pause state) instead of a static `Idle only`, Flight gets a full-width red `STOP NOW` (cancels immediately, enabled only while a routine runs), and instant mode is an `aria-checked` switch instead of a button.
- Server: `/controls` route and `controls.js` asset; sidebar links from `/haul` and `/multi-haul`.
- Verified with a preview `serve` on 127.0.0.1:8799: page and asset return 200, websocket gives `active_operator` and hydrate carries ship and routine state. No browser click-through (Chrome extension not connected), no button pressed against the game.

## Follow-ups

- Try it in a browser on the Deck; in the preview check hydrate `ship.station` came back empty, so confirm the Station tile fills in when docked.
