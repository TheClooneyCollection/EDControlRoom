# Iteration Log

- Area: `control-room`
- Title: `inara-supply-level-arrows`
- Started: `2026-11-11 21:42`

## Summary

- The haul page's Inara results showed boxes after supply and demand numbers. They are Inara's supply / demand level icons from its own icon font: U+E84E inside `supplydemandicon3` (high) and U+E84D inside `supplydemandicon0` (low or none). `marketAmount` in `web/haul-ui.js` shows them as ▲ / ▼ and drops any other private-use glyph. Only levels 0 and 3 were seen on a live results page; a level 1 or 2 glyph, if Inara has one, is dropped rather than guessed.
- README: the Screenshots section is gone (the intro screenshots replace it); `copy-paste-route-wide.png` and `travel-page.png` had no other reference and were removed. The intro Inara screenshot is now cropped to the same 1.6 ratio as the other two so the row lines up.
