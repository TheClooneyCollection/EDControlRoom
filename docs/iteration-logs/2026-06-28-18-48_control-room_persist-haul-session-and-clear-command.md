# Iteration Log

- Area: `control-room`
- Title: `persist-haul-session-and-clear-command`
- Started: `2026-06-28 18:48`

## Summary

- Added persisted haul-session totals plus an explicit reset command/config path so session profit and time survive relaunches until the operator clears them.

## Changes

- Added persisted haul-session fields to control-room saved state, restoring session elapsed time/profit and related summary fields on launch instead of dropping them on app restart.
- Added `new_session` with `clear` alias, wired it through command help/dispatch, and made it reset persisted session counters without interrupting an active haul routine.
- Added `defaults/control_room.toml` with `clear_session_on_launch = false`, threaded that config through parsing and `config.example.toml`, and made startup optionally clear the saved session automatically.
- Updated haul-session tracking so state saves happen as haul metrics change and starting a new haul preserves any restored persisted session totals until the operator explicitly resets them.

## Follow-ups

- Live-check whether operators want the no-active-haul panel to always show the persisted session block, or only when the session has non-zero time/profit.
