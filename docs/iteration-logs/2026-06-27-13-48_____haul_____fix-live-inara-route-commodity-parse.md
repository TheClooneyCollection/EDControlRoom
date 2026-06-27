# Iteration Log

- Area: `haul`
- Title: `fix-live-inara-route-commodity-parse`
- Started: `2026-06-27 13:48`

## Summary

- Fixed `haul route <n>` for live Inara trade-route cards whose `FROM` and `TO` headers both appear before the station trade details.

## Changes

- Updated the shared Inara row parser to ignore `BUY PRICE` metric lines when extracting commodities and to derive source/return cargo from the ordered `BUY` commodity rows across the full card.
- Added a regression test that matches the live `HIP 17597` card shape where `BUY\tSilver` and `BUY PRICE\t3,420 Cr` appear after both endpoint headers.
- Re-ran the existing scratch Inara probe against the live `HIP 17597` query and confirmed the previous failure mode came from parser output, not missing site data.

## Follow-ups

- Live-check `haul route <n>` in Control Room against the repaired parser to confirm the prompt now prefills the expected station and cargo values from the real results panel.
