# Iteration Log

- Area: `control-room`
- Title: `hydrate-keeps-operator-edits`
- Started: `2026-11-09 20:01`

## Summary

- On `/haul` the operator could not reach route results page 2 or edit cargo capacity: every hydrate (sent on each journal change, so often during a haul) rewrote `origin` and `capacity` and re-merged the selected route, which reset the selection and the page and re-rendered the rows.

## Changes

- `web/haul-ui.js`: `syncHydratedField` refills `origin`/`capacity` only when the field is not focused and still holds the last hydrated value (or is empty), so operator edits stick until Reset.
- The selected/running route is merged only when its key differs from the last hydrated one, so repeat hydrates keep the operator's row and page and do not re-render rows under a tap. A merged existing route keeps its local index.

## Follow-ups

- `/multi-haul` `applyShipDefaults` has the same pattern (origin, capacity, capital refilled on every hydrate); not changed yet.
- Not reproduced in a browser: the local preview has no live journal churn, so verify on the Deck during a haul.
