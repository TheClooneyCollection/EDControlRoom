# Iteration Log

- Area: `control-room`
- Title: `controls-voice-say`
- Started: `2026-11-10 13:31`

## Summary

- `/controls` gains a Voice panel: type any text and speak it on the browsing device, with the device voice selector, rate, test button and an opt-in for routine announcements.

## Changes

- `web/speech.js`: optional `speech-say-text` / `speech-say` control (click or Enter) that cancels any current utterance and speaks the text, regardless of the announcements toggle. Settings stay shared with `/haul` via `edcr.speech`.
- `web/controls.js` forwards `event.announcement_emitted` as `edcr:announcement`, so the opt-in works on `/controls`.
- `web/controls.html` loads `speech.js` and adds the panel.

## Follow-ups

- This is browser speech only. Speaking arbitrary text through the server TTS (`say` / Piper) with a server voice selector would need a new command and a server restart.
