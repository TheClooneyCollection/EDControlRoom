# CI and Release Status
## Current
- Latest stable release is `v1.32.0` (our captured markets feed the local EDDN DB, newest data wins; `/routes` filter defaults shown with per-filter off switches; a two-way haul that ends mid-run continues as one run on restart; restart after a denied dock requests docking again). `v1.31.0` was the all-in haul history total and `/routes` Open in haul; `v1.30.0` was the mass lock confirmation and supercruise fallback countdown.
- The unittest timing budget now scales as `0.0006s` per executed test, so the current `1051`-test suite budget is `0.6306s`; when a release-prep or CI run exceeds that computed ceiling, capture a timing report before wrapping up.
- Latest timing check (v1.32.0 prep): `1057` tests in `0.582s`, under the `0.6342s` budget; v1.31.0 prep ran `0.73-0.83s` with no single slow test (slowest 0.019s), so the overrun looked like machine load. After v1.29.0: Fixed: the EDDN service test's fake socket returned at once and spun the listener, starving the status thread (~0.11s, now ~0.015s), and the FSD charge wait polled per clock tick (haul tests' 0.01s ticks made ~200 Status.json reads per departure; it now polls by count). What remains is spread out: `test_control_room` (~0.27s over 233 tests) builds a full Textual `ControlRoomApp` per test (~0.23ms for `App()` alone) and every state save `fsync`s (~30-50ms suite-wide).
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
