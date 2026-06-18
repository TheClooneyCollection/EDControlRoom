# Iteration Log

- Area: `haul`
- Title: `haul-load-config`
- Started: `2026-06-18 07:36`

## Summary

- Added a repo-root `haul.toml` profile plus a `haul load [path]` command path so operators can edit one text file and launch the existing two-way haul routine without the multi-step prompt.

## Changes

- Added `edap/haul_config.py` to parse a small TOML haul profile into the same parameter keys used by the existing haul dispatcher.
- Added repo-root `haul.toml` as the default editable profile file for `haul load`.
- Updated Control Room haul help, command placeholder text, and the haul launcher so `haul load` can read `haul.toml` or an explicit TOML path and then dispatch the standard two-way routine.
- Added unit coverage for haul profile parsing and for Control Room `haul load` success, default-path, missing-file, and help-text behavior.

## Follow-ups

- Live-validate the `haul load` flow in Control Room against a real edited `haul.toml` profile to confirm the operator-facing log wording and launch ergonomics.
