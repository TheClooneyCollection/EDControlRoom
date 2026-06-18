# CI and Release Status
## Current
- Stable tags have been backfilled across the post-`v1.7.3` milestones as `v1.8.0`, `v1.9.0`, and `v1.10.0`; only the latest milestone on `main` carries a fresh release-prep version bump.
- `main` is now the rolling-update branch, and stable features or releases are identified with tags instead of `dev -> main` promotion.
- The legacy `.github/workflows/promote-dev-to-main.yml` automation has been removed; release/process automation now centers on `main`, semantic version tags, and manual GitHub release publishing.
- The auto-commit `.github/workflows/sync-iteration-archive.yml` workflow has been removed; iteration archive refresh is manual, while CI still guards drift.
- Pull requests still need `tools/iteration_logs.py validate` plus a rendered-archive diff check in `Tests` so stale archive drift fails visibly until `docs/iteration-archive.md` is refreshed locally.
- A repo-wide `workflow_run` notifier posts to Discord via `DISCORD_WEBHOOK_URL` whenever any workflow other than the notifier itself completes with `failure`.
- PR `#17` confirmed the notifier trigger still fires after a `Tests` failure; the notifier now includes the first failed job and failed step at the top of the Discord message and suppresses link previews with `flags: 4`.
- Workflow YAML changes are expected to be locally parse-validated before push so GitHub does not become the first syntax check.
- Tests run on `pull_request` and on `push` only for `main`.
- Release prep is manual: prepare the release commit, run the full suite, tag `vX.Y.Z`, and publish the GitHub release directly.
## Caveats
- Retroactive milestone tags after `v1.7.3` were placed directly on existing commits to avoid rewriting `main`, so historical release-prep commits do not exist for those backfilled cuts.
- Historical iteration logs and generated archives still mention the old promotion path because they are retained as chronology, not current policy.
## Next
- Live-check the next failing Actions run to confirm the job/step lookup and markdown link rendering match the local proof-of-concept.
- Confirm the next PR that changes iteration logs is refreshed locally so the `Tests` archive guard remains the only enforcement path.
- Remove or refresh any remaining non-historical promotion or legacy release-automation references if they surface in future docs or automation changes.
