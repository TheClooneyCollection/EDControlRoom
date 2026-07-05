# Iteration Log

- Area: `web`
- Title: `root-entry-point`
- Started: `2026-07-05 05:49`

## Summary

- Made the observer web root `/` serve the same haul web entry point as `/haul`.

## Changes

- Added a root route constant and mounted it to the existing haul web HTML handler, preserving the no-store response behavior and token injection path.
- Added server regression coverage for the root web entry point.
- Updated the Control Room status handoff to mention both web entry paths.

## Follow-ups

- None.
