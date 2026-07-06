# Travel Status
## Current
- `travel <system> / <station>` starts a server-first assistive station travel routine exposed through Control Room TUI and websocket `command.dispatch_travel`.
- TUI haul search results support `t` to save the highlighted route and start `travel` to its first station; the `/haul` web Travel Assist fields autofill to the selected route's first station.
- Travel can launch from docked state, depart from normal space, continue from supercruise, set a galaxy-map route for other-system targets, and then reuse shared station transit/docking behavior.
- In-system travel reuses the haul-style arrival path: announce the target station, open the left/nav panel when configured, then wait for supercruise drop and request docking.
- Shared station transit, route retry/unconfirmed-route handling, manual surface handoff, and interdiction abort behavior live in `edap.routines.transit` for travel, two-way haul, and multi-leg haul.
- The `/haul` web surface includes a compact Travel Assist form that sends structured travel dispatch; a dedicated `/travel` page is not implemented.
## Caveats
- Live validation is still needed for all start states under CrossOver/macOS, especially docked launch into same-system station travel and multi-jump resume.
- Surface/on-land travel currently inherits manual landing handoff behavior; settlement approach automation is not implemented.
## Next
- Live-validate `travel` from docked, same-system supercruise, normal-space, and remote-system starts before expanding the web UI or adding route-search handoff affordances.
