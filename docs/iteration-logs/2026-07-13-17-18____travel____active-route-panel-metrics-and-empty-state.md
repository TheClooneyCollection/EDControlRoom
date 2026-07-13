# Iteration Log

- Area: `travel`
- Title: `active-route-panel-metrics-and-empty-state`
- Started: `2026-07-13 17:18`

## Summary

- Fleshed out the `/haul` Active route panel so it stops looking like a stub. Idle state shows a dashed empty message pointing at Route Comparison. Active state renders a 5-waypoint window using the same `.routine-bar`/`.step` styling as the Active haul routine card (done/current highlighting, neutron `· N` label suffix), a compact `last -> current -> next` inline summary, and three `.metric` tiles for Jumps / LY / Boosts remaining. The panel header now shows `N of M jumps` instead of a summary string. Cleaned up Route Comparison by removing the `beta` tag and the two fixture-load buttons (the `?fixture=` REST param stays for offline dev).

## Changes

- `web/haul-v1.html`: Active route panel rewritten (empty-state block + content block with waypoint bar and mini-metrics). Removed `beta` tag on Route Comparison. Removed `rc-fixture-normal` / `rc-fixture-overcharge` buttons.
- `web/active-route.js`: rewritten to render the 5-waypoint centered window (clamped to route bounds), compute remaining jumps / LY / boosts from waypoint tail, and toggle empty vs content state. `Off route` and `Arrived` are handled explicitly in the status pill.
- `web/haul-ui.css`: `.active-spansh-empty` styling for the idle card; dropped `.active-spansh-gap` (no longer used); tightened `.active-spansh-line` spacing to sit below the waypoint bar.
- `web/route-compare.js`: dropped the two fixture button handlers alongside the removed HTML buttons.

## Follow-ups

- No hydrate is currently emitted when a Spansh route finishes or is cancelled; the panel will show `Arrived` once the last waypoint matches ship system but stays populated afterwards. A future step should clear `set_active_spansh_route(None)` on routine completion / operator stop.
- Live-validate the enhanced panel under CrossOver/macOS on a real Spansh run and verify the waypoint window scrolls correctly across mid-route hops.
