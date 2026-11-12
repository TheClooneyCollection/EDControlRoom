# Iteration Log

- Area: `routes`
- Title: `carrier-access-filter`
- Started: `2026-11-12 18:08`

## Summary

- `/routes` shows fleet carriers by display name and docking access, and hides carriers known not to be open to all by default.
- Sources: commodity/3 `carrierDockingAccess` (only on uploads made from Market.json; a 45 s live sample had 1 carrier with it) and `fsssignaldiscovered/1` carrier signals (`<name> <callsign>`; 685 names in the same 45 s).

## Changes

- New tables `carrier_access (market_id, access)` and `carrier_name (callsign, name)`, created with `IF NOT EXISTS`, so an existing DB opens unchanged (checked on a copy of the 56 MB local DB). Prune leaves them alone.
- Access: newest timestamp wins, a message without the field leaves it alone. Our own Market.json captures carry `CarrierDockingAccess` through `recent_markets` (and so through a peer's push).
- Names: the upsert writes only when the name changed, since the same signals repeat many times a minute.
- `RouteFilters.carriers_open_only` from the `carrier_access` param (`all` default, `any`); `resolve_route_params` passes it to a hub. Payload stations add `is_carrier`, `carrier_access`, `carrier_name`.
- Page: **Open to all only** checkbox next to Fleet carriers (on, disabled while carriers are off); station line shows `NAME (CALLSIGN)` and the access label or `access unknown`.

## Follow-ups

- Most carriers stay `access unknown` until someone uploads their Market.json; a Spansh dump seed is possible but 4.6 GB.
- /haul and Copy still use the callsign as the station name, which is what the game navigates by.
