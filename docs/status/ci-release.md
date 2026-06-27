# CI and Release Status
## Current
- The unittest timing budget now scales as `0.0006s` per executed test, so the current `551`-test suite budget is `0.3306s`; when a release-prep or CI run exceeds that computed ceiling, capture a timing report before wrapping up.
- The latest full `uv run python3 -m unittest discover -s tests` release-prep run was `551` tests in `1.030s`, which is over budget; the follow-up `tools/report_test_timing.py --top 10 --sort slowest` report still points at the same server, path, and bindings cases, with the slowest individual test at about `0.040s`.
- The Discord workflow-failure notifier is now split into a checked-in Python script plus a thin workflow wrapper, so the same payload/fetch/post path can be dry-run locally against saved jobs JSON and exercised in CI without keeping the logic trapped inside inline workflow shell.
- `main` is now prepared for `v1.14.1`, covering the configurable Inara haul-search flow, remote observer/control-room follow-ups, haul profit and navigation fixes, the extracted Discord workflow-failure notifier, and Playwright promoted into the base runtime dependency set so released installs no longer need a separate browsing extra.
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
