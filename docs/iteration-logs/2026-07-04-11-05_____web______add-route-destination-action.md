# Iteration Log

- Area: `web`
- Title: `add-route-destination-action`
- Started: `2026-07-04 11:05`

## Summary

- Added a web Haul v1 action to set the galaxy-map destination from the selected route before starting haul.

## Changes

- Added a `Set destination` button beside `Start route` in the start panel.
- Wired the button to websocket `command.dispatch_destination` using the selected route's Station 1 system, matching the existing route-picker `d` shortcut behavior.
- Reused the `Galmap settle time` input for destination dispatch and kept active-operator/token guardrails aligned with route start.

## Follow-ups

- Live-check the action against a running server to confirm route selection, galaxy map timing, and activity feedback feel right before start-route handoff.
