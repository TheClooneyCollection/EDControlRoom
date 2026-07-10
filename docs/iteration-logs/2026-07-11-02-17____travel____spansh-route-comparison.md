# Iteration Log

- Area: `travel`
- Title: `spansh-route-comparison`
- Started: `2026-07-11 02:17`

## Summary

- Landed v1 of the Spansh neutron route comparison surface per `docs/plans/0010`.
- New `/haul` panel "Route Comparison (beta)" renders in-game NavRoute.json against a Spansh plot side-by-side.
- Live and offline (fixture-backed) paths share the same rendering.
- Comparison verdict uses reduced jump count as the only tiebreak; TTS phrase surfaces "{title}, Spansh route came back and it saves/adds X jumps, with Y more/fewer neutron jumps, would you like to review?".
- Executed with three parallel Sonnet agents in worktrees for navroute parser, Spansh API client, and FSD-type detection; comparison layer, web endpoint, and panel done in the parent session.

## Changes

- `docs/plans/0010-spansh-neutron-route-comparison.md` — new plan doc.
- `tests/fixtures/routing/` — captured live NavRoute.json + Spansh normal/overcharge/queued responses.
- `edap/routing/{navroute,types,comparison,web}.py` — pure parsers + comparison + fixture/live glue.
- `edap/spansh_router.py` — httpx-based Spansh `/api/route` submit+poll client.
- `edap/state.py`, `edap/control_room/{models,events,dependencies,protocol/data_messages,app}.py` — new `fsd_type` (standard/sco/overcharge_mkii) + `supercharge_multiplier` fields plumbed from Loadout through the control-room read model. Detection is by FSD module Item string (`overchargebooster_mkii` marker), not ship name.
- `edap/control_room/server/{app,serve}.py` — new `/api/route-compare` endpoint with `?fixture=` support, wired to `journal_dir`.
- `web/haul-v1.html`, `web/haul-ui.css`, `web/route-compare.js` — new panel + inline JS + styles.
- Tests: `test_navroute.py`, `test_spansh_router.py`, `test_route_comparison.py`, `test_routing_web.py`, `test_route_compare_endpoint.py`; extended `test_state.py` and `test_control_room.py` for FSD detection. Full suite 757 tests, 0.309s.

## Follow-ups

- Neutron travel routine that flies each Spansh waypoint (parked; would enable the disabled "Switch to Spansh" button).
- Wire ship state's `supercharge_multiplier` into the panel's supercharge default so Caspian + Mk II SCO auto-picks Overcharge without operator toggling.
- Auto-prefill `From` from current system and `Range` from `Loadout.MaxJumpRange` in the panel form.
- Laden jump-range calculation for a more honest default when hauling cargo.
- TUI comparison view and modal to mirror the web surface.
- Live validation against Elite under CrossOver/macOS.
