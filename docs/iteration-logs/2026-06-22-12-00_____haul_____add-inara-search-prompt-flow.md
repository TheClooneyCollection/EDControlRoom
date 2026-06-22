# Iteration Log

- Area: `haul`
- Title: `add-inara-search-prompt-flow`
- Started: `2026-06-22 12:00`

## Summary

- Finished the first operator-facing Inara search workflow for Control Room: prompt-driven `haul search [system]`, direct `haul search url <inara-url>`, local ignored `haul_search.toml` defaults, and replay/default-haul separation for search history entries.

## Changes

- Added named Inara search-parameter mapping and URL parsing so Control Room no longer depends on raw `pi*` keys outside the shared helper layer.
- Added ignored local `haul_search.toml` support plus search-config parsing, with cargo capacity inferred from the current ship when available instead of being pinned in the config file.
- Extended the haul prompt state machine, protocol snapshot, replay flow, and history/default-haul rules so search prompts/edit replay behave like first-class Control Room flows without polluting saved default loop hauls.
- Expanded tests for the new config loader, search prompt submission, direct pasted-URL execution, and state-load rejection of saved search entries as default hauls.

## Follow-ups

- Live-validate the prompt defaults and direct URL flow against a real Inara session, then decide whether `pi14` / `pi15` should stay pinned passthrough defaults or become explicit Powerplay prompt fields.
