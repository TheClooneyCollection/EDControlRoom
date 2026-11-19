# Iteration Log

- Area: `eddn`
- Title: `eddn-listen-no-config`
- Started: `2026-11-19 22:51`

## Summary

- The standalone EDDN listener now starts without a local `config.toml`.

## Changes

- Use shipped `defaults/eddn.toml` only when local config is absent; existing config validation and CLI precedence remain unchanged. Other `load_config` callers still require their requested file.
- Extract the listening boundary as a plain injected function so five behavior tests run the real CLI/config entry path without sockets, threads or sleeping.
- Updated runtime handoff; the VPS operator guide has no instruction to create `config.toml`, so no correction was needed.
- Validation: targeted 5 tests passed; full suite 1292 tests in 1.062s, OK (1 skipped). Iteration archive rendered and filenames validated.

## Follow-ups

- Existing suite timing exceeds the 0.7752s target. Unmodified main baseline: 1287 tests in 1.086s (target 0.7722s). Required timing report passed; top five hotspots are existing haul web/two-way tests (~0.24s combined). No unrelated timing optimization included.
- No live EDDN relay verification; listener loop behavior is unchanged.
