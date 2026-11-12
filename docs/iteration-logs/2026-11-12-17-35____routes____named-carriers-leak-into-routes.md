# Iteration Log

- Area: `routes`
- Title: `named-carriers-leak-into-routes`
- Started: `2026-11-12 17:35`

## Summary

- The Global routes view showed fleet carrier VAON (Greae Hype LK-C d14-561) with "Fleet carriers" unchecked.
- Cause: commodity messages carry no station type, so `market.is_carrier` comes from the callsign pattern only. Each newer commodity message rewrites the row and clears the flag for a carrier with a custom name. The station table still had `FleetCarrier`. About 120 of 2,152 carrier markets in the local store had lost the flag.

## Changes

- `load_route_markets` also treats station type `FleetCarrier` as a carrier, with a regression test.

## Follow-ups

- `market.is_carrier` stays wrong in the store; fix it at write time if another reader starts relying on it.
