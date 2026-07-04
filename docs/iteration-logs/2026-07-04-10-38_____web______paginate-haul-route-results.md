# Iteration Log

- Area: `web`
- Title: `paginate-haul-route-results`
- Started: `2026-07-04 10:38`

## Summary

- Improved the haul v1 route results view so two-way cargo details are visible without opening the debug preview.

## Changes

- Renamed the result table endpoints to Station 1 and Station 2 and shows both Station 1 buy and Station 2 buy cargo in each row.
- Expanded selected route details with Station 1, Station 1 buy, Station 2, Station 2 buy, route distance, and station distance.
- Added client-side pagination for route results with 12 rows per page and disabled pager controls at the bounds.

## Follow-ups

- Backend pagination is not needed yet; the v1 page still receives the full search result payload and paginates locally.
