# Iteration Log

- Area: `haul`
- Title: `sell-final-web-routine-step`
- Started: `2026-07-05 07:36`

## Summary

- Reordered the Haul Web V1 active routine timeline so sell is presented as the final step in a hauling leg.

## Changes

- Updated `web/haul-v1.html` to display `Buy -> Undock -> Depart -> Transit -> Sell`.
- Updated the routine panel phase completion order to match the displayed timeline.
- Added a focused static web test that asserts sell remains the fifth/final displayed step and that the JavaScript phase order matches.

## Follow-ups

- No server or protocol changes appear necessary; the existing hydrate phase names are sufficient for the frontend order change.
