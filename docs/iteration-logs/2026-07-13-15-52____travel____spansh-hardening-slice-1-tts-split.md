# Iteration Log

- Area: `travel`
- Title: `spansh-hardening-slice-1-tts-split`
- Started: `2026-07-13 15:52`

## Summary

- Split shared `AnnouncementId.DESTINATION_SET` into two ids so the mid-route "opening galaxy map" TTS stops firing on every `FSDTarget` journal event. Plan 0013 slice 1.

## Changes

- `edap/tts.py`: added `AnnouncementId.FSD_TARGET_LOCKED = "fsd_target_locked"`.
- `defaults/tts.toml`: new phrase `fsd_target_locked = "New FSD target acquired: {system_name}."`. `destination_set` phrase unchanged.
- `edap/control_room/app.py`: `FSDTarget` handler now emits `FSD_TARGET_LOCKED`. Routine call site in `edap/routines/transit.py` still emits `DESTINATION_SET` when the routine is actually about to open the galaxy map.
- `tests/test_control_room.py`: FSDTarget path now asserts `FSD_TARGET_LOCKED`.
- `tests/test_config.py`: defaults test asserts the new phrase text.

## Follow-ups

- Slice 2 (undock/boost handoff) and slice 2b (drop per-hop timeout) up next.
