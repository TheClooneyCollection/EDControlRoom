# Iteration Log

- Area: `docs`
- Title: `readme-intro-screenshots-and-haul-loop-warning`
- Started: `2026-11-11 21:36`

## Summary

- README opens with three screenshots (Markets page, Routes page, integrated Inara search) above the tagline, in `docs/assets/screenshots/intro-*.png`. Machine names were replaced in the page before capture, and Inara's private-use trend glyphs (U+E84D / U+E84E, boxes in every browser) were stripped.
- The Terms of Use warning now covers only the assisted haul loops; other key-sending buttons are single actions left to the player's judgement.
- Assisted Haul Loop moved down to sit just above Documentation: the project leads with market intelligence and the hub. The hub section is now Hub: Connected Intelligence and says commands run on the picked peer from the hub's pages and `POST /api/command?node=`.
- The market intelligence bullet names the Markets and Routes pages and gives the database size (about 40 MB for 10,302 markets).

## Follow-ups

- The haul page shows Inara's supply and demand trend icons as boxes; mapping U+E84D / U+E84E to arrows in `web/haul-ui.js` would fix it.
