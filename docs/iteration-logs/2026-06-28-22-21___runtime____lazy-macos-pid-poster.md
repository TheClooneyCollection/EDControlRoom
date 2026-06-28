# Iteration Log

- Area: `runtime`
- Title: `lazy-macos-pid-poster`
- Started: `2026-06-28 22:21`

## Summary

- Fixed the macOS targeted-input test path so non-macOS runners no longer fail just by constructing the macOS controller during injected unit tests.

## Changes

- Changed `MacOSInputController` to lazily create the pid-targeted Quartz poster only when pid-targeted dispatch is actually attempted.
- Kept foreground macOS behavior unchanged while preserving the existing runtime error when pid-targeted Quartz posting is unavailable.
- Re-ran the focused macOS tests and the full unittest suite after the constructor change.

## Follow-ups

- Keep pid-targeted behavior covered through injected macOS unit tests, but avoid adding new tests that depend on Quartz pid posting existing on non-macOS CI runners.
