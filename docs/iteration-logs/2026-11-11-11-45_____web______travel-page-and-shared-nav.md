# Iteration Log

- Area: `web`
- Title: `travel-page-and-shared-nav`
- Started: `2026-11-11 11:45`

## Summary

- New `/travel` page holds the Active route and Route Comparison panels, moved off `/haul`.
- The sidebar link list now lives once in `web/nav.js` and every page renders it; `/haul` had lost its Multi-leg haul link because each page carried its own copy.
- Phones (<= 760px) show Two-way haul, Markets, Routes and Controls in the top row and a ☰ More menu for the rest.
- Activity text no longer shows a literal `[/]`: `stripMarkup` required at least one character inside the brackets.

## Changes

- `web/travel.html` + `web/travel.js`: same shell as `/controls` (token box, status foot, Hub chip, docked activity log). `travel.js` owns the websocket and provides the `window.EDCR_HAUL` bridge (`sendCommand`, `galmapSettleTime`, `shipState`, `lastHydrate`) and the `edcr:hydrate` / `edcr:ship-state` events, so `active-route.js` and `route-compare.js` run unchanged. Galaxy-map settle comes from `web_form_defaults.galaxyMapSettle`, since the haul form field is not on this page.
- `web/nav.js`: one `NAV_GROUPS` list; items with `mobile: true` stay in the phone row, the rest get `nav-desktop-only` and a copy in the More menu. Loaded without `defer` right after `<nav id="site-nav">` so there is no flash. `/` counts as `/haul` for `aria-current`. The menu is `position: fixed` because the phone nav row scrolls sideways and would clip it; Escape closes and refocuses the toggle, outside click and focus leaving close it. Below 480px the More label is visually hidden to fit the row at 390px.
- `.active-spansh-empty.hidden` / `.active-spansh-content.hidden` had no CSS rule, so the idle Active route card also showed empty metrics on `/haul`; added the rule.
- Server: `GET /travel`, and `travel.js` / `nav.js` added to the asset allowlist.
- README and `docs/user/getting-started.md` point at `/travel` for the Spansh panels.

## Verification

- Full suite passed (1082 tests, about 0.655s; the budget of 0.649s was already exceeded before this change and is being fixed separately).
- Headless Chrome over DevTools at 1400x850 and an emulated 390x844 on all six pages against a fixture server: correct `aria-current`, full list on desktop, four items plus More on phones, no horizontal page scroll, More opens by Enter and click, Escape closes and refocuses, outside click closes. The Travel page connected, hydrated and prefilled From.

## Follow-ups

- Try `/travel` against a live session: All in one, Switch to Spansh, and the Active route updating while the runner flies.
