# Travel Status
## Current
- `/haul` "Route Comparison (beta)" panel is now a full-width section above the layout grid; the endpoint publishes an `AnnouncementEvent(spansh_route_ready)` through the broker so all connected observers speak the phrase via the existing TTS pipeline (browser SpeechSynthesis path removed).
- `/haul` includes a "Route Comparison (beta)" panel backed by `/api/route-compare` that renders the in-game `NavRoute.json` and a Spansh neutron plot side-by-side. `?fixture=hd232819_xinca_{normal,overcharge}` bypasses live sources for offline dev.
- Ship state now exposes `fsd_type` (`standard`/`sco`/`overcharge_mkii`) and `supercharge_multiplier` (4 or 6) from Loadout, detected by FSD module Item marker `overchargebooster_mkii`.
- `travel <system> [/ <station>]` starts server-first assistive travel; station is optional, and system-only travel stops after destination-system arrival instead of docking.
- TUI haul search results support `t` to save the highlighted route and start `travel` to its first station; the `/haul` web Travel Assist fields autofill from the selected route until manually edited or cleared.
- Travel can launch from docked state, depart from normal space, continue from supercruise, set a galaxy-map route for other-system targets, and reuse shared station transit/docking behavior when a station is provided.
- In-system travel reuses the haul-style arrival path: announce the target station, open the left/nav panel when configured, then wait for supercruise drop and request docking.
- Shared station transit, route retry/unconfirmed-route handling, manual surface handoff, and interdiction abort behavior live in `edap.routines.transit` for travel, two-way haul, and multi-leg haul.
- The `/haul` web surface includes a compact Travel Assist form that sends structured travel dispatch; a dedicated `/travel` page is not implemented.
## Caveats
- Live validation is still needed for all start states under CrossOver/macOS, especially docked launch into same-system station travel and multi-jump resume.
- Surface/on-land travel currently inherits manual landing handoff behavior; settlement approach automation is not implemented.
## Next
- Wire the route-compare panel's supercharge default to ship state's `supercharge_multiplier` and prefill From/Range from current system + `Loadout.MaxJumpRange`.
- Build the neutron travel routine that flies each Spansh waypoint (enables the disabled "Switch to Spansh" button).
- Live-validate `travel` from docked, same-system supercruise, normal-space, and remote-system starts before expanding the web UI or adding route-search handoff affordances.
