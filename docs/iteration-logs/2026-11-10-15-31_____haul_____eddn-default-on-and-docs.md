# Iteration Log

- Area: `haul`
- Title: `eddn-default-on-and-docs`
- Started: `2026-11-10 15:31`

## Summary

- EDDN listening is on by default, the server logs a periodic status line, `/routes` shows a live listener log, and players have docs for it. README gained a Piper voice section.

## Changes

- `EddnConfig.enabled` and `defaults/eddn.toml` now default to true; new `eddn.status_every_s` (30 s, 0 turns it off, negative rejected).
- `status_line` moved from `tools/eddn_listen.py` into `edap/eddn/service.py`; `EddnService` runs an `eddn-status` thread that logs `EDDN connected: N msgs, ... | db N markets, ...` through the `edap.eddn` logger, stopped by `close()`.
- `/routes`: EDDN listener panel polls `/api/eddn-status` every 10 s and prepends one line per check (deltas since the last check, errors, reconnects, DB totals), capped at 60 lines.
- Docs: `docs/user/trade-routes.md` (indexed in `docs/user/README.md`), README "Trade routes (EDDN)" block and new "Piper Voice" section with TOC entry, `config.example.toml` EDDN comments.
- `TimeModel` checked against today's Chauhan Dock (Crater Outpost, 292 Ls) ↔ The Job Centre (2 Ls) loop, 1 jump each way: legs to the Job Centre averaged 302s vs 296s modeled, legs to Chauhan ~390s vs 366s, docked ~90 to 120s. Added `surface_extra_s = 30` for legs ending at a surface station; `leg_s` now takes `surface=`. Inara listed Chauhan at 3214 Ls, the journal and EDDN say 292 Ls. Handh is not in the EDDN DB yet, so `/routes` cannot show this route.
- Removed the now redundant `[eddn] enabled = true` block from the local `config.toml`.

## Follow-ups

- Restart the running server to pick up the status line, then check the `/routes` log panel live.
