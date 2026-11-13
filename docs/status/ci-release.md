# CI and Release Status
## Current
- Latest stable release is `v1.38.0` (/routes carrier names, access filter and distances; buy/sell prices and supply/demand per leg on /routes and /haul; haul run and Track only fixes). `v1.37.0` renamed `edap` to `edcr` and removed CV; `v1.36.0` added two-way haul Track only; `v1.33.0` was the hub Control Room.
- Every recent `Tests` failure was the `test_timing` wall-clock guard (5s) on `ubuntu-latest`, never a test: a fresh runner spent ~2s compiling `.pyc` files, so passing runs sat at 4.0-4.8s and noise tipped them over. The job now installs with `--compile-bytecode` and runs `compileall` on the repo before the timed run.
- The unittest budget is `0.0006s` per executed test; over it, run `tools/report_test_timing.py` before wrapping up. Latest check (`1183` tests, budget `0.71s`): `0.72-0.75s`, was `0.87s`. Test apps get `tests.fakes.write_text_plain` as `write_state_file` (no fsync and rename per save) and `memory_store` copies a prebuilt schema. Earlier: `_CachedThemeVariables`, the shared-loop `TestClient` in `tests/shared_loop.py`, C YAML loader, 1ms EDDN polling. Left: GC (~60ms/suite; a raised threshold cut ~40ms, not applied) and ~3.4ms per hub relay test from WebSocket sessions.
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
