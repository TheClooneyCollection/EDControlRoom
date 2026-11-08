# Iteration Log

- Area: `runtime`
- Title: `piper-setup-all-platforms`
- Started: `2026-11-08 23:21`

## Summary

- One Piper path on macOS, Linux and Windows: piper-tts as an isolated `uv tool`, the two picked voices as defaults, and `tools/setup_piper.py` to install and configure it.

## Changes

- Engine: PyPI `piper-tts==1.8.0` (piper1-gpl) via `uv tool install`, run only as a subprocess. It is GPL-3.0-or-later and this repo is MIT, so it is not a project dependency and is never imported. The old rhasspy C++ release is dropped: its macOS build misses `libespeak-ng`.
- `PiperSpeechBackend` reads piper-tts' stderr `Wrote <path>` line (the C++ build printed the path on stdout) and plays through an injected `play(wav_path)`: `pw-play`/`paplay`/`aplay`, `afplay`, or stdlib `winsound` on Windows. The child gets UTF-8 stdio.
- `edap/piper_setup.py` + `tools/setup_piper.py [--voice cori|jenny]`: install the tool, download the voice to the platform data dir (`~/Library/Application Support/EDControlRoom/piper`, `$XDG_DATA_HOME` or `~/.local/share/EDControlRoom/piper`, `%LOCALAPPDATA%\EDControlRoom\piper`) with pinned piper-voices v1.0.0 sizes and md5s, write `[tts.piper]` (TOML literal strings), reload-check the config (restoring it on failure), and speak a test line.
- Voice licenses: Cori is trained on public-domain LibriVox. Jenny's dataset allows commercial use but asks for the "Jenny (Dioco)" credit, which the voice label and docs carry.
- Verified on the Mac: a fresh install, an install of the second voice, and a switch back (files already present skipped, section replaced in place).

## Follow-ups

- Windows is untested live (unit tests only).
