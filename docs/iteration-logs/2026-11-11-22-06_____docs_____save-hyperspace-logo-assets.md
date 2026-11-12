# Iteration Log

- Area: `docs`
- Title: `save-hyperspace-logo-assets`
- Started: `2026-11-11 22:06`

## Summary

- Saved the user's selected Hyperspace Trail v2 logo family in `assets/logos/`.

## Changes

- Copied the amber icon, horizontal wordmark, and original monochrome master without modifying the images; `cmp` verified all three copies.
- Published only the README banner and its required image in commit `8fa52c5`, per the user's requested push scope; other working changes were excluded.
- Generated transparent light/dark wordmark variants; imagegen alpha extraction left speckles and broken white lettering on the first attempts.
- Commit `c20ec50` centers the README logo and serves `hyperspace-trail-wordmark-light.png` / `-dark.png` per color scheme.
- Commit `770867d` adds the icon and monochrome masters. The imagegen concept drafts in `output/` were discarded.

## Follow-ups

- If the light/dark wordmarks show artifacts on GitHub, regenerate cleaner transparent versions.
