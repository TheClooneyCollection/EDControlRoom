# Iteration Log

- Area: `control-room`
- Title: `routes-mobile-layout`
- Started: `2026-11-11 05:58`

## Summary

- `/routes` is usable on a phone: each route is a labelled card instead of a 760 px table that scrolled sideways, and the mobile nav row no longer draws the brand name over the links on every page.

## Changes

- `haul-ui.css` already turns `.route-table` rows into cards at ≤760 px for `/haul`, but `/routes` reused the class with its own `min-width: 760px`, `nowrap` and right-aligned cells, no `data-label`s, and a `<br>` between the two stations. `web/routes.js` now labels every cell and wraps each station in a `<div>`; `web/routes.html` drops the wide-table rules under the same breakpoint.
- Mobile nav: `.brand` had `min-width: 0` in the scrolling flex row, so it shrank to nothing and its "Control Room" text spilled over "Two-way haul". It now keeps its size and shows only the ED mark.
- Checked with Playwright at 390 px against the live server's assets and a mocked `/api/eddn-routes` built from the local EDDN DB: page `scrollWidth` 390, cards readable, nav clear on `/haul`, `/multi-haul`, `/markets`, `/routes`, `/controls`.

## Follow-ups

- Not tried on a real phone yet.
