# Iteration Log

- Area: `haul`
- Title: `buy-warning-tts`
- Started: `2026-11-06 21:13`

## Summary

- The user asked for spoken TTS for three buy warnings: no units available, cannot afford a top-up, and still short after the top-up limit. They use the existing `AnnouncementId` plus `defaults/tts.toml` path; the progress text is unchanged.

## Changes

- `market_buy_none_available` (market-level, also used by the `buy` command): "{title}, no {commodity_name} available to buy. Continuing with current load."
- `haul_top_up_unaffordable` (two-way and multi-leg): "{title}, cannot afford more {commodity_name} at {station_name}. Continuing with partial load."
- `haul_buy_still_short` (two-way and multi-leg): "{title}, buy short at {station_name}. Continuing with partial load."
- The per-top-up "Short buy ... topping up" line is not spoken, because each top-up already announces `buying_cargo`.

## Follow-ups

- Listen to the phrases live after the `lan` server restart.
