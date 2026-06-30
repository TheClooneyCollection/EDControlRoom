# Iteration Log

- Area: `control-room`
- Title: `fix-connect-remote-routine-readiness`
- Started: `2026-06-30 14:07`

## Summary

- Fixed `connect` mode so prompt-owning remote commands like `dest sol` no longer fail locally with `controls unavailable` before the client can collect prompt input.

## Changes

- Overrode observer routine readiness to check remote operator/routine state instead of local controls availability, which is intentionally absent on remote-only clients.
- Tightened observer tests so `dest` and `haul` prompt flows must work without setting fake local controls on the client.
- Live-validated against a real local `serve` process plus observer session: `dest sol` now opens the local settle-seconds prompt and does not log `controls unavailable`.

## Follow-ups

- Run one more manual pass against a real interactive `control_room connect` terminal to confirm the visible TUI behavior matches the automated observer-path probe.
