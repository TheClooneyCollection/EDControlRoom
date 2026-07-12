# Iteration Log

- Area: `travel`
- Title: `spansh-route-tts-and-layout`
- Started: `2026-07-13 02:53`

## Summary

- Follow-up on the v1 Spansh route comparison surface: wire the real TTS pipeline and hoist the panel to full width.
- TTS now flows through the existing broker/AnnouncementEvent path so every connected observer speaks locally via `edap/tts.py`, matching how other server-initiated announcements fan out. The browser `window.speechSynthesis` path is gone.
- Route Comparison panel is no longer stuck in the narrow left-stack column; it renders as its own full-width section above the layout grid.

## Changes

- `edap/tts.py`, `defaults/tts.toml` — new `AnnouncementId.SPANSH_ROUTE_READY` + default phrase template using `{title}`, `{jump_summary}`, `{neutron_summary}`.
- `edap/routing/comparison.py` — expose `jump_summary` and `neutron_summary` on `RouteComparison` so the server can pass structured `message_values` to clients for local re-rendering.
- `edap/control_room/server/app.py` — `/api/route-compare` now publishes an `AnnouncementEvent` through the broker after a successful comparison (fixture or live).
- `web/haul-v1.html`, `web/haul-ui.css` — Route Comparison panel hoisted out of `.left-stack` into a top-level `.route-compare-full` section inside `<main>`; field-row wraps on narrow widths.
- `web/route-compare.js` — removed `speakOnce`/`window.speechSynthesis`; TTS is now server-driven.
- Tests: extended `test_route_comparison.py` for the new summary fields and `test_route_compare_endpoint.py` for the broker-published announcement. Full suite 758 tests, 0.344s.

## Follow-ups

- Wire the route-compare panel's supercharge default to ship state's `supercharge_multiplier` and prefill From/Range from current system + `Loadout.MaxJumpRange` (still parked from v1).
- Neutron travel routine to fly each Spansh waypoint (still parked; would enable the disabled "Switch to Spansh" button).
- Live-validate the TTS fan-out under CrossOver/macOS with two observers connected.
