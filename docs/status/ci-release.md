# CI and Release Status
## Current
- Latest stable release is `v1.33.0` (hub Control Room: `[hub] url` peers forward haul searches and `/routes` to a home hub and push markets to its shared DB, with heartbeat, `/api/hub-status` and a sidebar Hub chip; `POST /api/command` and `/api/stop`; new `/travel` page and one shared nav; CI bytecode precompile fixes the timing guard). `v1.32.0` fed our captured markets into the EDDN DB; `v1.31.0` was the all-in haul history total.
- Every recent `Tests` failure was the `test_timing` wall-clock guard (5s) on `ubuntu-latest`, never a test: a fresh runner spent ~2s compiling `.pyc` files, so passing runs sat at 4.0-4.8s and noise tipped them over. The job now installs with `--compile-bytecode` and runs `compileall` on the repo before the timed run.
- The unittest budget is `0.0006s` per executed test; over it, run `tools/report_test_timing.py` before wrapping up. Latest check (hub branch, `1135` tests): `0.60s`, was `0.66-0.72s`. Test `ControlRoomApp`s share `_CachedThemeVariables` (Textual theme build once per theme), and `tests/shared_loop.py`'s `TestClient` runs every app on one event loop thread; import it instead of Starlette's. Earlier: no real `git` via the default version source, C YAML loader, 1ms EDDN polling. Left: GC (~45ms/suite, not tunable usefully) and ~2.5ms per hub relay test from WebSocket thread hops.
- The Discord workflow-failure notifier is now split into a checked-in Python script plus a thin workflow wrapper, so the same payload/fetch/post path can be dry-run locally against saved jobs JSON and exercised in CI without keeping the logic trapped inside inline workflow shell.
- `main` is now the rolling-update branch, and stable features or releases are identified with tags instead of `dev -> main` promotion.
- The legacy `.github/workflows/promote-dev-to-main.yml` automation has been removed; release/process automation now centers on `main`, semantic version tags, and manual GitHub release publishing.
- The auto-commit `.github/workflows/sync-iteration-archive.yml` workflow has been removed; iteration archive refresh is manual, while CI still guards drift.
- Pull requests still need `tools/iteration_logs.py validate` plus a rendered-archive diff check in `Tests` so stale archive drift fails visibly until `docs/iteration-archive.md` is refreshed locally.
- A repo-wide `workflow_run` notifier posts to Discord via `DISCORD_WEBHOOK_URL` whenever any workflow other than the notifier itself completes with `failure`.
- PR `#17` confirmed the notifier trigger still fires after a `Tests` failure; the notifier now includes the first failed job and failed step at the top of the Discord message and suppresses link previews with `flags: 4`.
- Workflow YAML changes are expected to be locally parse-validated before push so GitHub does not become the first syntax check; tests run on `pull_request` and on `push` only for `main`.
- Release prep is manual: prepare the release commit, run the full suite, tag `vX.Y.Z`, and publish the GitHub release directly.
## Caveats
- Retroactive milestone tags after `v1.7.3` were placed directly on existing commits to avoid rewriting `main`, and historical iteration logs/generated archives still mention the old promotion path because they are retained as chronology, not current policy.
## Next
- Live-check the next failing Actions run to confirm the extracted notifier script matches the locally tested payload and webhook behavior end to end.
- Confirm the next PR that changes iteration logs is refreshed locally so the `Tests` archive guard remains the only enforcement path.
- Remove or refresh any remaining non-historical promotion or legacy release-automation references if they surface in future docs or automation changes.
