# Iteration Log

- Area: `control-room`
- Title: `localize-remote-haul-and-dest-prompts`
- Started: `2026-06-30 12:34`

## Summary

- Rebased remote operator mode on the existing local `ControlRoomApp` prompt, replay, and market-panel flows for `haul`, `haul route`, `haul search`, `dest`, `home`, history replay/edit, and market lock/filter controls, so `connect` now resolves those operator-surface interactions locally and sends only finalized routine payloads to the headless server.

## Changes

- Added structured remote routine commands for finalized destination and haul launches, wired the remote backend to emit them, and taught the headless observer server to execute them without opening server-owned prompt sessions.
- Changed `ObserverControlRoomApp` to intercept prompt-owning commands locally, preserve local prompt state across snapshot refreshes, and load trade-route picker selections into the same local haul prompt used by embedded mode.
- Switched `connect` replay/history browsing to the existing local replay helpers, so open/filter/selection/edit/default-haul behavior now stays client-side while the remote snapshot remains the source of executed history entries.
- Removed the last remote prompt-prefill fallback in `connect`, so server snapshot prompt state no longer repopulates the local command bar when the client is not already in a local prompt flow.
- Aligned market lock semantics so embedded mode still ingests fresh `Market.json` data while locked, `connect` handles `market` commands locally, and both modes now treat lock/unlock as display freeze/unfreeze over a continuously updating underlying market source.
- Updated the checked-in control-room message schema plus client/server/protocol tests to cover the new dispatch commands and the new local-prompt/local-replay remote behavior.

## Follow-ups

- Trim the remote protocol snapshot/state model next so server-retained `prompt_state`, `replay_browser`, and related replay-filter/browser-open fields are no longer needed for `connect` compatibility.
- Consider the same cleanup for remote `market.locked` / remote market-filter snapshot fields now that `connect` owns those controls locally.
