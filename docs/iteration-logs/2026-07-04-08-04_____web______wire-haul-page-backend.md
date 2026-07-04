# Iteration Log

- Area: `web`
- Title: `wire-haul-page-backend`
- Started: `2026-07-04 08:04`

## Summary

- Wired the static Haul v1 page to the Control Room server with authenticated search and start endpoints.

## Changes

- Added `GET /haul` to serve `web/haul-v1.html` from `control_room.py serve`.
- Added `POST /api/haul/search` to run shared Inara route search, force station/carrier-only query params, optionally filter by destination, and return serialized route data.
- Added `POST /api/haul/start` to validate web haul params, reject surface destinations, default both `on_land` flags false, and call existing structured `dispatch_haul_loop`.
- Updated the Haul page to hydrate summary state, search live routes, render backend route data, and start the selected two-way haul.
- Removed unsupported supply/demand columns from the web route table for v1 because the current backend route model does not expose them as first-class fields.
- Added server regression tests for serving `/haul`, route search serialization, start dispatch, auth, and surface-destination rejection.

## Follow-ups

- Live-check `/haul?access_token=...` against a running server with the real Inara browser profile before treating the web search flow as operator-validated.
