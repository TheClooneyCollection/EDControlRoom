# Iteration Log

- Area: `haul`
- Title: `reopen-market-on-station-check`
- Started: `2026-11-09 08:31`

## Summary

- A haul at Melroy Gateway failed the market station check although the station was right: the market never opened, and the retries only re-read the stale `Market.json`. Restarting the haul worked because it navigated again.

## Changes

- Deck journal 2026-11-09: `Docked` 08:14:10, open-market presses 08:14:16 to 08:14:23, no `Market` event until the haul was restarted (08:15:23). The operator saw station services open but not the market.
- Docked-to-first-`Market` gaps over 11/08 to 11/09 journals: Melroy Gateway (Coriolis) 4 of 24 over 40s, Voltaire Terminal (Dodec) 1 of 21. Both legs start pressing about 6s after `Docked`.
- `edap/routines/market.py`: navigation and the station check moved into `_open_commodities_market` and `_check_market_station`; each of the 3 attempts now backs out and navigates again. The failure reason text is unchanged, so the operator-facing mismatch message still applies.

## Follow-ups

- If lost presses keep showing up, wait for the services screen (a longer settle after a fresh `Docked`) rather than adding more attempts.
- Meaney Depot (2026-11-08 23:16 failure) has no `Market` event in the journals; not investigated.
