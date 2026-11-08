# Iteration Log

- Area: `runtime`
- Title: `piper-tts-backend`
- Started: `2026-11-08 22:58`

## Summary

- Add a Piper TTS backend so the Deck (and Mac) get a natural local voice instead of `spd-say`/espeak.

## Changes

- `[tts.piper] executable` + `model` (`PiperVoiceConfig`); config load rejects a half-filled table or missing files.
- `PiperSpeechBackend` keeps one `piper --output_dir` process loaded: write a line, read back the wav path, play it, delete it. A dead or silent Piper is killed and restarted once per line. Players: `pw-play`/`paplay`/`aplay` on Linux, `afplay` on macOS; no player means the platform voice.
- Deck measurements: cold `cori-high` about 3.1s per line, warm about 1.85s; medium voices about 0.9s cold. Live check on the Deck through `build_speech_backend` played two lines and left no wavs.
- `tools/speak.py` still uses the platform voice. Docs: `config.example.toml`, getting-started (browser speech plus Piper; dropped the stale "browser will not speak").

## Follow-ups

- `lan` still passes `NullSpeechBackend`; speaking on the server host by default is the planned next step.
