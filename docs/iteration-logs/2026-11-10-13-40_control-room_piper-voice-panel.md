# Iteration Log

- Area: `control-room`
- Title: `piper-voice-panel`
- Started: `2026-11-10 13:40`

## Summary

- The `/controls` Voice panel now drives the host Piper voice instead of browser speech: free-text `say`, TTS phrase presets to prefill it, a voice picker, five tuning sliders and Save to config.

## Changes

- `[tts.piper]` accepts optional `length_scale`, `noise_scale`, `noise_w_scale`, `sentence_silence` and `volume` (unset keeps the model or piper default); `save_piper_voice` upserts them without touching other lines.
- `PiperSpeechBackend.configure` swaps the voice between utterances and restarts piper; `piper_model_defaults` reads the model's `inference` block, `piper_voice_models` lists `<voices>/<name>/*.onnx` beside the configured model.
- New commands `say <text>` and `voice` / `voice set k=v ...` / `voice save` (`edap/control_room/voice.py`); `TTSAnnouncer.say` bypasses phrases and disabled messages.
- Hydrate carries `voice` (speech on, Piper flag, current and installed voices, effective settings, phrase presets with `{title}` filled). The web fills `{system_name}` / `{station_name}` from the ship.
- Reverted the browser `say` hook in `web/speech.js`; `/haul` keeps its device speech.
- Verified the real piper CLI accepts every tuning flag with the jenny voice.

## Follow-ups

- Needs a LAN server restart before the panel works; not yet tried in a real browser.
