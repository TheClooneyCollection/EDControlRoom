# Iteration Log

- Area: `control-room`
- Title: `server-version-commit`
- Started: `2026-11-10 13:27`

## Summary

- A LAN server could not show which code it was running. The Mac server reported `1.26.0` on `/health` after v1.27.0 shipped, and the version alone cannot tell commits after a release apart.

## Changes

- `edap/version.py`: `get_current_commit(git)` returns the short HEAD, with `+dirty` for uncommitted tracked edits, or `""` without git; `get_startup_commit()` caches it once per process so a running server keeps reporting what it loaded.
- `VersionSource.get_current_commit` feeds `ServerStatusReadModel.server_commit`; `/health` returns `server_commit`, and pages get `serverCommit` in their injected config.
- `/haul`, `/multi-haul` and `/controls` show a sidebar Version row such as `1.27.0 (b2a65e4)`, refreshed from each hydrate.
- Calling git per app construction pushed the suite to 1.6 s; the per-process cache brings it back to baseline.

## Follow-ups

- Optional: flag when the server's startup commit differs from the checkout's current HEAD (restart needed).
