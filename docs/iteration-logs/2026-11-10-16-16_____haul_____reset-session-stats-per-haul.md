# Iteration Log

- Area: `haul`
- Title: `reset-session-stats-per-haul`
- Started: `2026-11-10 16:16`

## Summary

- Haul session stats (timer, profit, runs, average run time) used to accumulate across hauls until `new_session`, which blurred how long runs take. The user asked for them to clear on stop.

## Changes

- `stop_haul_stats` sets `session_active = False` and logs `Haul session: N runs, X Cr in mm:ss, average run mm:ss`; the frozen numbers stay on screen.
- `start_haul_stats` starts from zero when the previous session is not active (a stopped haul, `stop_session`, or a fresh state), and still carries totals over when resuming after a relaunch mid-haul.
- Resume detection after a drop at a planetary port stays as is: the user only wants it picked up once docking starts (`DockingRequested`).

## Follow-ups

- If the user wants the panel blank right at stop instead of at the next start, clear in `stop_haul_stats` after the summary log.
