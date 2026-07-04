# Iteration Log

- Area: `web`
- Title: `empty-haul-results-layout`
- Started: `2026-07-04 10:34`

## Summary

- Removed static haul route seed data and widened the results area by stacking selected route controls under search.

## Changes

- `/haul` route results now start empty with a neutral prompt until websocket search returns data.
- Moved the selected route/start panel into a left-side stack below haul search, leaving the right column for a wider route results table.
- Added a responsive single-column fallback for narrower viewports.

## Follow-ups

- Recheck route table width after the next live search result shape changes.
