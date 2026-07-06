# Iteration Log

- Area: `web`
- Title: `editable-route-distance-defaults`
- Started: `2026-07-06 13:47`

## Summary

- Matched the `/haul` route-distance search control to INARA's visible preset values while keeping the field editable for custom distances.

## Changes

- Replaced the route-distance select in `web/haul-v1.html` with an editable text input paired with a visible preset selector containing `10 Ly`, `20 Ly`, `30 Ly`, `40 Ly`, `50 Ly`, `60 Ly`, `70 Ly`, `80 Ly`, `500 Ly`, and `1,000 Ly`.
- Updated `web/haul-ui.js` so search reset/default hydration writes directly to the editable route-distance input, formats numeric defaults with `Ly`, and copies selected presets into the input.
- Added styling for the joined input/preset control and web regression coverage proving the submitted value still comes from `max_route_distance_ly`.

## Follow-ups

- Live-check the hybrid route-distance control in the browser once the next `/haul` UI pass is running locally.
