# Iteration Log

- Area: `control-room`
- Title: `expand-browser-remote-controls`
- Started: `2026-06-19 18:04`

## Summary

- Expanded the hosted browser probe so the web-client path can exercise replay-browser and prompt flows, not just basic command submission and discovery.

## Changes

- Added replay-browser controls for open/close, filter updates, selection movement, replay run/edit, and default-haul toggling using the same remote protocol commands as the Textual client.
- Added prompt-facing inputs for explicit and default submissions plus clearer prompt/routine/replay state rendering in the browser probe.
- Extended the browser-probe endpoint coverage and updated the remote operator docs/status handoff to reflect that the browser path now covers replay and prompt-heavy remote flows too.

## Follow-ups

- If a dedicated web client replaces the probe, keep the replay and prompt command paths explicit rather than tunneling widget-local behavior over the wire.
