# Iteration Log

- Area: `web`
- Title: `simplify-route-start-panel`
- Started: `2026-07-04 10:57`

## Summary

- Simplified the haul v1 start panel so it acts as route launch controls instead of duplicating route details.

## Changes

- Removed the selected-route stats table, endpoint support banner, and backend command callout from the start panel.
- Renamed the panel to `Start route`, the action button to `Start route`, and the timing controls to `Galmap settle time` and `Transit wait time`.
- Kept selected-route details in the results table and selected-route title only.

## Follow-ups

- Re-check the compact start panel with live results once the route table layout settles.
