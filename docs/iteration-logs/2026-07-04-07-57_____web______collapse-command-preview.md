# Iteration Log

- Area: `web`
- Title: `collapse-command-preview`
- Started: `2026-07-04 07:57`

## Summary

- Converted the selected route command preview into a collapsed debug disclosure.

## Changes

- Wrapped the existing command preview output in a native `details` section labeled `Debug command preview`.
- Added compact disclosure styling so debug params no longer occupy the default start panel layout.
- Kept the existing `command-preview` id intact for the current static JavaScript updater.

## Follow-ups

- Revisit debug affordances when backend integration lands and decide whether command previews should be hidden behind a developer mode.
