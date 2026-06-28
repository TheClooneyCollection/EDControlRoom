# Iteration Log

- Area: `control-room`
- Title: `haul-panel-session-profit-refresh`
- Started: `2026-06-28 18:34`

## Summary

- Restored live-feeling haul panel updates after the client/server split and expanded the panel to show session duration, net session profit, and clearer billion-scale credit formatting.

## Changes

- Added `session_started_at` to haul runtime state and the observer snapshot contract so local and remote Control Room views can render session duration consistently.
- Updated haul-panel rendering to show `Session` and net `Profit`, and changed compact credit formatting to display billion-plus values as `1b xxx.xxM CR`.
- Updated the headless observer host so periodic haul refreshes publish snapshots, allowing remote clients to keep elapsed/profit rows moving even when no new journal event has arrived.
- Added focused coverage for billion-format rendering/TTS and for the haul panel session/profit rows, then verified the full suite passed.

## Follow-ups

- Live-check the panel in both embedded and `control_room connect` sessions to confirm the new compact billion format reads well during long-haul runs.
