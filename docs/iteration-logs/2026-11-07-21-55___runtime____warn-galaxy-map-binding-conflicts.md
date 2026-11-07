# Iteration Log

- Area: `runtime`
- Title: `warn-galaxy-map-binding-conflicts`
- Started: `2026-11-07 21:55`

## Summary

- Warn about galaxy-map camera/menu cursor chord conflicts and fix primary modifier carry-over into keyboard secondary bindings.

## Changes

- Added a pure parsed-tree conflict detector beside the bindings layer, comparing resolved UI_Up/Down/Left/Right keys plus modifiers against both keyboard slots of CamTranslate/CamYaw/CamPitch/CamZoom button actions. Axes, joystick inputs and different modifier chords are excluded.
- Reused the detector in Control Room startup and the check_bindings CLI. Warnings include the conflicting action and UI Mode arrow-key guidance; lookup/dispatch, existing issue counts and exit status remain unchanged. JSON adds a warnings list. Advisory file reread failures are ignored.
- Reset the modifier when selecting a keyboard secondary, then read only that slot's modifier. Keyboard secondary priority remains unchanged.
- Added 10 behavior tests including the four-direction WASD + VKB setup, arrow secondaries, differing/matching modifiers and aliases, all camera button families/slots, axes exclusion, startup logging, CLI text/JSON and modifier carry-over.
- Full unittest discovery: 931 tests passed in 2.372s. Sequential same-session baseline on unchanged main: 921 tests in 2.444s, so no regression is indicated despite exceeding the 0.5586s target. Required timing report ran (931 tests OK, 1.561s; slowest are existing helper/CLI/haul/timezone tests).
- Updated bindings setup guidance and runtime handoff; iteration archive regenerated and validation passed.

## Follow-ups

- Live operators should assign arrow-key secondaries in Elite when warned. This change never edits the user bindings file or blocks their routines.
