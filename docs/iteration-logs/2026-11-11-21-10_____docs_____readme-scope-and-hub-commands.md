# Iteration Log

- Area: `docs`
- Title: `readme-scope-and-hub-commands`
- Started: `2026-11-11 21:10`

## Summary

- README: the Terms of Use warning is no longer a repo-wide banner. It sits in the Assisted Haul Loop section (was The Idea) and covers every routine that presses keys: haul loops, `/controls`, Set destination, Travel assist, the `/travel` runner and `dock` / `undock` / `jump`. Markets, routes, Best deal, history, the hub and voice read journals and public data and send nothing to the game.
- README intro now leads with the built-in market intelligence (EDDN database, `/routes`, Best deal with the trip time model and measured profit per hour), the hub, history and callouts, then the optional haul loop. New top-level Hub: Several Machines section; the Hub details block moved there.
- `control_room.py hub` and `control_room.py peer` run `lan` with that role, overriding `[hub] role` (`edap.config.with_hub_role`). An empty `[hub] token` falls back to the page token (`--token`, default `edcr`), so two machines need no config to link.

## Follow-ups

- `peer` takes no hub address argument; a fixed hub still goes in `[hub] url`.
