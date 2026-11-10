# Iteration Log

- Area: `haul`
- Title: `eddn-routes-ignore-demand`
- Started: `2026-11-10 16:32`

## Summary

- The best route in the EDDN store, Chauhan Dock ↔ Sitterly Enterprise (same system, beryllium out, insulating membrane back), was hidden by `min_demand = 5000`: Sitterly also produces beryllium, so EDDN shows demand 1, yet every haul run sold the full 1137 t there. The user confirmed any listed sell price is enough.
- With demand ignored, the finder ranks it first at 302M/h, 50.5M per trip, 10.0 min; the haul run log shows 308M/h and 9.8 min over 2 clean runs. Next best: Chauhan → Oracular Oriole silver at 214M/h; nothing without Chauhan beats ~146M/h.

## Changes

- `edap/eddn/routes.py` treats any `sell > 0` as a buyer; `RouteFilters.min_demand`, the `min_demand` query parameter and the `/routes` Min demand field are gone. Inara haul search keeps its own min demand.
- Test: a station listing a sell price with demand 1 is a route target.

## Follow-ups

- Selling a full hold where demand is tiny has only been seen at Sitterly; watch for price drops elsewhere.
