# Iteration Log

- Area: `control-room`
- Title: `serve-project-icon-as-favicon`
- Started: `2026-11-13 10:00`

## Summary

- Web pages now use the project icon (`assets/logos/hyperspace-trail-icon.png`) as their favicon and iOS home screen icon.

## Changes

- `web/favicon.png` (64 px) and `web/apple-touch-icon.png` (180 px) are resized from the logo with `sips -Z`. Every page links both, `/assets/` serves them as `image/png` (assets now read as bytes), and `/favicon.ico` returns the PNG.

## Follow-ups

- Regenerate both PNGs if the logo changes.
