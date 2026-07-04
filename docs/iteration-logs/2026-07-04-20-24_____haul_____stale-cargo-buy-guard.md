# Iteration Log

- Area: `haul`
- Title: `stale-cargo-buy-guard`
- Started: `2026-07-04 20:24`

## Summary

- Fixed the live resume-haul failure mode where Elite reported loaded cargo in `Status.json` but stale/empty `Cargo.json` made the routine proceed into a buy phase.

## Changes

- Added commodity-name normalization for raw Elite inventory names such as `$palladium_name;` so haul phase detection and market sell quantity lookup match configured route commodities.
- Added a pre-buy stale-cargo guard: when `Status.json` reports cargo tonnage and `Cargo.json` has no sellable named cargo, two-way haul aborts before market input, logs a relog/resume message, and emits `haul_cargo_state_stale` TTS.
- Covered the stale-cargo abort and raw-name resume detection with unit tests, plus a config assertion for the `{title}`-prefixed default TTS phrase.

## Follow-ups

- Resume/session tracking still needs separate web/TUI work so stopped or restarted hauls do not clear stats inconsistently.
