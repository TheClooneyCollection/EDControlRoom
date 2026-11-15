# Projected session hourly earnings on /haul

## Changes
- The routine panel places Projected immediately after Current / Accumulated.
- Rate is `(accumulated_profit + current_run_profit) / session_elapsed_s * 3600`, formatted with the existing credits formatter as e.g. `~250.0m/h`. Using the session retains the rate when a new run starts before its first sale.
- Zero profit or missing/zero elapsed always displays `- (no sale yet)`; the metric remains visible. No fixed-horizon projection.
- The session metric grid auto-fits columns with a 180px minimum capped to available width; existing phone CSS still switches it to one column. Run-times grid remains unchanged.

## Validation
- Added source-level hooks/formula/fallback/responsive-grid assertions in `tests/test_control_room_haul_web.py`, matching existing style.
- `node --check web/haul-ui.js` passed. A temporary Node VM check of updateRoutinePanel verified session rate, new-run continuity, zero profit and zero/missing elapsed.
- Full suite: 1243 tests / 1.165s, OK (1 skipped); above 0.7458s timing budget. Required timing report suite_status=ok / 1.439s; no unrelated performance changes.
- No live deploy or browser visual check; phone behavior checked against existing media rules and the grid definition.
