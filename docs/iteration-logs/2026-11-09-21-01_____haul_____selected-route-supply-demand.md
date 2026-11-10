# Iteration Log

- Area: `haul`
- Title: `selected-route-supply-demand`
- Started: `2026-11-09 21:01`

## Summary

- The first `/haul` search result showed `-` for supply and demand. After a search the page selects route 1 and sends it to the server; the server's route parser dropped `from_supply`/`from_demand`/`to_supply`/`to_demand`, and the next hydrate merged that stripped route over the search result.
- Separately, the TUI `haul search` rejected a decimal route distance (`17.2`) that the web page had saved to `haul_search.toml`, so the prompt failed for anyone who searched from the web with a jump-range preset.

## Changes

- `edap/control_room/server/commands.py` and `edap/control_room/protocol/data_messages.py`: route parsers keep the four supply/demand fields, so selected/running routes keep them through select, hydrate and `connect`.
- `edap/control_room/prompts.py`: `parse_optional_nonnegative_number_text` accepts any non-negative number for max route distance and keeps the text as typed.
- Tests: server select test and data-message round trip check supply/demand; new TUI test for a decimal route distance.

## Follow-ups

- TUI haul search tests read the real working-directory `haul_search.toml`, so a local web search can change their results; isolate them from that file.
