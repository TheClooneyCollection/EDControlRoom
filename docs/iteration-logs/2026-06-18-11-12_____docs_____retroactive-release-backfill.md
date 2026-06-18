# Iteration Log

- Area: `docs`
- Title: `retroactive-release-backfill`
- Started: `2026-06-18 11:12`

## Summary

- Backfilled stable release milestones after `v1.7.3` into three coherent cuts: `v1.8.0`, `v1.9.0`, and `v1.10.0`.

## Changes

- Tagged `f0e99ce` as `v1.8.0` for the standalone multi-leg haul and control-room/operator improvements tranche.
- Tagged `36411f1` as `v1.9.0` for the haul-loop, arrival/sell timing, and release-process hardening tranche.
- Prepared `main` for `v1.10.0` by bumping `[project].version` to match the configurable timing/routing milestone at `HEAD`.
- Updated `docs/status/ci-release.md` to record the retroactive-tagging exception and the current stable tag state.

## Follow-ups

- Run `uv sync`, validate the full unittest suite, refresh `docs/iteration-archive.md`, and publish the GitHub releases for the backfilled tags.
