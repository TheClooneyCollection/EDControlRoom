# Iteration Log

- Area: `control-room`
- Title: `server-mirror-activity-and-disable-local-tts`
- Started: `2026-06-19 12:27`

## Summary

- Changed `serve` so the headless server no longer speaks TTS locally, while connected clients still receive announcement events and can speak them client-side; server-side activity log entries are now mirrored into server logs.

## Changes

- Forced `HeadlessControlRoomHost` to build its `TTSAnnouncer` with a `NullSpeechBackend`, which keeps `event.announcement_emitted` intact but suppresses local server speech.
- Added `ServerActivityLogSink` plus a small fan-out sink so `serve` mirrors protocol activity-log entries into server logs alongside the broker session stream.
- Added server tests covering announcement-event emission without local speech and activity-log mirroring into a logger.
- Verified with `uv run python3 -m unittest tests/test_control_room_server.py` and `uv run python3 -m unittest discover -s tests`.

## Follow-ups

- Live-check the `serve` console output during real routine runs to make sure the mirrored activity lines are the right signal density for operators.
- If the server needs structured logs later, replace the current plain mirrored message sink with a JSON or field-based logger instead of changing the activity event shape.
