# Iteration Log

- Area: `control-room`
- Title: `hub-command-centre-plan`
- Started: `2026-11-11 11:53`

## Summary

- Wrote plan 0015 (`docs/plans/0015-hub-command-centre.md`): the hub becomes the one control room. Peers keep an outbound websocket link to it, send markets, haul runs, state and activity up, and run commands the hub sends down. Hub pages pick a node and reuse the existing session protocol over the link.
- Confirmed with the user: the hub is also a playable node, peers keep their own pages as a fallback, LAN only with the hub token, and a peer obeys only the hub it connected to.

## Changes

- New plan 0015; control-room status points at it from the hub bullet.

## Follow-ups

- Build phase 1 (peer link, node registry, link state replaces the heartbeat) once the user approves the plan.
- Open: TTS on the hub for the selected node, how "game running" is detected.
