# Iteration Log

- Area: `haul`
- Title: `complete-run-docked-by-hand`
- Started: `2026-11-12 11:50`

## Summary

- Live side-by-side test on forge (assisted haul plus a second Control Room in Track only). Docking at Chauhan Dock (station 1) was denied for distance, the haul ended and kept the run open, the commander docked by hand, then restarted the haul. The routine sold at station 1 but the run never completed: no `Docked` at station 1 reached the stats while the haul was ended, so `docked_back_at_station_1` stayed false. Stop after run then suspended the open run again, and neither run complete nor session complete TTS played.
- The Track only process stayed active the whole time and recorded the run as completed: 45,194,613 Cr profit, 772 s, matching the assisted run's trades exactly.

## Changes

- `start_haul_stats` continuing a suspended run while docked at station 1 after a clean departure sets `docked_back_at_station_1`, so the next station 1 sale completes it; if the run already holds a station 1 sale after a station 2 visit, it completes at once.
- The completed run's time stops where the haul ended; the hand-flown docking is not counted.

## Follow-ups

- Restarting a Control Room still aborts a kept-open run, so the forge run from this test stays in the Track only file only.
- A `Distance` docking denial retries in place; approaching before the retry is a possible follow-up.
