# Iteration Log

- Area: `haul`
- Title: `routes-filter-toggles`
- Started: `2026-11-11 06:47`

## Summary

- `/routes` shows the haul search defaults its blank fields use, and Min supply, Max station distance and Max data age each get a tick box to turn the filter off.

## Changes

- Why: the Min supply field showed only `haul_search`, so the 5000 default that hid Chauhan Dock beryllium (about 4,000 t in stock) was invisible.
- Placeholders read `<value> (haul search)` for laden jump range (`max_route_distance_ly`), min supply, max station distance and max data age, and `<value> (ship)` for cargo. Web defaults gain `maxPriceAgeHours` from `max_price_age_hours`.
- Unticked filters send `any`: min supply 0 and no station distance limit as before. `max_age_hours=any` now lifts the age limit (finite `_NO_AGE_LIMIT_S`, since the query is echoed as JSON) instead of falling back to 48 h. Tick state is kept per browser in localStorage; a toggle reruns the search.
- Form fields are bottom-aligned so the wrapping Max station distance label does not push its input down.

## Follow-ups

- The Max data age placeholder and `any` age need a server restart; until then it shows `haul_search` and `any` means 48 h.
