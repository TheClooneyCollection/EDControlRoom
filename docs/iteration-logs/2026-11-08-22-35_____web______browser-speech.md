# Iteration Log

- Area: `web`
- Title: `browser-speech`
- Started: `2026-11-08 22:35`

## Summary

- Bring TTS to iPhone/Safari without the console app. The server already broadcast `event.announcement_emitted` with rendered `message_text`; the web page ignored it.

## Changes

- `haul-ui.js` re-dispatches the event as `edcr:announcement`; new `web/speech.js` (served from the asset allowlist) speaks it with `speechSynthesis`.
- Routine panel disclosure `Speak announcements on this device`: on/off, voice (English voices, or all if none), rate 0.5x to 1.5x, `Test voice`. Settings are per device in localStorage so a Mac already using `say` does not double up.
- iOS needs a user gesture: the first tap after load speaks a silent utterance to unlock audio. Only live announcements speak; nothing replays on reconnect.

## Follow-ups

- Not yet tested on a real iPhone: which voices Safari lists (downloaded enhanced voices vs Siri voices) and whether the silent switch mutes it.
- Locked screen or background tab suspends the page, so speech stops. Wake Lock needs https (for example `tailscale serve`); Web Push plus AirPods announce notifications is the locked-screen option.
- The server must restart once to serve `speech.js` because the asset allowlist lives in `app.py`.
