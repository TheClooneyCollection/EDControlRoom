# Iteration Log

- Area: `haul`
- Title: `eddn-default-off`
- Started: `2026-11-10 16:55`

## Summary

- `eddn.enabled` defaults to false again: the user does not want every server listening to EDDN by default. Turn it on with `[eddn] enabled = true`.

## Changes

- `EddnConfig.enabled`, its parse fallback and `defaults/eddn.toml` are false; `config.example.toml`, README, `docs/user/trade-routes.md` and status describe opting in. The defaults test asserts it is off.
- The user's ignored `config.toml` gets `[eddn] enabled = true` back (removed earlier as redundant) so their server keeps listening.

## Follow-ups

-
