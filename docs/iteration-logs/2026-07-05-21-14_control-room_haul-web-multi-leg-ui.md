# Iteration Log

- Area: `control-room`
- Title: `haul-web-multi-leg-ui`
- Started: `2026-07-05 21:14`

## Summary

- Reworked the haul web surface toward Spansh-style planner inputs/results and added a UI-only multi-leg haul page.

## Changes

- Split `web/haul-v1.html` into shared `haul-ui.css` / `haul-ui.js` assets served under `/assets/...` with no-store caching.
- Added `/multi-haul` as the same shared shell, with client-side view switching and a dedicated `command.dispatch_multi_leg_haul` websocket message path for future backend handling.
- Replaced the old route table renderer with Spansh-like result cards and commodity tables; active routine context now shows buy/sell/transit/next-sale secondary details.
- Kept existing two-way backend command payloads intact; two-way web `on_land` remains hardcoded false until surface metadata is reliable.

## Follow-ups

- Browser screenshot verification was blocked because no in-app or extension browser backend was available in this session; local server/curl and automated source/server tests passed.
- Backend support is still needed before the multi-leg page can run real Spansh calculations or dispatch live multi-leg routes.
