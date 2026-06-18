# Haul Status
## Current
- Market buy/sell quantity restore is now configurable: buy `MAX` has a configurable hold cap plus linear/log timing modes, and sell `MAX` now restores quantity with configurable rapid `UI_Right` taps instead of a long hold.
- Two-way haul prompt/dispatch now records per-destination `on land` flags; orbital stops still auto-dock, while on-land stops hand off after destination-system `SupercruiseExit` so the operator can finish the planetary approach and resume after landing.
- Two-way and multi-leg transit now ignore intermediate `FSDJump` arrivals in multi-jump routes and only open the nav panel once the jump event matches the configured destination system.
- Haul prompt resume/edit now prefills the command input with the saved station names, systems, cargo legs, and timing values, and deleting a prefilled cargo/station field now leaves it truly blank instead of silently restoring saved text.
- Two-way `haul` now accepts one-sided loops: station 1 or station 2 buy cargo may be blank as long as the other side is configured, and the routine skips the missing buy/sell leg cleanly during prompt flow, launch, and resume detection.
- Two-way and multi-leg haul transit now announce the next station immediately after hyperspace arrival and before opening the nav panel, using a haul-specific TTS line instead of the generic `FSDJump` announcer.
- Market sell routines now merge the hidden-cargo subset from `Cargo.json` back into the demand-sorted `Market.json` sell list so hidden commodities no longer misindex later sale rows.
- Two-way `haul` remains the primary operator path.
- Standalone `multi_leg_haul` / `mult` handles finite external JSON or Spansh-driven routes without changing the two-way haul flow.
- Multi-leg resume derives state from live journal, cargo, and market data instead of persisted routine state.
## Caveats
- Orbital station automation still assumes `DockingGranted`/`Docked` on arrival and `Music` `NoTrack` as the clear-of-station cue after launch; `on land` only hands off for manual landing and does not automate settlement trading screens yet.
- One-sided haul loops still need live validation to confirm station-side UI timing and resume behavior when a station intentionally has no configured buy cargo.
- Multi-leg flow still needs live validation for repeated stations, consecutive trades, final-leg completion semantics, and external routes that mark surface destinations with `on_land`.
## Next
- Live-validate multi-jump haul routes plus `on land` destinations to confirm the final-system arrival match and post-drop manual handoff behavior in live Odyssey/CrossOver runs.
